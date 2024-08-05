from typing import Optional

from crud import cache
from crud import database as db
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Request

from shared.models.session import Session
from shared.models.user import User

router = APIRouter(
    tags=["users"],
    prefix="/users"
)

@router.get("/id",
    response_model=Optional[User],
    summary="Gets a user by ID from memory. 1 hour cache.")
async def get_user_id(
    user_id:str,
    request:Request,
    background_tasks:BackgroundTasks):

    cached_user = await cache.get_user(request.app.cache, user_id)
    if cached_user:
        return cached_user

    db_user = await db.fetch_user(request.app.database, user_id)
    if db_user:
        background_tasks.add_task(cache.put_user, request.app.cache, db_user)
        return db_user
    return None

@router.put("/save",
    summary="Saves a user to memory.")
async def put_user_save(
    user:User,
    request:Request,
    background_tasks:BackgroundTasks):

    background_tasks.add_task(db.insert_user, request.app.database, user)

    await cache.put_user(request.app.cache, user)

@router.get("/session/id",
    response_model=Optional[Session],
    summary="Gets a stored session by cookie value (session_id). 1 hour cache.")
async def resume_session(
    session_id:str,
    request:Request,
    background_tasks:BackgroundTasks):

    cached_session = await cache.get_session(request.app.cache, session_id)
    if cached_session:
        return cached_session

    db_session = await db.fetch_session(request.app.database, session_id)
    if db_session:
        background_tasks.add_task(cache.put_session, request.app.cache, db_session)
        return db_session
    return None

@router.put("/session/save",
    summary="Saves a session to memory.")
async def save_session(
    session:Session,
    request:Request,
    background_tasks:BackgroundTasks):

    background_tasks.add_task(db.insert_session, request.app.database, session)

    await cache.put_session(request.app.cache, session)
    await put_user_save(session.user, request, background_tasks)

@router.get("/threads",
    summary="Gets all conversation threads for a user. Only returns the Thread IDs.")
async def get_user_threads_list(
    user_id:str,
    request:Request,
    background_tasks:BackgroundTasks) -> Optional[list[str]]:

    cached_threads = await cache.get_user_threads(request.app.cache, user_id)
    print(cached_threads)
    if cached_threads:
        return cached_threads

    db_threads = await db.fetch_user_threads(request.app.database, user_id)
    print(db_threads)
    if db_threads:
        background_tasks.add_task(cache.put_user_threads, request.app.cache, user_id, db_threads)
        return db_threads
    return None
