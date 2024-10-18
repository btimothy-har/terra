import os

import aiohttp
import ell
from ell.stores.sql import PostgresStore
from openai import OpenAI

from jobs.database import cache_client

ENV = os.getenv("ENV", "dev")

openrouter_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

openrouter_extra_body = {
    "provider": {
        "order": ["DeepInfra", "Hyperbolic"],
        "data_collection": "deny",
        "allow_fallbacks": True,
    },
    "transforms": [],
}

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def _get_openrouter_models():
    models = None
    async with cache_client() as cache:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://openrouter.ai/api/v1/models"
                ) as response:
                    response.raise_for_status()
                    models = await response.json()
        except Exception:
            models = await cache.get("openrouter_models")
        else:
            await cache.set("openrouter_models", models)

    if not models:
        raise Exception("Failed to fetch openrouter models")
    return models


async def _get_openai_models():
    models = None
    async with cache_client() as cache:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                ) as response:
                    response.raise_for_status()
                    models = await response.json()
        except Exception:
            models = await cache.get("openai_models")
        else:
            await cache.set("openai_models", models)

    if not models:
        raise Exception("Failed to fetch openai models")
    return models


async def init_ell():
    ell.init(
        store=PostgresStore(
            db_uri=f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/{os.getenv('ELL_DB')}"
        ),
        lazy_versioning=False,
        default_client=openrouter_client,
        autocommit_model="gpt-4o-mini",
    )
    openrouter_models = await _get_openrouter_models()["data"]
    for model in openrouter_models:
        ell.config.register_model(model["id"], openrouter_client)

    openai_models = await _get_openai_models()["data"]
    for model in openai_models:
        ell.config.register_model(model["id"], openai_client)
