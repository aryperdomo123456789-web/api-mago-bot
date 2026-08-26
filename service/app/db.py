from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .core.config import Settings


settings = Settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=20, max_overflow=40)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
