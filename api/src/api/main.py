from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.clients import chromadb
from api.clients import logger
from api.clients import postgres
from api.clients import redis
from api.routers import messages_router
from api.routers import threads_router
from api.routers import users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.database = await postgres()
    app.state.cache = await redis()
    app.state.vector = await chromadb()

    logger.info("Database and cache connections established.")

    yield

    await app.state.database.close()
    await app.state.cache.close()


app = FastAPI(lifespan=lifespan)

app.include_router(users_router)
app.include_router(threads_router)
app.include_router(messages_router)
