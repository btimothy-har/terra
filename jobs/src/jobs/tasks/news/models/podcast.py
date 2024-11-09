import io
import random
import uuid
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydub import AudioSegment
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import TIMESTAMP

from jobs.config import ENV
from jobs.config import openai_client
from jobs.database import Base

AUDIO_MODEL = "tts-1" if ENV == "dev" else "tts-1-hd"

EXPERT_VOICES = ["alloy", "echo", "onyx", "shimmer"]


class PodcastSchema(Base):
    __tablename__ = "podcasts"
    __table_args__ = {"schema": "news"}

    id = Column(String, primary_key=True, nullable=False)
    date = Column(TIMESTAMP(timezone=True), nullable=False)
    title = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    tags = Column(ARRAY(String), nullable=False)
    transcript = Column(JSONB, nullable=False)
    articles = Column(ARRAY(String), nullable=False)
    audio_file = Column(String)


class PodcastMessage(BaseModel):
    role: Literal["host", "expert", "cohost"]
    content: str


class PodcastEpisode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    title: str
    summary: str
    tags: list[str]
    transcript: list[PodcastMessage]
    articles: list[str]
    audio: Any = None

    def _to_schema(self) -> dict:
        as_dict = self.model_dump()
        as_dict["audio_file"] = as_dict["audio"]
        del as_dict["audio"]
        return as_dict

    def create_audio(self) -> AudioSegment:
        combined_audio = AudioSegment.silent(duration=0)
        expert_voice = None

        for message in self.transcript:
            if message.role == "host":
                voice = "fable"
            elif message.role == "cohost":
                voice = "nova"
                expert_voice = None
            elif message.role == "expert":
                if expert_voice is None:
                    expert_voice = random.choice(EXPERT_VOICES)
                voice = expert_voice

            audio_file = openai_client.audio.speech.create(
                input=message.content[:4096],
                model=AUDIO_MODEL,
                voice=voice,
                response_format="wav",
                speed=1,
            )
            audio_segment = AudioSegment.from_file(
                io.BytesIO(audio_file.read()), format="wav"
            )
            combined_audio = (
                combined_audio + AudioSegment.silent(duration=2000) + audio_segment
            )

        self.audio = combined_audio
        return self.audio
