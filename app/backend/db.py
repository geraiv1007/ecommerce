from datetime import datetime
from environs import Env
from sqlalchemy import Integer, Text, Boolean, DateTime, MetaData, func, URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column
from typing import Annotated


int_pk = Annotated[int, mapped_column(Integer, primary_key=True)]
basic_str = Annotated[str, mapped_column(Text)]
true_bool = Annotated[bool, mapped_column(Boolean, default=True)]
false_bool = Annotated[bool, mapped_column(Boolean, default=False)]
str_uq_ix = Annotated[str, mapped_column(Text, unique=True, index=True)]
curr_time = Annotated[datetime, mapped_column(DateTime, server_default=func.clock_timestamp())]


class Base(DeclarativeBase):

    metadata = MetaData(schema='ecommerce_fastapi')

    @property
    def attrs(self):
        cols = {col.key: getattr(self, col.key) for col in list(self.__table__.columns)}
        return cols


env = Env()
env.read_env()
connect_args = {
    'drivername': f'{env("DB_LANGUAGE")}+{env("DB_DRIVER")}',
    'username': env("DB_USERNAME"),
    'password': env("DB_PASSWORD"),
    'host': env("DB_HOST"),
    'port': env("DB_PORT"),
    'database': env("DB_DATABASE")
}

url = URL.create(**connect_args)
engine = create_async_engine(url)
AsyncSession = async_sessionmaker(bind=engine, expire_on_commit=False)
