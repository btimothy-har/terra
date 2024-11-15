from abc import ABC
from abc import abstractmethod
from datetime import UTC
from datetime import datetime
from typing import Any

import aiohttp
from aiolimiter import AsyncLimiter
from retry_async import retry

from jobs.database import async_cache_client
from jobs.logger import logger


class ScraperFetchError(Exception):
    pass


class BaseAsyncPipeline(ABC):
    def __init__(
        self,
        namespace: str,
        request_limit: float = 1,
        request_interval: int = 60,
    ):
        self.namespace = namespace
        self.log = logger.getChild(f"scraper.{namespace}")

        self._limiter = AsyncLimiter(request_limit, request_interval)

    @retry(
        (ScraperFetchError),
        is_async=True,
        tries=10,
        delay=1,
        backoff=2,
    )
    async def download(self, url: str, method: str = "GET", **request_args):
        async with self._limiter:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(method, url, **request_args) as response:
                        response.raise_for_status()
                        content = await response.text()
            except Exception as e:
                raise ScraperFetchError(f"Failed to fetch {url}: {e}") from e

        extract_id = f"extract:{datetime.now(UTC).isoformat()}"

        await self.save_state(extract_id, content, ex=259_200)
        self.log.info(f"Saved extract ID: {extract_id}.")

        return content, response.headers

    async def save_state(self, key: str, value: Any, **kwargs):
        async with async_cache_client() as cache:
            await cache.set(f"jobs:{self.namespace}:{key}", value, **kwargs)

    async def get_state(self, key: Any, **kwargs) -> Any:
        async with async_cache_client() as cache:
            data = await cache.get(f"jobs:{self.namespace}:{key}", **kwargs)
        return data if data else None

    @abstractmethod
    async def fetch(self):
        pass

    @abstractmethod
    async def run(self):
        pass

    @abstractmethod
    async def process(self):
        pass

    @abstractmethod
    async def load(self):
        pass
