import os
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from crud import cache
from crud import database as db
from fastapi import BackgroundTasks
from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

from shared.models.session import Session
from shared.models.thread import ConversationThread
from shared.models.thread import ThreadMessage
from shared.models.user import User

POSTGRES_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"
POSTGRES = AsyncConnectionPool(POSTGRES_URL,open=False)

REDIS = Redis(
    host="redis",
    port=6379,
    decode_responses=True,
    auto_close_connection_pool=False
    )

@asynccontextmanager
async def lifespan(app:FastAPI):
    app.database = POSTGRES
    await app.database.open()
    await app.database.wait()

    app.cache = REDIS
    await app.cache.ping()

    yield

    await app.database.close()
    await app.cache.close()


app = FastAPI(lifespan=lifespan)


@app.get("/users/find",
    response_model=Optional[User],
    summary="Finds a user by ID from memory. 1 hour cache.")
async def find_user(user_id:str, background_tasks:BackgroundTasks):
    cached_user = await cache.get_user(app.cache, user_id)
    if cached_user:
        return cached_user
    db_user = await db.fetch_user(app.database, user_id)
    if db_user:
        background_tasks.add_task(cache.put_user, app.cache, db_user)
        return db_user
    return None


@app.put("/users/save", summary="Saves a user to memory.")
async def save_user(user:User):
    await cache.put_user(app.cache, user)
    await db.insert_user(app.database, user)


@app.get("/sessions/find",
    response_model=Optional[Session],
    summary="Loads a session from the database by cookie value (session_id). 1 hour cache.")
async def resume_session(session_id:UUID, background_tasks:BackgroundTasks):
    cached_session = await cache.get_session(app.cache, session_id)
    if cached_session:
        return cached_session

    db_session = await db.fetch_session(app.database, session_id)
    if db_session:
        background_tasks.add_task(cache.add_session, app.cache, db_session)
        return db_session
    return None


@app.put("/sessions/save",
    summary="Saves a session to memory.")
async def save_session(session:Session):
    await cache.add_session(app.cache, session)
    await db.insert_session(app.database, session)


@app.get("/threads/by_user",
    summary="Gets all conversation threads for a user.",
    response_model=ConversationThread)
async def get_threads_by_user(user_id:str):
    return None

@app.get("/threads/find",
    summary="Gets a conversation thread for a User by Thread ID.",
    response_model=ConversationThread)
async def find_thread(user_id:str, thread_id:str):
    return None

@app.patch("/threads/update",
    summary="Updates a conversation thread with a new Message for a User by Thread ID.")
async def put_thread(session_id:UUID, thread_id:str, message:ThreadMessage):
    return None
