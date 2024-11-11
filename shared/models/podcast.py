import uuid
from datetime import UTC
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class PodcastMessage(BaseModel):
    role: Literal["host", "expert", "cohost"]
    content: str


class PodcastEpisode(BaseModel):
    episode_num: int = 0
    episode_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    title: str
    summary: str
    geos: list[str]
    tags: list[str]
    transcript: list[PodcastMessage]
    articles: list[str]
