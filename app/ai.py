import os
from enum import Enum

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

load_dotenv()

class OpenAIModels(Enum):
    if os.getenv("OPENAI_API_KEY"):
        GPT_4O_MINI = "gpt-4o-mini"
        GPT_4O = "gpt-4o"
        GPT_4_TURBO = "gpt-4-turbo"

class OllamaModels(Enum):
    LLAMA3_1 = "llama3.1:8b"
    if os.getenv("ENV", "development") == "production":
        CODE_LLAMA = "codellama:7b"
        GEMMA2 = "gemma2:9b"
        MISTRAL_NEMO = "mistral-nemo"

AVAILABLE_MODELS = [*[m.value for m in OllamaModels],*[m.value for m in OpenAIModels]]
MAX_TOKEN_VALUES = [512, 1024, 2048, 4096, 8192]

def get_client(model:str, temp:float, max_tokens:int):
    if model in set([m.value for m in OpenAIModels]):
        return ChatOpenAI(
            model=model,
            temperature=temp,
            max_tokens=max_tokens,
            timeout=30,
            api_key=os.getenv("OPENAI_API_KEY"),
            )

    if model in set([m.value for m in OllamaModels]):
        return ChatOllama(
            model=model,
            temperature=temp,
            num_predict=max_tokens,
        )
