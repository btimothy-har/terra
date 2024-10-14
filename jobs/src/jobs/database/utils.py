import os
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

POSTGRES_URL = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/{os.getenv('POSTGRES_DB')}"

engine = create_async_engine(POSTGRES_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def database_session():
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def cache_client():
    redis = Redis(
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
    from .schemas import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
