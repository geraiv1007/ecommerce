from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Literal


class CreateCategory(BaseModel):

    name: str
    parent_id: int | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Sample Category",
                "parent_id": 0,
            }
        }
    )


class CreateProduct(BaseModel):

    name: str
    description: str
    price: int
    image_url: str | None = None
    stock: int
    category_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Sample Product",
                "description": "Description of a Product",
                "price": 0.0,
                "image_url": "http",
                "stock": 0,
                "category_id": 1
            }
        }
    )


class CreateUser(BaseModel):

    first_name: str
    last_name: str
    username: str
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Ivan",
                "last_name": "Ivanov",
                "username": 'username',
                "email": "username@google.com",
                "password": ''
            }
        }
    )


class UserNoPassword(BaseModel):

    first_name: str
    last_name: str
    username: str
    email: EmailStr


class JWTToken(BaseModel):

    access_token: str
    token_type: str = Field(default='bearer')


class JWTTokenWithScope(JWTToken):

    scopes: list[str] = Field(default=[])


class TokenData(BaseModel):

    username: str
    scopes: list[str] = Literal['admin', 'supplier', 'customer']


class ReviewWithRating(BaseModel):

    comment: str = Field(min_length=10)
    grade: int = Field(gt=0, le=10)
