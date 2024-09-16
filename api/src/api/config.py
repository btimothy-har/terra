import os

POSTGRES_URL = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"

EMBED_DIM = 1536
EMBED_MODEL = "text-embedding-3-small"
