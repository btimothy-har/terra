import os
from enum import Enum

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI


class OpenAIModels(Enum):
    if os.getenv("OPENAI_API_KEY"):
        GPT_4O_MINI = "gpt-4o-mini"
        GPT_4O = "gpt-4o"
        GPT_4_TURBO = "gpt-4-turbo"

class GoogleModels(Enum):
    if os.getenv("GOOGLE_API_KEY"):
        GEMINI_PRO = "gemini-1.5-pro"
        GEMINI_FLASH = "gemini-1.5-flash"

AVAILABLE_MODELS = [
    *[m.value for m in OpenAIModels],
    *[m.value for m in GoogleModels]
    ]

def get_client(model:str, temp:float=0.2, max_tokens:int=2048):
    if model in set([m.value for m in OpenAIModels]):
        return ChatOpenAI(
            model=model,
            temperature=temp,
            max_tokens=max_tokens,
            timeout=30,
            api_key=os.getenv("OPENAI_API_KEY"),
            )

    if model in set([m.value for m in GoogleModels]):
        return ChatGoogleGenerativeAI(
            model=model,
            api_key=os.getenv("GOOGLE_API_KEY"),
            temp=temp,
            max_output_tokens=max_tokens
        )
