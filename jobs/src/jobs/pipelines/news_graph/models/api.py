from datetime import datetime
from typing import Any

from llama_index.core.schema import Document
from pydantic import BaseModel
from pydantic import model_validator


class NewsItem(BaseModel):
    item_id: str
    title: str
    content: str
    summary: str | None = None
    url: str
    image: str | None = None
    video: str | None = None
    publish_date: datetime
    author: str | None = None
    authors: list[str] | None = None
    category: str | None = None
    language: str | None = None
    source_country: str | None = None
    sentiment: float = None

    @model_validator(mode="before")
    @classmethod
    def convert_keys(cls, data: Any):
        if not isinstance(data, dict):
            return data

        if "id" in data:
            data["item_id"] = str(data.pop("id"))
        if "text" in data:
            data["content"] = data.pop("text")
        if "catgory" in data:
            data["category"] = data.pop("catgory")
        return data

    def as_document(self) -> Document:
        document = Document(
            doc_id=self.item_id,
            text=self.content,
            metadata=self.model_dump(
                mode="json",
                exclude={"content", "item_id", "image", "video", "language"},
            ),
        )
        return document


class NewsAPIResponse(BaseModel):
    offset: int
    number: int
    available: int
    news: list[dict]
