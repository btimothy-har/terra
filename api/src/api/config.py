import os

from redis.commands.search.field import NumericField
from redis.commands.search.field import TextField
from redis.commands.search.field import VectorField

POSTGRES_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"

REDIS_PORT = 6379

CHROMA_PORT = 8001

CONTEXT_PREFIX = "ctx"
CONTEXT_INDEX = f"idx:{CONTEXT_PREFIX}"
CONTEXT_DIM = 1536

CONTEXT_SCHEMA = (
    TextField("$.thread_id", no_stem=True, as_name="thread_id"),
    TextField("$.message_id", no_stem=True, as_name="message_id"),
    NumericField("$.message_num", as_name="message_num"),
    NumericField("$.chunk_num", as_name="chunk_num"),
    TextField("$.timestamp", as_name="timestamp"),
    TextField("$.title", as_name="title"),
    TextField("$.content", as_name="content"),
    VectorField(
        "$.embeddings",
        "FLAT",
        {
            "TYPE": "FLOAT32",
            "DIM": CONTEXT_DIM,
            "DISTANCE_METRIC": "COSINE",
        },
        as_name="embeddings",
    ),
)
