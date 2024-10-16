import os

import ell
import requests
from ell.stores.sql import PostgresStore
from openai import OpenAI

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


def _get_models():
    response = requests.get("https://openrouter.ai/api/v1/models")
    return response.json()


def init_ell():
    ell.init(
        store=PostgresStore(
            db_uri=f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/{os.getenv('ELL_DB')}"
        ),
        lazy_versioning=False,
        default_client=openrouter_client,
        autocommit_model="openai/gpt-4o-mini",
    )
    openrouter_models = _get_models()["data"]
    for model in openrouter_models:
        ell.config.register_model(model["id"], openrouter_client)
