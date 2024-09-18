from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers import threads_router
from api.routers import users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from api.database.schemas import Base
    from api.utils import engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield


app = FastAPI(lifespan=lifespan)

app.include_router(users_router)
app.include_router(threads_router)
