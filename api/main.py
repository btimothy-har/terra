from contextlib import asynccontextmanager
from uuid import UUID
from typing import Optional

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Request


from shared.models.session import Session
from shared.models.user import User

from clients.postgres import get_postgres_client
from clients.redis import get_redis_client


# REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
# REDIS_PORT = os.getenv('REDIS_PORT', 6379)
# REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# REDIS_HOST = "redis"
# REDIS_PORT = 6379

@asynccontextmanager
async def lifespan(app:FastAPI):
    print("startup")
    app.cache = await get_redis_client()
    app.database = await get_postgres_client()
    yield

    app.database.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def main():
    sql = """
        SELECT *
        FROM
            users.sessions as ts
        ORDER BY
            ts.timestamp DESC
        LIMIT 1;
        """

    with app.database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            raw_data = cursor.fetchone()
    return raw_data

@app.get("/chat")
async def chat(x:str):
    return {"x":f"hello world {x}"}

@app.get("/tal")
async def talk(x:str):
    return {"x":f"hellotalk world {x}"}

@app.put("/users/save")
async def save_user(user:User) -> None:
    insert_user = """
        INSERT INTO users.googleid (uid, email, name, given_name, family_name, picture)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (uid) DO UPDATE SET
            email = EXCLUDED.email,
            name = EXCLUDED.name,
            given_name = EXCLUDED.given_name,
            family_name = EXCLUDED.family_name,
            picture = EXCLUDED.picture;
        """

    async with app.database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                insert_user,
                (
                    user.id,
                    user.email,
                    user.name,
                    user.given_name,
                    user.family_name,
                    user.picture
                    )
                )
    return None

@app.get("/session/find", response_model=Optional[Session])
async def resume_session(session_id:UUID):
    sql = f"""
        SELECT
            ts.uid,
            ts.timestamp,
            tu.email,
            tu.name,
            tu.given_name,
            tu.family_name,
            tu.picture,
            ts.credentials
        FROM
            users.sessions as ts
            JOIN users.googleid as tu ON ts.uid = tu.uid
        WHERE
            ts.sid='{session_id}'
        ORDER BY
            ts.timestamp DESC
        LIMIT 1;
        """

    async with app.database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(sql)
            raw_data = await cursor.fetchone()

            if raw_data:
                return Session(
                    id=session_id,
                    timestamp=raw_data[1],
                    user=User(
                        id=raw_data[0],
                        email=raw_data[2],
                        name=raw_data[3],
                        given_name=raw_data[4],
                        family_name=raw_data[5],
                        picture=raw_data[6]
                        ),
                    credentials=raw_data[7]
                    )
            return None

@app.put("/session/save")
async def save_session(session:Session) -> None:

    insert_session = """
        INSERT INTO users.sessions (sid, uid, timestamp, credentials)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (sid) DO UPDATE
        SET timestamp = EXCLUDED.timestamp,
            credentials = EXCLUDED.credentials
        """

    async with app.database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                insert_session,
                (session.id, session.user.id, session.timestamp, session.credentials)
                )

    return None
