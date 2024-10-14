import asyncio
from functools import wraps
from typing import Any

from aiolimiter import AsyncLimiter
from tqdm.asyncio import tqdm_asyncio


def rate_limited_task(max_rate: int = 10, interval: int = 1):
    task_limiter = AsyncLimiter(max_rate, interval)

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            async with task_limiter:
                return await func(self, *args, **kwargs)

        return wrapper

    return decorator


def sequential_task(concurrent_tasks: int = 1):
    sem = asyncio.Semaphore(concurrent_tasks)

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            async with sem:
                return await func(self, *args, **kwargs)

        return wrapper

    return decorator


async def tqdm_iterable(iterable, desc: str):
    async for item in tqdm_asyncio(iterable, desc=desc):
        yield item


def clean_string(s: Any) -> Any:
    if isinstance(s, str):
        return s.encode("utf-8", errors="ignore").decode("utf-8").replace("\x00", "")
    elif isinstance(s, list):
        return [clean_string(item) for item in s]
    elif isinstance(s, dict):
        return {k: clean_string(v) for k, v in s.items()}
    return s
