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

Base = declarative_base()


class UserSchema(Base):
    __tablename__ = "profile"
    __table_args__ = {"schema": "users"}

    id = Column(String, primary_key=True)
    email = Column(String, nullable=False, index=True)
    name = Column(String)
    given_name = Column(String)
    family_name = Column(String)
    picture = Column(String)


class SessionSchema(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "users"}

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.profile.id"), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)


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


class MessageSchema(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": "conversations"}

    id = Column(String, primary_key=True)
    thread_id = Column(String, ForeignKey("conversations.threads.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(BYTEA, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    model = Column(String)


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
