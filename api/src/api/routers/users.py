from typing import Optional

from fastapi import APIRouter
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import select

from api.clients import database_session
from api.database.schemas import SessionSchema
from api.database.schemas import ThreadSchema
from api.database.schemas import UserSchema
from api.models.models import Session
from api.models.models import User

router = APIRouter(tags=["users"], prefix="/users")


@router.get(
    "/{user_id}",
    response_model=Optional[User],
    summary="Gets a user by ID from memory.",
)
async def get_user_id(user_id: str):
    async with database_session() as db:
        query = await db.execute(select(UserSchema).filter(UserSchema.id == user_id))
        results = query.scalar_one_or_none()
    if results:
        return User.model_validate(results)
    return None


@router.put(
    "/save",
    summary="Saves a user to memory.",
)
async def put_user_save(user: User):
    async with database_session() as db:
        stmt = pg_insert(UserSchema).values(**user.model_dump())
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "email": stmt.excluded.email,
                "name": stmt.excluded.name,
                "given_name": stmt.excluded.given_name,
                "family_name": stmt.excluded.family_name,
                "picture": stmt.excluded.picture,
            },
        )
        await db.execute(stmt)
        await db.commit()


@router.get(
    "/session/{session_id}",
    response_model=Optional[Session],
    summary="Gets a stored session by cookie value (session_id).",
)
async def resume_session(session_id: str):
    async with database_session() as db:
        query = await db.execute(
            select(SessionSchema).filter(SessionSchema.id == session_id)
        )
        results = query.scalar_one_or_none()
    if results:
        user = await get_user_id(results.user_id)
        return Session.model_validate(
            {
                "id": results.id,
                "timestamp": results.timestamp,
                "user": user,
            }
        )
    return None


@router.put(
    "/session/save",
    summary="Saves a session to memory.",
)
async def save_session(session: Session):
    await put_user_save(session.user)

    async with database_session() as db:
        stmt = pg_insert(SessionSchema).values(
            user=session.user.id,
            **session.model_dump(exclude={"user"}),
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
        await db.execute(stmt)
        await db.commit()


@router.get(
    "/{user_id}/threads",
    summary="Gets all conversation threads for a user. Only returns the Thread IDs.",
)
async def get_user_threads_list(user_id: str) -> Optional[list[str]]:
    async with database_session() as db:
        query = await db.execute(
            select(ThreadSchema).filter(
                ThreadSchema.user == user_id,
                ThreadSchema.is_deleted.is_(False),
            )
        )
        results = query.scalars().all()
    if results:
        return [t.id for t in results]
    return None
