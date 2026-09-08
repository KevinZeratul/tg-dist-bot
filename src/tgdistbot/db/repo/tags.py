"""标签仓库：标签的查询与创建。"""

from __future__ import annotations

from sqlalchemy import select

from ..models import Tag
from ..schemas import TagDTO
from .base import BaseRepo


def _to_dto(tag: Tag) -> TagDTO:
    return TagDTO(id=tag.id, name=tag.name, color=tag.color)


class TagRepo(BaseRepo):
    async def get_or_create(self, name: str, color: str | None = None) -> TagDTO:
        """按名字取标签，不存在则创建（幂等）。"""
        async with self.session_factory() as session:
            tag = await session.scalar(select(Tag).where(Tag.name == name))
            if tag is None:
                tag = Tag(name=name, color=color)
                session.add(tag)
                await session.commit()
                await session.refresh(tag)
            return _to_dto(tag)

    async def get_by_name(self, name: str) -> TagDTO | None:
        async with self.session_factory() as session:
            tag = await session.scalar(select(Tag).where(Tag.name == name))
            return _to_dto(tag) if tag else None

    async def list_all(self) -> list[TagDTO]:
        async with self.session_factory() as session:
            result = await session.scalars(select(Tag).order_by(Tag.name))
            return [_to_dto(t) for t in result]
