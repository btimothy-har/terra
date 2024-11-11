import json
import os

import ell
import requests
from ell.stores.sql import PostgresStore
from openai import AsyncOpenAI
from openai import OpenAI

from jobs.database import cache_client

ENV = os.getenv("ENV", "dev")
API_ENDPOINT = "http://api:8000"

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
async_openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

pplx_client = OpenAI(
    api_key=os.getenv("PPLX_API_KEY"), base_url="https://api.perplexity.ai"
)
async_pplx_client = AsyncOpenAI(
    api_key=os.getenv("PPLX_API_KEY"), base_url="https://api.perplexity.ai"
)


def _get_openrouter_models():
    raw_models = None
    with cache_client() as cache:
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            )
            response.raise_for_status()
            raw_models = response.text
        except Exception:
            raw_models = cache.get("openrouter_models")
        else:
            cache.set("openrouter_models", raw_models)

    if not raw_models:
        raise Exception("Failed to fetch openrouter models")
    return json.loads(raw_models)


def _get_openai_models():
    raw_models = None
    with cache_client() as cache:
        try:
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            )
            response.raise_for_status()
            raw_models = response.text
        except Exception:
            raw_models = cache.get("openai_models")
        else:
            cache.set("openai_models", raw_models)

    if not raw_models:
        raise Exception("Failed to fetch openai models")
    return json.loads(raw_models)


def init_ell():
    ell.init(
        store=PostgresStore(
            db_uri=f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/{os.getenv('ELL_DB')}"
        ),
        lazy_versioning=False,
        default_client=openrouter_client,
        autocommit_model="gpt-4o-mini",
    )
    openrouter_models = _get_openrouter_models()["data"]
    for model in openrouter_models:
        ell.config.register_model(model["id"], openrouter_client)

    openai_models = _get_openai_models()["data"]
    for model in openai_models:
        ell.config.register_model(model["id"], openai_client)
