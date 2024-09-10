from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import TIMESTAMP

from .base import Base


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


class NewsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: str
    title: str
    content: str
    summary: str | None
    url: str
    image: str | None
    video: str | None
    publish_date: datetime
    author: str | None
    authors: list[str] | None
    language: str | None
    category: str | None
    source_country: str | None
    sentiment: float | None
