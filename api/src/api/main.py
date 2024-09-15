from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis import exceptions as redis_exceptions
from redis.commands.search.indexDefinition import IndexDefinition
from redis.commands.search.indexDefinition import IndexType

import api.config as config
from api.clients import logger
from api.clients import postgres
from api.clients import redis
from api.routers import messages_router
from api.routers import threads_router
from api.routers import users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.database = postgres
    app.cache = redis

    try:
        await app.cache.ft(config.CONTEXT_INDEX).create_index(
            fields=config.CONTEXT_SCHEMA,
            definition=IndexDefinition(
                prefix=[config.CONTEXT_PREFIX + ":"], index_type=IndexType.JSON
            ),
        )
    except redis_exceptions.ResponseError:
        index_info = await app.cache.ft(config.CONTEXT_INDEX).info()
        logger.warning(
            f"Index {config.CONTEXT_INDEX} already exists. "
            f"{index_info['num_docs']} documents indexed with "
            f"{index_info['hash_indexing_failures']} failures."
        )
    else:
        index_info = await app.cache.ft(config.CONTEXT_INDEX).info()
        logger.warning(
            f"Index {config.CONTEXT_INDEX} created. "
            f"{index_info['num_docs']} documents indexed with "
            f"{index_info['hash_indexing_failures']} failures."
        )

    await app.database.open()
    logger.info("Database and cache connections established.")

    yield

    await app.database.close()
    await app.cache.close()


app = FastAPI(lifespan=lifespan)

app.include_router(users_router)
app.include_router(threads_router)
app.include_router(messages_router)
