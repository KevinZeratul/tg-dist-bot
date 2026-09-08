"""鉴权仓库：文件夹访问白名单 + 分享令牌。"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select

from ..models import FolderAccess, ShareToken, utcnow
from .base import BaseRepo


class AccessRepo(BaseRepo):
    async def grant(self, folder_id: int, user_id: int) -> None:
        """授予某用户访问某文件夹的权限（幂等）。"""
        async with self.session_factory() as session:
            exists = await session.scalar(
                select(FolderAccess).where(
                    FolderAccess.folder_id == folder_id,
                    FolderAccess.user_id == user_id,
                )
            )
            if exists is None:
                session.add(FolderAccess(folder_id=folder_id, user_id=user_id))
                await session.commit()

    async def revoke(self, folder_id: int, user_id: int) -> None:
        async with self.session_factory() as session:
            row = await session.scalar(
                select(FolderAccess).where(
                    FolderAccess.folder_id == folder_id,
                    FolderAccess.user_id == user_id,
                )
            )
            if row is not None:
                await session.delete(row)
                await session.commit()

    async def list_users(self, folder_id: int) -> list[int]:
        async with self.session_factory() as session:
            result = await session.scalars(
                select(FolderAccess.user_id).where(FolderAccess.folder_id == folder_id)
            )
            return list(result)

    async def has_access(self, folder_id: int, user_id: int) -> bool:
        async with self.session_factory() as session:
            row = await session.scalar(
                select(FolderAccess).where(
                    FolderAccess.folder_id == folder_id,
                    FolderAccess.user_id == user_id,
                )
            )
            return row is not None

    async def list_granted_folder_ids(self, user_id: int) -> list[int]:
        """列出某用户被授权访问的所有目录 id。"""
        async with self.session_factory() as session:
            result = await session.scalars(
                select(FolderAccess.folder_id).where(FolderAccess.user_id == user_id)
            )
            return list(result)

    async def create_token(
        self, folder_id: int, ttl_seconds: int | None = None
    ) -> str:
        """生成分享令牌。ttl_seconds 为空表示永不过期。"""
        token = uuid.uuid4().hex
        expires_at = utcnow() + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        async with self.session_factory() as session:
            session.add(
                ShareToken(token=token, folder_id=folder_id, expires_at=expires_at)
            )
            await session.commit()
        return token

    async def get_folder_by_token(self, token: str) -> int | None:
        """用令牌换目录 id；令牌不存在或已过期返回 None。"""
        async with self.session_factory() as session:
            row = await session.get(ShareToken, token)
            if row is None:
                return None
            if row.expires_at is not None and row.expires_at < utcnow():
                return None
            return row.folder_id
