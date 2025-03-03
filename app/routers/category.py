from fastapi import APIRouter, Depends, status, Security, Path, Body
from fastapi.responses import ORJSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slugify import slugify
from typing import Annotated

from app.backend.db_depends import get_session, category_found, category_already_exists
from app.schemas.schemas import CreateCategory
from app.models.models import Category, User
from app.routers.auth import check_user_credentials


router = APIRouter(
    prefix='/categories',
    tags=['category']
)


@router.get(
    '/',
    dependencies=[Security(check_user_credentials, scopes=['admin', 'supplier', 'customer'])]
)
async def get_all_categories(
        db: Annotated[AsyncSession, Depends(get_session)]
):
    categories = (await db.scalars(select(Category).where(Category.is_active == True))).all()
    return categories


@router.post(
    '/',
    status_code=status.HTTP_201_CREATED,
    response_class=ORJSONResponse,
    dependencies=[Depends(category_already_exists),
                  Security(check_user_credentials, scopes=['admin'])]
)
async def create_category(
        db: Annotated[AsyncSession, Depends(get_session)],
        category: CreateCategory
):
    new_category = Category(name=category.name,
                            parent_id=category.parent_id,
                            slug=slugify(category.name))
    db.add(new_category)
    await db.commit()

    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful'
    }


@router.delete(
    '/{category_slug}',
    dependencies=[Depends(category_found),
                  Security(check_user_credentials, scopes=['admin'])]
)
async def delete_category(
        category_slug: Annotated[str, Path()],
        db: Annotated[AsyncSession, Depends(get_session)]
):
    category = await db.scalar(select(Category).where(Category.slug == category_slug))
    category.is_active = False
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Category delete is successful'
    }


@router.put(
    '/{category_slug}',
    dependencies=[Depends(category_found),
                  Security(check_user_credentials, scopes=['admin'])]
)
async def update_category(
        category_slug: Annotated[str, Path()],
        db: Annotated[AsyncSession, Depends(get_session)],
        upd_category: Annotated[CreateCategory, Body()]
):
    category = await db.scalar(select(Category).where(Category.slug == category_slug))
    new_attrs = {key: getattr(upd_category, key)
                 for key in upd_category.model_fields_set}
    new_attrs.update({'slug': slugify(upd_category.name)})
    for attr, val in new_attrs.items():
        setattr(category, attr, val)
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Category update is successful'
    }
