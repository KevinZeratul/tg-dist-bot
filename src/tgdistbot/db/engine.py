"""异步数据库引擎与会话工厂。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine_and_sessionmaker(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """根据 URL 创建异步引擎和会话工厂。

    ``expire_on_commit=False``：提交后 ORM 对象仍保留已加载的属性，
    方便仓库方法返回对象后直接读取标量字段。
    """
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory
