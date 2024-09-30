import asyncio
from abc import ABC
from abc import abstractmethod
from datetime import UTC
from datetime import datetime
from typing import Any

import aiohttp
from aiolimiter import AsyncLimiter

from jobs.database import cache_client
from jobs.logger import logger
from jobs.pipelines.utils import check_and_set_next_run


class ScraperFetchError(Exception):
    pass


class BaseAsyncScraper(ABC):
    def __init__(
        self,
        namespace: str,
        task_concurrency: int = 1,
        request_limit: float = 1,
        request_interval: int = 60,
    ):
        self.namespace = namespace
        self.log = logger.getChild(f"scraper.{namespace}")

        self._concurrency = asyncio.Semaphore(task_concurrency)
        self._limiter = AsyncLimiter(request_limit, request_interval)
        self._last_fetch = None
        self._iter_count = 0

    async def fetch(self, url: str, method: str = "GET", **request_args):
        async with self._limiter:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(method, url, **request_args) as response:
                        response.raise_for_status()
                        content = await response.text()
            except Exception as e:
                raise ScraperFetchError(f"Failed to fetch {url}: {e}") from e

        await self.save_state(
            f"extract:{datetime.now(UTC).isoformat()}", content, ex=259_200
        )
        return content, response.headers

    async def save_state(self, key: str, value: Any, **kwargs):
        async with cache_client() as cache:
            await cache.set(f"jobs:{self.namespace}:{key}", value, **kwargs)

    async def get_state(self, key: Any, **kwargs) -> Any:
        async with cache_client() as cache:
            data = await cache.get(f"jobs:{self.namespace}:{key}", **kwargs)
        return data if data else None

    @abstractmethod
    @check_and_set_next_run()
    async def run(self):
        pass

    @abstractmethod
    async def process(self):
        pass

    @abstractmethod
    async def load(self):
        pass

    async def ingest(self):
        raise NotImplementedError("Ingest method must be implemented in subclass.")
