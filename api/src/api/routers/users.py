from typing import Annotated
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from api.database.schemas import ThreadSchema
from api.database.schemas import UserSchema
from api.models.models import User
from api.utils import database_session

router = APIRouter(tags=["users"], prefix="/users")

DatabaseSession = Annotated[AsyncSession, Depends(database_session)]


@router.get(
    "/{user_id}",
    response_model=Optional[User],
    summary="Gets a user by ID from memory.",
)
async def get_user_id(user_id: str, db: DatabaseSession):
    query = await db.execute(select(UserSchema).filter(UserSchema.id == user_id))
    results = query.scalar_one_or_none()
    if results:
        return User.model_validate(results)
    return None


@router.put(
    "/save",
    summary="Saves a user to memory.",
)
async def put_user_save(user: User, db: DatabaseSession):
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
    "/{user_id}/threads",
    summary="Gets all conversation threads for a user. Only returns the Thread IDs.",
)
async def get_user_threads_list(
    user_id: str, db: Annotated[AsyncSession, Depends(database_session)]
) -> Optional[list[str]]:
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
