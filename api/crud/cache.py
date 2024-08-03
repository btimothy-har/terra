import json
from typing import Optional

from redis.asyncio import Redis

from shared.models.session import Session
from shared.models.user import User


##############################
##### USER CACHE         #####
##############################
async def put_user(cache:Redis, user:User):
    await cache.set(
        name=f"user:{user.id}",
        value=user.model_dump_json(exclude={"id":True}),
        ex=3600
        )

async def get_user(cache:Redis, user_id:str) -> Optional[User]:
    user_data = await cache.get(f"user:{user_id}")
    if user_data:
        user_data = json.loads(user_data)
        return User(id=user_id,**user_data)
    return None


##############################
##### SESSION CACHE      #####
##############################
async def add_session(cache:Redis, session:User):
    session_model = session.model_dump_json(
        include={
            "timestamp":True,
            "credentials":True,
            "user": {"id":True}
            }
        )
    await cache.set(
        name=f"session:{session.id}",
        value=session_model,
        ex=3600
        )
    await put_user(cache, session.user)

async def get_session(cache:Redis, session_id:str) -> Optional[Session]:
    print("getting session from cache")
    session_data = await cache.get(f"session:{session_id}")
    if session_data:
        session_data = json.loads(session_data)
        user_id = session_data.pop("user")["id"]
        user = await get_user(cache, user_id)
        if user:
            return Session(id=session_id, user=user, **session_data)
    return None
