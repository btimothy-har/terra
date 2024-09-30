from datetime import UTC
from datetime import datetime
from functools import wraps

from aiolimiter import AsyncLimiter

from jobs.database import cache_client

openrouter_limiter = AsyncLimiter(20, 1)


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
