from typing import Annotated
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

import api.auth as auth
from api.data.schemas import SessionSchema
from api.models import Session
from api.utils import database_session

router = APIRouter(tags=["session"], prefix="/session")

DatabaseSession = Annotated[AsyncSession, Depends(database_session)]


@router.put(
    "/save",
    summary="Saves a session to memory.",
)
async def save_session(session: Session, db: DatabaseSession):
    stmt = pg_insert(SessionSchema).values(
        **session.model_dump(),
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
    await db.execute(stmt)
    await db.commit()


@router.get(
    "/{session_id}",
    response_model=Optional[Session],
    summary="Gets a stored session by cookie value (session_id).",
)
async def resume_session(session_id: str, db: DatabaseSession):
    query = await db.execute(
        select(SessionSchema).filter(SessionSchema.id == session_id)
    )
    results = query.scalar_one_or_none()
    if results:
        return Session.model_validate(results, from_attributes=True)
    return None


@router.post(
    "/authorize",
    response_model=auth.Token,
    summary="Authorizes a session and returns a JWT token.",
)
async def authorize_session(
    payload: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    key_handler = auth.UserKeyHandler(payload.password)

    if not await key_handler.is_valid_session(payload.username):
        raise HTTPException(status_code=401, detail="Invalid session or user.")

    public_key = await key_handler.get_public_key()

    if not public_key:
        public_key = await key_handler.generate_rsa_keys()

    token = key_handler.create_api_token(payload.username)
    return token
