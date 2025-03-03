from datetime import timedelta, datetime, timezone
from environs import Env
from fastapi import APIRouter, Depends, status, Security, Path
from fastapi.exceptions import HTTPException
from fastapi.responses import ORJSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from jwt import InvalidTokenError, ExpiredSignatureError
from passlib.context import CryptContext
from pydantic import ValidationError
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any
import jwt

from app.backend.db_depends import get_session
from app.schemas.schemas import CreateUser, JWTTokenWithScope, TokenData, UserNoPassword
from app.models.models import User


router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

oauth2 = OAuth2PasswordBearer(
    tokenUrl='auth/login',
    scopes={
        'admin': 'all privileges',
        'supplier': 'add goods',
        'customer': 'read only'
    }
)
env = Env()
env.read_env()
secret_key = env('SECRET_KEY')
expires = timedelta(seconds=env.int('EXPIRES'))
algorithm = env('ALGORITHM')
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def create_access_token(data: dict[str, Any], expires_delta: timedelta) -> JWTTokenWithScope:
    payload = data.copy()
    payload.update({'exp': datetime.now(tz=timezone.utc) + expires_delta})
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return token


async def user_authenticate(
        user_auth: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[AsyncSession, Depends(get_session)]
):
    user = await db.scalar(select(User).where(User.username == user_auth.username))

    if not (user and user.is_active == True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found',
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not bcrypt_context.verify(user_auth.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect password',
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


async def check_user_credentials(
    scopes: SecurityScopes,
    db: Annotated[AsyncSession, Depends(get_session)],
    token: Annotated[str, Depends(oauth2)]
):
    if scopes.scopes:
        header = f'Bearer scope="{scopes.scope_str}"'
    else:
        header = "Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": header},
    )

    try:
        decoded_token = jwt.decode(token, secret_key, leeway=0, algorithms=[algorithm])
        username = decoded_token.get('sub')
        user = await db.scalar(select(User).where(User.username == username))
        if not (username and user):
            raise credentials_exception
        TokenData.model_validate({'username': username, 'scopes': decoded_token.get('scopes', [])})
    except (InvalidTokenError, ExpiredSignatureError, ValidationError):
        raise credentials_exception

    token_scopes = set(decoded_token.get('scopes', []))
    if not token_scopes.issubset(set(scopes.scopes)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not enough permissions",
            headers={"WWW-Authenticate": header},
        )

    return user


@router.post(
    '/',
    status_code=status.HTTP_201_CREATED,
    response_class=ORJSONResponse
)
async def create_user(
        db: Annotated[AsyncSession, Depends(get_session)],
        create_user: CreateUser
):
    new_user = User(first_name=create_user.first_name,
                    last_name=create_user.last_name,
                    username=create_user.username,
                    email=create_user.email,
                    hashed_password=bcrypt_context.hash(create_user.password))
    db.add(new_user)
    await db.commit()

    return {
        'status_code': status.HTTP_201_CREATED,
        'detail': 'User created'
    }


@router.get(
    '/users/me',
    response_model=UserNoPassword
)
async def read_current_user(
        user: Annotated[User, Security(check_user_credentials, scopes=['admin', 'supplier', 'customer'])]
):
    return user


@router.post('/login')
async def login(
        user: Annotated[User, Depends(user_authenticate)]
):
    scopes = []
    if user.is_admin:
        scopes = ['admin']
    if user.is_supplier:
        scopes = ['supplier']
    if user.is_customer:
        scopes = ['customer']
    if not scopes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User error. Contact support'
        )
    data = {
        'sub': user.username,
        'user_id': user.id,
        'scopes': scopes
    }
    token = create_access_token(data, expires_delta=expires)
    return JWTTokenWithScope(access_token=token)


@router.patch(
    '/add_supplier/{user_id}',
    dependencies=[Security(check_user_credentials, scopes=['admin'])]
)
async def apply_supplier_role(
    db: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[int, Path()]
):
    new_supplier = await db.scalar(select(User).where(and_(User.id == user_id,
                                                           User.is_supplier == False,
                                                           User.is_active == True)))
    if not new_supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No inactive supplier found by id'
        )
    new_supplier.is_supplier = True
    new_supplier.is_customer = False
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'detail': 'User is now supplier'
    }


@router.patch(
    '/revoke_supplier/{user_id}',
    dependencies=[Security(check_user_credentials, scopes=['admin'])]
)
async def revoke_supplier_role(
    db: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[int, Path()]
):
    rev_supplier = await db.scalar(select(User).where(and_(User.id == user_id,
                                                           User.is_supplier == True,
                                                           User.is_active == True)))
    if not rev_supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No active supplier found by id'
        )
    rev_supplier.is_supplier = False
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'detail': 'User is no longer supplier'
    }


@router.delete(
    '/delete_user/{user_id}',
    dependencies=[Security(check_user_credentials, scopes=['admin'])]
)
async def delete_user(
    db: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[int, Path()]
):
    del_user = await db.scalar(select(User).where(and_(User.id == user_id,
                                                       User.is_active == True)))
    if not del_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No active supplier found by id'
        )
    del_user.is_active = False
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'detail': 'User is deleted'
    }
