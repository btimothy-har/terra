import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

POSTGRES_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"

engine = create_engine(POSTGRES_URL)

Session = sessionmaker(bind=engine)
session = Session()


def init_db():
    from .models import Base

    Base.metadata.create_all(engine)
