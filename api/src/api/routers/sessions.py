from typing import Annotated
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import select

import api.auth as auth
from api.clients import database_session
from api.database.schemas import SessionSchema
from api.models.models import Session

from .users import get_user_id
from .users import put_user_save

router = APIRouter(tags=["session"], prefix="/session")


@router.put(
    "/save",
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
    "/{session_id}",
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
                "credentials": results.credentials,
            }
        )
    return None


@router.post(
    "/authorize",
    response_model=auth.Token,
    summary="Authorizes a session and returns a JWT token.",
)
async def authorize_session(payload: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # username = session id
    # password = google uid

    key_handler = auth.UserKeyHandler(payload.password)

    if not await key_handler.is_valid_session(payload.username):
        raise HTTPException(status_code=401, detail="Invalid session or user.")

    public_key = await key_handler.get_public_key()

    if not public_key:
        public_key = await key_handler.generate_rsa_keys()

    token = key_handler.create_api_token(payload.username)
    return token
