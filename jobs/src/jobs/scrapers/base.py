import logging
import os
from abc import ABC
from abc import abstractmethod
from contextlib import asynccontextmanager
from datetime import UTC
from datetime import datetime

import aiohttp
from aiolimiter import AsyncLimiter
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("scraper")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(levelname)s [%(asctime)s] %(name)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


POSTGRES_URL = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"

engine = create_async_engine(POSTGRES_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

REDIS = Redis(
    host="redis", port=6379, decode_responses=True, auto_close_connection_pool=False
)


async def init_db():
    from .models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class AsyncScraper(ABC):
    def __init__(
        self,
        namespace: str,
        request_limit: float = 1,
        request_interval: int = 60,
    ):
        self.namespace = namespace
        self.logger = logger.getChild(namespace)

        self._limiter = AsyncLimiter(request_limit, request_interval)
        self._last_fetch = None
        self._next_run = None

    @property
    def should_run(self) -> bool:
        if not self._next_run:
            return True
        return datetime.now(UTC) > self._next_run

    @asynccontextmanager
    async def get_session(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def cache_api_response(self, response: str):
        await REDIS.set(f"jobs:extract:{self.namespace}", response)

    async def set_last_fetch(self, timestamp: datetime):
        await REDIS.set(f"jobs:lastfetch:{self.namespace}", timestamp.isoformat())

    async def get_last_fetch(self) -> datetime | None:
        last_fetch = await REDIS.get(f"jobs:lastfetch:{self.namespace}")
        if last_fetch:
            return datetime.fromisoformat(last_fetch)
        else:
            return None

    async def set_next_run(self, timestamp: datetime):
        await REDIS.set(f"jobs:nextrun:{self.namespace}", timestamp.isoformat())

    async def get_next_run(self) -> datetime | None:
        next_run = await REDIS.get(f"jobs:nextrun:{self.namespace}")
        if next_run:
            return datetime.fromisoformat(next_run)
        else:
            return None

    async def fetch(self, url: str, method: str = "GET", **request_args):
        async with self._limiter:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **request_args) as response:
                    response.raise_for_status()
                    content = await response.text()

        await self.set_last_fetch(datetime.now(UTC))
        await self.cache_api_response(content)
        return content, response.headers

    @abstractmethod
    async def transform(self):
        pass

    @abstractmethod
    async def load(self):
        pass

    @abstractmethod
    async def run(self):
        pass
