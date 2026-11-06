from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import Settings

class Base(DeclarativeBase): pass

def make_session_factory(url: str):
    if url.startswith("sqlite"):
        Path("data").mkdir(exist_ok=True)
    engine = create_async_engine(url, pool_pre_ping=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db(engine):
    from app import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
