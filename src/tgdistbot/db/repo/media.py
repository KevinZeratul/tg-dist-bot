"""文件仓库：文件条目（MediaItem）的增删改查与打标。"""

from __future__ import annotations

from sqlalchemy import func, or_, select

from ..models import MediaItem, Tag, utcnow
from ..schemas import MediaDTO
from .base import BaseRepo, is_root


def _to_dto(item: MediaItem) -> MediaDTO:
    return MediaDTO(
        id=item.id,
        channel_id=item.channel_id,
        msg_id=item.msg_id,
        folder_id=item.folder_id,
        filename=item.filename,
        mime_type=item.mime_type,
        file_size=item.file_size,
        caption=item.caption,
        media_group_id=item.media_group_id,
        created_at=item.created_at,
        tag_names=[t.name for t in item.tags],
    )


def _folder_clause(folder_id: int | None):
    """folder_id 为空或 0 都表示"未归档到任何文件夹（根目录下）"。"""
    if is_root(folder_id):
        return MediaItem.folder_id.is_(None)
    return MediaItem.folder_id == folder_id


class MediaRepo(BaseRepo):
    async def create(
        self,
        *,
        channel_id: int,
        msg_id: int,
        filename: str | None = None,
        mime_type: str | None = None,
        file_size: int | None = None,
        file_unique_id: str | None = None,
        caption: str | None = None,
        media_group_id: str | None = None,
        folder_id: int | None = None,
    ) -> MediaDTO:
        async with self.session_factory() as session:
            item = MediaItem(
                channel_id=channel_id,
                msg_id=msg_id,
                folder_id=None if is_root(folder_id) else folder_id,
                filename=filename,
                mime_type=mime_type,
                file_size=file_size,
                file_unique_id=file_unique_id,
                caption=caption,
                media_group_id=media_group_id,
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return _to_dto(item)

    async def get(self, item_id: int) -> MediaDTO | None:
        async with self.session_factory() as session:
            item = await session.get(MediaItem, item_id)
            if item is None or item.deleted_at is not None:
                return None
            return _to_dto(item)

    async def list_in_folder(
        self, folder_id: int | None, offset: int = 0, limit: int = 10
    ) -> list[MediaDTO]:
        async with self.session_factory() as session:
            result = await session.scalars(
                select(MediaItem)
                .where(_folder_clause(folder_id), MediaItem.deleted_at.is_(None))
                .order_by(MediaItem.id.desc())
                .offset(offset)
                .limit(limit)
            )
            return [_to_dto(i) for i in result]

    async def count_in_folder(self, folder_id: int | None) -> int:
        async with self.session_factory() as session:
            result = await session.scalar(
                select(func.count())
                .select_from(MediaItem)
                .where(_folder_clause(folder_id), MediaItem.deleted_at.is_(None))
            )
            return int(result or 0)

    async def list_by_tag(
        self, tag_name: str, offset: int = 0, limit: int = 10
    ) -> list[MediaDTO]:
        async with self.session_factory() as session:
            result = await session.scalars(
                select(MediaItem)
                .join(MediaItem.tags)
                .where(Tag.name == tag_name, MediaItem.deleted_at.is_(None))
                .order_by(MediaItem.id.desc())
                .offset(offset)
                .limit(limit)
            )
            return [_to_dto(i) for i in result]

    async def search(
        self, query: str, offset: int = 0, limit: int = 10
    ) -> list[MediaDTO]:
        pattern = f"%{query}%"
        async with self.session_factory() as session:
            result = await session.scalars(
                select(MediaItem)
                .where(
                    MediaItem.deleted_at.is_(None),
                    or_(
                        MediaItem.filename.ilike(pattern),
                        MediaItem.caption.ilike(pattern),
                    ),
                )
                .order_by(MediaItem.id.desc())
                .offset(offset)
                .limit(limit)
            )
            return [_to_dto(i) for i in result]

    async def move(self, item_id: int, folder_id: int | None) -> bool:
        """把文件移到某目录；folder_id 为空/0 表示移回根目录。"""
        async with self.session_factory() as session:
            item = await session.get(MediaItem, item_id)
            if item is None or item.deleted_at is not None:
                return False
            item.folder_id = None if is_root(folder_id) else folder_id
            await session.commit()
            return True

    async def soft_delete(self, item_id: int) -> bool:
        async with self.session_factory() as session:
            item = await session.get(MediaItem, item_id)
            if item is None or item.deleted_at is not None:
                return False
            item.deleted_at = utcnow()
            await session.commit()
            return True

    async def add_tag(self, item_id: int, tag_id: int) -> None:
        async with self.session_factory() as session:
            item = await session.get(MediaItem, item_id)
            tag = await session.get(Tag, tag_id)
            if item is not None and tag is not None and tag not in item.tags:
                item.tags.append(tag)
                await session.commit()

    async def remove_tag(self, item_id: int, tag_id: int) -> None:
        async with self.session_factory() as session:
            item = await session.get(MediaItem, item_id)
            tag = await session.get(Tag, tag_id)
            if item is not None and tag is not None and tag in item.tags:
                item.tags.remove(tag)
                await session.commit()
