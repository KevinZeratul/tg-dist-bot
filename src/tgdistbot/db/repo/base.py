"""仓库基类：持有会话工厂，子类在各自方法里自行开/关会话。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# 约定：0 代表"根目录"（即 parent_id 为空 / 文件未归档到任何文件夹）。
# 真实目录的自增 id 从 1 开始，所以 0 不会冲突。
ROOT_FOLDER_ID = 0


def is_root(folder_id: int | None) -> bool:
    """目录 id 为空或 0 都视为根目录。"""
    return folder_id is None or folder_id == ROOT_FOLDER_ID


class BaseRepo:
    """所有仓库的基类。

    约定：每个方法内部用 ``async with self.session_factory() as session:``
    自行管理会话，方法返回 DTO 或标量，绝不把 ORM 对象泄露给上层。
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
