"""上传：管理员发送媒体 → 存入频道并记录元数据。"""

from __future__ import annotations

from dataclasses import dataclass

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..deps import Deps
from .auth import IsAdmin
from .nav import current_folder

router = Router()

MEDIA_TYPES = {"photo", "video", "document", "audio", "animation", "video_note", "voice"}


@dataclass
class MediaMeta:
    filename: str | None
    mime_type: str | None
    file_size: int | None
    file_unique_id: str | None


def extract_media_meta(message: Message) -> MediaMeta:
    """从消息里提取媒体元信息（不同媒体类型字段不同）。"""
    if message.photo:
        p = message.photo[-1]  # 取最大分辨率
        return MediaMeta(None, "image/jpeg", p.file_size, p.file_unique_id)
    if message.video:
        v = message.video
        return MediaMeta(v.file_name, v.mime_type, v.file_size, v.file_unique_id)
    if message.document:
        d = message.document
        return MediaMeta(d.file_name, d.mime_type, d.file_size, d.file_unique_id)
    if message.animation:
        a = message.animation
        return MediaMeta(a.file_name, a.mime_type, a.file_size, a.file_unique_id)
    if message.audio:
        au = message.audio
        return MediaMeta(au.file_name, au.mime_type, au.file_size, au.file_unique_id)
    if message.video_note:
        vn = message.video_note
        return MediaMeta(None, "video/mp4", vn.file_size, vn.file_unique_id)
    if message.voice:
        vo = message.voice
        return MediaMeta(None, vo.mime_type, vo.file_size, vo.file_unique_id)
    return MediaMeta(None, None, None, None)


@router.message(IsAdmin(), F.content_type.in_(MEDIA_TYPES))
async def on_media(message: Message, deps: Deps, state: FSMContext) -> None:
    """上传媒体到当前浏览目录。"""
    folder_id = await current_folder(state)

    # 1) 把消息复制进私有频道（字节留在 Telegram 云端，不受 20MB 限制）
    channel_id, msg_id = await deps.storage.store(message)

    # 2) 记录元数据
    meta = extract_media_meta(message)
    item = await deps.repos.media.create(
        channel_id=channel_id,
        msg_id=msg_id,
        filename=meta.filename,
        mime_type=meta.mime_type,
        file_size=meta.file_size,
        file_unique_id=meta.file_unique_id,
        caption=message.caption,
        media_group_id=message.media_group_id,
        folder_id=folder_id,
    )

    path = await deps.repos.folders.get_path(folder_id)
    await message.answer(f"✅ 已保存 #{item.id} 到 {path}")
