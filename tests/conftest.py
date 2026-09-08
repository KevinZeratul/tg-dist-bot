"""pytest 公共 fixture：为每个测试提供独立的 SQLite 会话工厂。"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tgdistbot.db.models import Base


@pytest.fixture
async def session_factory(tmp_path):
    """每个测试用独立的临时 SQLite 文件，互不干扰。"""
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()
