from fastapi import APIRouter, Depends, status, HTTPException, Body, Path, Security
from fastapi.responses import ORJSONResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import Annotated

from app.backend.db_depends import get_session, product_found, rating_found
from app.schemas.schemas import ReviewWithRating
from app.models.models import Product, User, Review, Rating
from app.routers.auth import check_user_credentials


router = APIRouter(
    prefix='/reviews',
    tags=['reviews']
)


@router.get(
    '/',
    response_class=ORJSONResponse,
    dependencies=[Security(check_user_credentials, scopes=['admin', 'supplier', 'customer'])]
)
async def all_reviews(
    db: Annotated[AsyncSession, Depends(get_session)]
):
    reviews = await db.scalars(select(Review).where(Review.is_active == True))
    return [review.attrs for review in reviews]


@router.get(
    '/product/{product_slug}',
    response_class=ORJSONResponse,
    dependencies=[
        Security(check_user_credentials, scopes=['admin', 'supplier', 'customer']),
        Depends(product_found)
    ]
)
async def products_reviews(
        db: Annotated[AsyncSession, Depends(get_session)],
        product_slug: Annotated[str, Path()]
):
    reviews = await db.scalars(
        select(Review)
        .join(Product)
        .where(and_(Product.slug == product_slug,
                    Review.is_active == True))
    )
    return [review.attrs for review in reviews]


@router.post(
    '/product/{product_slug}',
    response_class=ORJSONResponse
)
async def add_review(
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Security(check_user_credentials, scopes=['customer'])],
    review: Annotated[ReviewWithRating, Body()],
    product: Annotated[Product, Depends(product_found)]
):

    new_rating = Rating(grade=review.grade,
                        user_id=user.id,
                        product_id=product.id)
    db.add(new_rating)

    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Review by user already posted'
        )
    else:
        new_review = Review(user_id=user.id,
                            product_id=product.id,
                            rating_id=new_rating.id,
                            comment=review.comment)
        db.add(new_review)
        await db.commit()

        return {
            'status_code': status.HTTP_201_CREATED,
            'transaction': 'Review added'
        }


@router.delete(
    '/{rating_id}',
    response_class=ORJSONResponse,
    dependencies=[Security(check_user_credentials, scopes=['admin'])]
)
async def delete_reviews(
    db: Annotated[AsyncSession, Depends(get_session)],
    rating: Annotated[Rating, Depends(rating_found)]
):
    rating.is_active = False
    rating.review.is_active = False
    await db.commit()

    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Review deleted'
    }
