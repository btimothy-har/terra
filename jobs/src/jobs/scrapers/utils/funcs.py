import os
from contextlib import asynccontextmanager
from datetime import UTC
from datetime import datetime
from functools import wraps

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

POSTGRES_URL = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"

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


def check_and_set_next_run():
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            async with cache_client() as cache:
                next_run = await cache.get(f"jobs:nextrun:{self.namespace}")
                next_run = datetime.fromisoformat(next_run) if next_run else None

                if not next_run or datetime.now(UTC) > next_run:
                    next_run = await func(self, *args, **kwargs)
                    await cache.set(
                        f"jobs:nextrun:{self.namespace}", next_run.isoformat()
                    )

            return next_run

        return wrapper

    return decorator


async def init_db():
    from scrapers.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
