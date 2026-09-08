"""目录仓库：目录树相关的增删改查。"""

from __future__ import annotations

from sqlalchemy import select, update

from ..models import Folder, MediaItem, utcnow
from ..schemas import FolderDTO
from .base import BaseRepo, is_root


def _to_dto(folder: Folder) -> FolderDTO:
    return FolderDTO(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        access_mode=folder.access_mode,
    )


def _parent_clause(parent_id: int | None):
    """parent_id 为空或 0 都表示根目录。"""
    if is_root(parent_id):
        return Folder.parent_id.is_(None)
    return Folder.parent_id == parent_id


class FolderRepo(BaseRepo):
    async def create(self, name: str, parent_id: int | None = None) -> FolderDTO:
        async with self.session_factory() as session:
            folder = Folder(name=name, parent_id=None if is_root(parent_id) else parent_id)
            session.add(folder)
            await session.commit()
            await session.refresh(folder)
            return _to_dto(folder)

    async def get(self, folder_id: int) -> FolderDTO | None:
        async with self.session_factory() as session:
            folder = await session.get(Folder, folder_id)
            if folder is None or folder.deleted_at is not None:
                return None
            return _to_dto(folder)

    async def list_children(self, parent_id: int | None) -> list[FolderDTO]:
        """列出某目录下的子目录（不含文件）。"""
        async with self.session_factory() as session:
            result = await session.scalars(
                select(Folder)
                .where(_parent_clause(parent_id), Folder.deleted_at.is_(None))
                .order_by(Folder.name)
            )
            return [_to_dto(f) for f in result]

    async def rename(self, folder_id: int, name: str) -> bool:
        async with self.session_factory() as session:
            folder = await session.get(Folder, folder_id)
            if folder is None or folder.deleted_at is not None:
                return False
            folder.name = name
            await session.commit()
            return True

    async def set_access_mode(self, folder_id: int, mode: str) -> bool:
        async with self.session_factory() as session:
            folder = await session.get(Folder, folder_id)
            if folder is None or folder.deleted_at is not None:
                return False
            folder.access_mode = mode
            await session.commit()
            return True

    async def soft_delete(self, folder_id: int) -> bool:
        """软删除目录及其所有子孙目录、其中的文件（不删除频道里的字节）。"""
        async with self.session_factory() as session:
            folder = await session.get(Folder, folder_id)
            if folder is None or folder.deleted_at is not None:
                return False

            # BFS 收集该目录及所有子孙目录 id
            ids: list[int] = []
            queue = [folder_id]
            while queue:
                parent = queue.pop()
                ids.append(parent)
                children = list(
                    await session.scalars(
                        select(Folder.id).where(
                            Folder.parent_id == parent, Folder.deleted_at.is_(None)
                        )
                    )
                )
                queue.extend(children)

            now = utcnow()
            await session.execute(
                update(Folder).where(Folder.id.in_(ids)).values(deleted_at=now)
            )
            await session.execute(
                update(MediaItem)
                .where(MediaItem.folder_id.in_(ids))
                .values(deleted_at=now)
            )
            await session.commit()
            return True

    async def get_path(self, folder_id: int | None) -> str:
        """返回从根到该目录的路径，如 /旅行/2024。根目录返回 /。"""
        if is_root(folder_id):
            return "/"
        parts: list[str] = []
        current: int | None = folder_id
        visited: set[int] = set()
        async with self.session_factory() as session:
            while current is not None and current not in visited:
                visited.add(current)
                folder = await session.get(Folder, current)
                if folder is None or folder.deleted_at is not None:
                    break
                parts.append(folder.name)
                current = folder.parent_id
        return "/" + "/".join(reversed(parts))
