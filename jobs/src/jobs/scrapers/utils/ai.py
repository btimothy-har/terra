import os

from langchain_openai import ChatOpenAI

LLM = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    max_tokens=2048,
    timeout=30,
    api_key=os.getenv("OPENAI_API_KEY"),
)
