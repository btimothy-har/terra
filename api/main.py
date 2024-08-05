import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis
from routers.chat import router as chat_router
from routers.users import router as users_router

POSTGRES_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"
POSTGRES = AsyncConnectionPool(POSTGRES_URL,open=False)

REDIS = Redis(
    host="redis",
    port=6379,
    decode_responses=True,
    auto_close_connection_pool=False
    )

@asynccontextmanager
async def lifespan(app:FastAPI):
    app.database = POSTGRES
    await app.database.open()
    await app.database.wait()

    app.cache = REDIS
    await app.cache.ping()

    yield

    await app.database.close()
    await app.cache.close()


app = FastAPI(lifespan=lifespan)

app.include_router(users_router)
app.include_router(chat_router)
