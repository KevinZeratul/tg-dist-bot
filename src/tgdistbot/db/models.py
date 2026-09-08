"""SQLAlchemy ORM 模型。

表结构对应"个人网盘"的元数据：
- folders        目录树（可嵌套）
- media_items    文件条目（指向频道里已存储的那条消息）
- tags / item_tags 标签（多对多）
- folder_access  文件夹级鉴权（shared 时哪些用户可访问）
- share_tokens   分享邀请令牌（deep-link 用）
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """返回"无时区信息"的 UTC 时间（SQLite 友好，且避免 datetime.utcnow 弃用告警）。"""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """所有模型的基类。"""


# 多对多关联表：media_items <-> tags
item_tags = Table(
    "item_tags",
    Base.metadata,
    Column(
        "media_id",
        ForeignKey("media_items.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Folder(Base):
    """目录节点，通过 parent_id 组成树。parent_id 为空表示根目录下的文件夹。"""

    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"), nullable=True
    )
    # private = 仅 owner；shared = 允许 folder_access 里列出的用户访问
    access_mode: Mapped[str] = mapped_column(String(16), default="private")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # 软删除标记：删除只改这里，不删频道里的字节
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MediaItem(Base):
    """一条已存储的文件。channel_id + msg_id 指向频道里那条真实消息。"""

    __tablename__ = "media_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    msg_id: Mapped[int] = mapped_column(BigInteger)
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id", ondelete="SET NULL"), nullable=True
    )
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    file_unique_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 相册（一次发多张图）的分组 id，供后续按相册聚合展示
    media_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tags: Mapped[list[Tag]] = relationship(
        secondary=item_tags, back_populates="items", lazy="selectin"
    )


class Tag(Base):
    """标签。MVP 平铺不分级，但预留 color 字段供日后扩展。"""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)

    items: Mapped[list[MediaItem]] = relationship(
        secondary=item_tags, back_populates="tags", lazy="selectin"
    )


class FolderAccess(Base):
    """文件夹级访问白名单：folder 为 shared 时，列出的 user_id 可以访问。"""

    __tablename__ = "folder_access"

    id: Mapped[int] = mapped_column(primary_key=True)
    folder_id: Mapped[int] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ShareToken(Base):
    """分享邀请令牌：`/share <folder>` 生成一个 UUID，受邀者点 deep-link 后授权。"""

    __tablename__ = "share_tokens"

    token: Mapped[str] = mapped_column(String(36), primary_key=True)
    folder_id: Mapped[int] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
