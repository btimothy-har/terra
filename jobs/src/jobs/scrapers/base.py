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

POSTGRES_URL = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"

REDIS = Redis(
    host="redis", port=6379, decode_responses=True, auto_close_connection_pool=False
)

engine = create_async_engine(POSTGRES_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


logger = logging.getLogger("scraper")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(levelname)s [%(asctime)s] %(name)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


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
        self._last_fetched = None
        self._next_run = None

    @property
    def last_fetched(self):
        return self._last_fetched

    @property
    def should_run(self) -> bool:
        if not self._next_run:
            return True
        return datetime.now(UTC) > self._next_run

    @asynccontextmanager
    async def get_session(self):
        async with AsyncSessionLocal() as session:
            yield session

    async def fetch(self, url: str, method: str = "GET", **request_args):
        async with self._limiter:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **request_args) as response:
                    response.raise_for_status()
                    self._last_fetched = datetime.now(UTC)
                    content = await response.text()
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
