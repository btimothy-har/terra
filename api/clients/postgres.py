import os

from psycopg_pool import AsyncConnectionPool


async def get_postgres_client() -> AsyncConnectionPool:
    db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"
    pool = AsyncConnectionPool(db_url,open=False)
    await pool.open()
    await pool.wait()

    return pool
