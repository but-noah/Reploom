from sqlmodel import Session, create_engine, SQLModel, text

from app.models import models
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)


def get_session():
    """FastAPI dependency to get database session."""
    with Session(engine) as session:
        yield session


def init_db():
    # Enable vector extension
    with Session(engine) as db_session:
        db_session.exec(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db_session.commit()

    SQLModel.metadata.create_all(engine)
