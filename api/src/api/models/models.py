import io
import os
import random
from datetime import datetime
from typing import Self

from pydantic import BaseModel
from pydub import AudioSegment

import shared.models as models
from api.auth import decrypt_user_data
from api.auth import encrypt_user_data
from api.config import ENV
from api.utils import openai_client


class User(models.User):
    pass


class Session(models.Session):
    pass


class ConversationThread(models.ConversationThread):
    last_used: datetime
    messages: None = None

    def encrypt(self, key: bytes, **kwargs) -> dict:
        model_dict = self.model_dump(exclude={"messages"}, **kwargs)
        model_dict["summary"] = encrypt_user_data(key, model_dict["summary"])
        return model_dict

    @classmethod
    def decrypt(cls, schema, key: bytes) -> Self:
        model_dict = {
            "id": schema.id,
            "summary": decrypt_user_data(key, schema.summary),
            "last_used": schema.last_used,
        }
        return cls.model_validate(model_dict)


class ThreadMessage(models.ThreadMessage):
    def encrypt(self, key: bytes, **kwargs) -> dict:
        model_dict = self.model_dump(**kwargs)
        model_dict["content"] = encrypt_user_data(key, model_dict["content"])
        return model_dict

    @classmethod
    def decrypt(cls, schema, key: bytes) -> Self:
        model_dict = {
            "id": schema.id,
            "thread_id": schema.thread_id,
            "role": schema.role,
            "content": decrypt_user_data(key, schema.content),
            "timestamp": schema.timestamp,
            "model": schema.model,
        }
        return cls.model_validate(model_dict)


class ContextMessage(models.ContextMessage):
    pass


class ContextChunk(BaseModel):
    timestamp: datetime
    agent: str
    content: str


AUDIO_MODEL = "tts-1" if ENV == "dev" else "tts-1-hd"


EXPERT_VOICES = ["alloy", "echo", "onyx", "shimmer"]


class PodcastEpisode(models.PodcastEpisode):
    @property
    def audio_file(self) -> AudioSegment:
        return f"/etc/artifacts/podcast_audio/{self.episode_id}.mp3"

    @property
    def audio_file_exists(self) -> bool:
        return os.path.exists(self.audio_file)

    def create_audio(self, create_if_missing: bool = True) -> io.BytesIO | None:
        if self.audio_file_exists:
            podcast_audio = AudioSegment.from_file(self.audio_file)

        elif create_if_missing:
            podcast_audio = AudioSegment.silent(duration=0)
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
                    response_format="mp3",
                    speed=1,
                )
                audio_segment = AudioSegment.from_file(
                    io.BytesIO(audio_file.read()), format="mp3"
                )
                podcast_audio = (
                    podcast_audio + AudioSegment.silent(duration=2000) + audio_segment
                )

        else:
            return None

        audio_data = podcast_audio.export(
            out_f=self.audio_file if not self.audio_file_exists else None,
            format="mp3",
        )

        return audio_data
