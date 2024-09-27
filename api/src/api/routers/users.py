from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.utils import database_session

router = APIRouter(tags=["users"], prefix="/users")

DatabaseSession = Annotated[AsyncSession, Depends(database_session)]


# @router.get(
#     "/{user_id}",
#     response_model=Optional[User],
#     summary="Gets a user by ID from memory.",
# )
# async def get_user_id(user_id: str, db: DatabaseSession):
#     query = await db.execute(select(UserSchema).filter(UserSchema.id == user_id))
#     results = query.scalar_one_or_none()
#     if results:
#         return User.model_validate(results, from_attributes=True)
#     return None


# @router.put(
#     "/save",
#     summary="Saves a user to memory.",
# )
# async def put_user_save(user: User, db: DatabaseSession):
#     stmt = pg_insert(UserSchema).values(**user.model_dump())
#     stmt = stmt.on_conflict_do_update(
#         index_elements=["id"],
#         set_={
#             "email": stmt.excluded.email,
#             "name": stmt.excluded.name,
#             "given_name": stmt.excluded.given_name,
#             "family_name": stmt.excluded.family_name,
#             "picture": stmt.excluded.picture,
#         },
#     )
#     await db.execute(stmt)
#     await db.commit()
