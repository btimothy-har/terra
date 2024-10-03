import asyncio
import os
from functools import wraps

from aiolimiter import AsyncLimiter
from langchain_openai import ChatOpenAI
from tqdm.asyncio import tqdm_asyncio


def get_llm(model: str):
    return ChatOpenAI(
        model=model,
        temperature=0,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )


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
