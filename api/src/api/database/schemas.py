from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class UserKeySchema(Base):
    __tablename__ = "keys"
    __table_args__ = {"schema": "users"}

    id = Column(String, primary_key=True)
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
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    credentials = Column(BYTEA, nullable=True)


class ThreadSchema(Base):
    __tablename__ = "threads"
    __table_args__ = {"schema": "conversations"}

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
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
    __tablename__ = "context"
    __table_args__ = {"schema": "agent"}

    id = Column(String, primary_key=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    agent = Column(String, nullable=False)
    content = Column(String, nullable=False)
