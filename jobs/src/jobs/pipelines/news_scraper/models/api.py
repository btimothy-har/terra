from datetime import datetime
from typing import Any

from llama_index.core.schema import Document
from pydantic import BaseModel
from pydantic import model_validator
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import TIMESTAMP

from jobs.database.schemas import Base


class NewsItemSchema(Base):
    __tablename__ = "raw_items"
    __table_args__ = {"schema": "news"}

    item_id = Column(String, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    summary = Column(String)
    url = Column(String, nullable=False)
    image = Column(String)
    video = Column(String)
    publish_date = Column(TIMESTAMP(timezone=True), nullable=False)
    author = Column(String)
    authors = Column(ARRAY(String))
    language = Column(String)
    category = Column(String)
    source_country = Column(String)
    sentiment = Column(Float)
    batch_id = Column(String, nullable=False)


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
