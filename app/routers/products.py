from fastapi import APIRouter, Depends, status, HTTPException, Body, Path, Security
from fastapi.responses import ORJSONResponse
from sqlalchemy import select, union, and_
from sqlalchemy.ext.asyncio import AsyncSession
from slugify import slugify
from typing import Annotated

from app.backend.db_depends import get_session, product_found, product_already_exists, category_found
from app.schemas.schemas import CreateProduct
from app.models.models import Product, Category, User
from app.routers.auth import check_user_credentials


router = APIRouter(
    prefix='/products',
    tags=['products']
)


@router.post(
    '/',
    status_code=status.HTTP_201_CREATED,
    response_class=ORJSONResponse,
    dependencies=[Depends(product_already_exists)]
)
async def create_product(
        product: Annotated[CreateProduct, Body()],
        db: Annotated[AsyncSession, Depends(get_session)],
        user: Annotated[User, Security(check_user_credentials, scopes=['admin', 'supplier'])]
):
    new_product = Product(
        name=product.name,
        slug=slugify(product.name),
        description=product.description,
        price=product.price,
        image_url=product.image_url,
        stock=product.stock,
        supplier_id=user.id if user.is_supplier else None,
        category_id=product.category_id,
        rating=0.0
    )
    db.add(new_product)
    await db.commit()

    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful'
    }


@router.get(
    '/',
    status_code=status.HTTP_200_OK,
    response_class=ORJSONResponse,
    dependencies=[Security(check_user_credentials, scopes=['admin', 'customer', 'supplier'])]
)
async def all_products(
        db: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = (
        select(Product).
        where(Product.is_active == True).
        where(Product.stock > 0)
    )
    result = (await db.scalars(stmt)).all()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There are no products'
        )

    return list(map(lambda x: x.attrs, result))


@router.get(
    '/category/{category_slug}',
    status_code=status.HTTP_200_OK,
    response_class=ORJSONResponse,
    dependencies=[Security(check_user_credentials, scopes=['admin', 'supplier', 'customer'])]
)
async def product_by_category(
    category_slug: Annotated[str, Path()],
    category: Annotated[dict[str, str | int], Depends(category_found)],
    db: Annotated[AsyncSession, Depends(get_session)]
):
    subcategories = select(Category.id)\
        .where(Category.parent_id == category['id'])
    categories = select(Category.id)\
        .where(Category.id == category['id'])
    union_stmt = union(categories, subcategories).subquery()
    stmt = (
        select(Product)
        .where(and_(Product.is_active == True,
                    Product.stock > 0,
                    Product.category_id.in_(select(union_stmt))))
    )
    rows = await db.scalars(stmt)
    result = [row.attrs for row in rows]

    return result


@router.get(
    '/detail/{product_slug}',
    status_code=status.HTTP_200_OK,
    response_class=ORJSONResponse,
    dependencies=[Security(check_user_credentials, scopes=['admin', 'supplier', 'customer'])]
)
async def product_detail(
    product_slug: Annotated[str, Path()],
    product: Annotated[Product, Depends(product_found)]
):

    return product.attrs


@router.put(
    '/{product_slug}',
    status_code=status.HTTP_200_OK,
    response_class=ORJSONResponse,
    dependencies=[Depends(product_found)]
)
async def update_product(
    product_slug: Annotated[str, Path()],
    update_product: Annotated[CreateProduct, Body()],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Security(check_user_credentials, scopes=['admin', 'supplier'])]
):
    product = await db.scalar(select(Product).where(Product.slug == product_slug))
    if user.is_supplier and user.id != product.supplier_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to use this method"
        )
    new_attrs = {key: getattr(update_product, key)
                 for key in update_product.model_fields_set}
    new_attrs.update({'slug': slugify(update_product.name)})
    for attr, val in new_attrs.items():
        setattr(product, attr, val)
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Product update is successful'
    }


@router.delete(
    '/{product_slug}',
    status_code=status.HTTP_200_OK,
    response_class=ORJSONResponse,
    dependencies=[Depends(product_found)]
)
async def delete_product(
    product_slug: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Security(check_user_credentials, scopes=['admin', 'supplier'])]
):
    product = await db.scalar(select(Product).where(Product.slug == product_slug))
    if user.is_supplier and user.id != product.supplier_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are not authorized to use this method"
        )
    product.is_active = False
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Product delete is successful'
    }

