from app.backend.db import AsyncSession
from app.models.models import Category, Product, Rating
from app.schemas.schemas import CreateProduct, CreateCategory
from fastapi import Depends, status, Body, Path, Query
from fastapi.exceptions import HTTPException
from sqlalchemy import select, and_
from slugify import slugify
from typing import Annotated


async def get_session():
    session = AsyncSession()
    try:
        yield session
    finally:
        await session.reset()


async def category_found(
    category_slug: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_session)]
):
    stmt = select(Category).where(Category.slug == category_slug)
    category = await db.scalar(stmt)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There is no category found'
        )

    return category.attrs


async def category_already_exists(
    category: Annotated[CreateCategory, Body()],
    db: Annotated[AsyncSession, Depends(get_session)]
):
    category = await db.scalar(select(Category).where(Category.slug == slugify(category.name)))
    if category:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Category already present'
        )


async def product_found(
    product_slug: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_session)]
):
    product = await db.scalar(select(Product).where(Product.slug == product_slug))
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No product found'
        )
    return product


async def product_already_exists(
    product: Annotated[CreateProduct, Body()],
    db: Annotated[AsyncSession, Depends(get_session)]
):
    product = await db.scalar(select(Product).where(Product.slug == slugify(product.name)))
    if product:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Product already present'
        )


async def rating_found(
    rating_id: Annotated[int, Path()],
    db: Annotated[AsyncSession, Depends(get_session)]
):
    rating = await db.scalar(select(Rating).where(and_(Rating.id == rating_id, Rating.is_active == True)))
    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No active rating found'
        )

    return rating
