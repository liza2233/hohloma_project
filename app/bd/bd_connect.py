import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from decouple import config

DATABASE_URL = (
    f"postgresql+asyncpg://{config("DB_USER")}:{config("DB_PASSWORD")}"
    f"@{config("DB_HOST")}:{config("DB_PORT", "5432")}/{config("DB_NAME")}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)
