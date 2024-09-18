from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import VECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from api.auth import decrypt_user_data

Base = declarative_base()


class UserSchema(Base):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "users"}

    id = Column(String, primary_key=True)
    email = Column(String, nullable=False, index=True)
    name = Column(String)
    given_name = Column(String)
    family_name = Column(String)
    picture = Column(String)


class UserKeySchema(Base):
    __tablename__ = "keys"
    __table_args__ = {"schema": "users"}

    id = Column(String, ForeignKey("users.profile.id"), primary_key=True)
    public_key = Column(BYTEA)
    private_key = Column(BYTEA)


class UserDataKeySchema(Base):
    __tablename__ = "data_keys"
    __table_args__ = {"schema": "users"}

    id = Column(String, primary_key=True)
    data_key = Column(BYTEA)


class SessionSchema(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "users"}

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.profile.id"), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    credentials = Column(BYTEA, nullable=True)


class ThreadSchema(Base):
    __tablename__ = "threads"
    __table_args__ = {"schema": "conversations"}

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.profile.id"), nullable=False)
    summary = Column(BYTEA, nullable=False)
    last_used = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    is_deleted = Column(Boolean, nullable=False, default=False)

    def decrypt(self, key: bytes) -> dict:
        return {
            "id": self.id,
            "summary": decrypt_user_data(key, self.summary),
            "last_used": self.last_used,
        }


class MessageSchema(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": "conversations"}

    id = Column(String, primary_key=True)
    thread_id = Column(String, ForeignKey("conversations.threads.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(BYTEA, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    model = Column(String)

    def decrypt(self, key: bytes) -> dict:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "role": self.role,
            "content": decrypt_user_data(key, self.content),
            "timestamp": self.timestamp,
            "model": self.model,
        }


class ContextSchema(Base):
    __tablename__ = "context_store"
    __table_args__ = {"schema": "agent"}

    id = Column(String, primary_key=True)
    thread_id = Column(String, ForeignKey("conversations.threads.id"), nullable=False)
    message_id = Column(String, ForeignKey("conversations.messages.id"), nullable=False)
    chunk = Column(Integer, nullable=False)
    timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    agent = Column(String, nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(VECTOR(1536), nullable=False)
