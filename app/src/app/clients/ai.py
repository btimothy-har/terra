import os
from enum import Enum

from langchain_openai import ChatOpenAI


class OpenRouterModels(Enum):
    GOOGLE_GEMINI_FLASH = "google/gemini-flash-1.5"
    GOOGLE_GEMINI_PRO = "google/gemini-pro-1.5"
    GOOGLE_GEMMA2_27B = "google/gemma-2-27b-it"
    ANTHROPIC_CLAUDE_SONNET = "anthropic/claude-3.5-sonnet"
    ANTHROPIC_CLAUDE_HAIKU = "anthropic/claude-3-haiku"
    ANTHROPIC_CLAUDE_OPUS = "anthropic/claude-3-opus"
    DEEPSEEK_CHAT_2_5 = "deepseek/deepseek-chat"
    DEEPSEEK_CODER_2 = "deepseek/deepseek-coder"
    OPENAI_GPT4O = "openai/gpt-4o"
    OPENAI_GPT4O_MINI = "openai/gpt-4o-mini"
    MATTSHUMER_REFLECTION_70B = "mattshumer/reflection-70b"
    MISTRALAI_MISTRALNEMO = "mistralai/mistral-nemo"


AVAILABLE_MODELS = [m.value for m in OpenRouterModels]


def get_client(model: str, temp: float = 0.2):
    return ChatOpenAI(
        model=model,
        temperature=temp,
        timeout=30,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=os.getenv("OPENROUTER_BASE_URL"),
    )
