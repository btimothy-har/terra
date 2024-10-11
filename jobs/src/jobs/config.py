import os

import ell
import requests
from openai import OpenAI

ENV = os.getenv("ENV", "dev")

openrouter_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": os.getenv("GITHUB_URL"),
        "X-Title": f"terra-jobs-{ENV}",
    },
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
        store="/src/logdir",
        autocommit=True,
        default_client=openrouter_client,
    )
    openrouter_models = _get_models()["data"]
    for model in openrouter_models:
        ell.config.register_model(model["id"], openrouter_client)
