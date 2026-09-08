"""仓库层返回给 handler 的轻量数据传输对象（DTO）。

为什么不直接返回 ORM 对象？ORM 对象一旦离开会话（session）就是"游离"的，
访问懒加载的关系会报错。DTO 是纯数据，边界清晰、无副作用，也更好测试。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FolderDTO:
    id: int
    name: str
    parent_id: int | None
    access_mode: str


@dataclass
class MediaDTO:
    id: int
    channel_id: int
    msg_id: int
    folder_id: int | None
    filename: str | None
    mime_type: str | None
    file_size: int | None
    caption: str | None
    media_group_id: str | None
    created_at: datetime
    tag_names: list[str] = field(default_factory=list)


@dataclass
class TagDTO:
    id: int
    name: str
    color: str | None
