from celery import Celery
from app.middleware.log import log_middleware
from app.models.models import Base
from app.routers import category, products, auth, reviews
from fastapi import FastAPI, BackgroundTasks
import time
import uvicorn


app = FastAPI()
app.include_router(category.router)
app.include_router(products.router)
app.include_router(auth.router)
app.include_router(reviews.router)
#app.middleware('http')(log_middleware)

celery = Celery(
    __name__,
    broker='redis://127.0.0.1:6379/0',
    backend='redis://127.0.0.1:6379/0',
    broker_connection_retry_on_startup=True
)
