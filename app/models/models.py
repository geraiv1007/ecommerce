from app.backend.db import (
    Base,
    int_pk,
    basic_str,
    str_uq_ix,
    true_bool,
    false_bool,
    curr_time,
    AsyncSession
)
from sqlalchemy import ForeignKey, func, event, select, update, cast, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.orm.attributes import get_history
from typing import Optional


class Category(Base):

    __tablename__ = 'categories'

    id: Mapped[int_pk]
    name: Mapped[basic_str]
    slug: Mapped[str_uq_ix]
    is_active: Mapped[true_bool]
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey('categories.id'))

    products: Mapped[list['Product']] = relationship(back_populates='category')


class Product(Base):

    __tablename__ = 'products'

    id: Mapped[int_pk]
    name: Mapped[basic_str]
    slug: Mapped[str_uq_ix]
    description: Mapped[basic_str]
    price: Mapped[int]
    image_url: Mapped[basic_str]
    stock: Mapped[int]
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey('categories.id', ondelete='SET NULL'))
    rating: Mapped[float]
    is_active: Mapped[true_bool]

    category: Mapped['Category'] = relationship(back_populates='products', passive_deletes=True, single_parent=True)
    user: Mapped['User'] = relationship(back_populates='products', passive_deletes=True, single_parent=True)
    ratings: Mapped[list['Rating']] = relationship(back_populates='product')
    reviews: Mapped[list['Review']] = relationship(back_populates='product')


class User(Base):

    __tablename__ = 'users'

    id: Mapped[int_pk]
    first_name: Mapped[str]
    last_name: Mapped[str]
    username: Mapped[str_uq_ix]
    email: Mapped[str_uq_ix]
    hashed_password: Mapped[str]
    is_active: Mapped[true_bool]
    is_admin: Mapped[false_bool]
    is_supplier: Mapped[false_bool]
    is_customer: Mapped[true_bool]

    products: Mapped[list['Product']] = relationship(back_populates='user')
    ratings: Mapped[list['Rating']] = relationship(back_populates='user')
    reviews: Mapped[list['Review']] = relationship(back_populates='user')


class Review(Base):

    __tablename__ = 'reviews'

    id: Mapped[int_pk]
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey('products.id', ondelete='SET NULL'))
    rating_id: Mapped[int] = mapped_column(ForeignKey('ratings.id', ondelete='CASCADE'), unique=True)
    comment: Mapped[basic_str]
    comment_date: Mapped[curr_time]
    is_active: Mapped[true_bool]

    __mapper_args__ = {'eager_defaults': True}

    product: Mapped['Product'] = relationship(back_populates='reviews', passive_deletes=True, single_parent=True)
    user: Mapped['User'] = relationship(back_populates='reviews', passive_deletes=True, single_parent=True)
    rating: Mapped['Rating'] = relationship(back_populates='review', single_parent=True)


class Rating(Base):

    __tablename__ = 'ratings'
    __table_args__ = (UniqueConstraint('user_id', 'product_id'),)

    id: Mapped[int_pk]
    grade: Mapped[float]
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey('products.id', ondelete='SET NULL'))
    is_active: Mapped[true_bool]

    product: Mapped['Product'] = relationship(back_populates='ratings', passive_deletes=True, single_parent=True)
    user: Mapped['User'] = relationship(back_populates='ratings', passive_deletes=True, single_parent=True)
    review: Mapped['Review'] = relationship(back_populates='rating', lazy='selectin')


def calculate_rating(connection, product_id):
    """
    Функция пересчета рейтинга у продукта
    """
    rtng_stmt = (
        select(func.round(cast(func.avg(Rating.grade), Numeric), 2))
        .where(Rating.product_id == product_id)
        .where(Rating.is_active == True)
    )
    avg_rating = connection.scalar(rtng_stmt)
    upd_stmt = (
        update(Product)
        .where(Product.id == product_id)
        .values(rating=avg_rating)
    )
    connection.execute(upd_stmt)


@event.listens_for(Rating, 'after_insert')
def receive_after_insert(mapper, connection, target):
    calculate_rating(connection, target.product_id)


@event.listens_for(Rating, 'after_update')
def receive_after_insert(mapper, connection, target):
    status = get_history(target, 'is_active')
    if status.added[-1] is False and status.deleted[-1] is True:
        calculate_rating(connection, target.product_id)
