import os
from contextlib import asynccontextmanager
from contextlib import contextmanager

from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    url=f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/{os.getenv('POSTGRES_DB')}"
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def database_session():
    async with AsyncSessionLocal() as session:
        yield session


@contextmanager
def cache_client():
    redis = Redis(host="redis", port=6379, decode_responses=True)
    try:
        yield redis
    finally:
        redis.close()


@asynccontextmanager
async def async_cache_client():
    redis = AsyncRedis(
        host="redis",
        port=6379,
        decode_responses=True,
        auto_close_connection_pool=False,
    )
    try:
        yield redis
    finally:
        await redis.close()


async def init_db():
    from .base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
