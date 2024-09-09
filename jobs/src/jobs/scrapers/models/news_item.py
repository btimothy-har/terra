from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TIMESTAMP

from .base import Base


class NewsItemSchema(Base):
    __tablename__ = "raw_items"
    __table_args__ = {"schema": "news"}

    _id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    url = Column(String, nullable=False)
    image = Column(String, nullable=True)
    video = Column(String, nullable=True)
    publish_date = Column(TIMESTAMP(timezone=True), nullable=False)
    author = Column(String, nullable=False)
    authors = Column(String, nullable=True)
    language = Column(String, nullable=True)
    category = Column(String, nullable=True)
    source_country = Column(String, nullable=True)
    sentiment = Column(Float, nullable=True)


class NewsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: str
    title: str
    content: str
    summary: str
    url: str
    image: str | None
    video: str | None
    publish_date: datetime
    author: str
    authors: list[str] | None
    language: str | None
    category: str | None
    source_country: str | None
    sentiment: float | None
