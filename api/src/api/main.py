import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers import sessions_router
from api.routers import threads_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from api.database.context import setup_context_collection
    from api.database.schemas import Base
    from api.utils import engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await asyncio.to_thread(setup_context_collection)

    yield


app = FastAPI(lifespan=lifespan)

app.include_router(threads_router)
app.include_router(sessions_router)
