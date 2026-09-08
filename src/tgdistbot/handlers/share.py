"""分享：生成 deep-link 邀请，被邀请者点链接后获得访问权限。"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from ..deps import Deps
from .auth import IsAdmin

router = Router()


async def handle_share_start(message: Message, token: str, deps: Deps) -> None:
    """处理 deep-link 分享入口：/start share_<token>。"""
    folder_id = await deps.repos.access.get_folder_by_token(token)
    if folder_id is None:
        await message.answer("❌ 分享链接无效或已过期。")
        return
    folder = await deps.repos.folders.get(folder_id)
    if folder is None:
        await message.answer("❌ 该文件夹不存在。")
        return

    await deps.repos.access.grant(folder_id, message.from_user.id)
    await message.answer(
        f"✅ 已授权你访问共享文件夹「{folder.name}」(#{folder_id})。\n"
        f"发送 /files 即可查看。"
    )


@router.message(Command("share"), IsAdmin())
async def cmd_share(message: Message, command: CommandObject, deps: Deps) -> None:
    parts = (command.args or "").split()
    if not parts or not parts[0].isdigit():
        await message.answer("用法：/share <目录id> [有效秒数，默认永久]")
        return
    folder_id = int(parts[0])
    folder = await deps.repos.folders.get(folder_id)
    if folder is None:
        await message.answer("❌ 目录不存在")
        return

    ttl: int | None = None
    if len(parts) >= 2 and parts[1].isdigit():
        ttl = int(parts[1])

    await deps.repos.folders.set_access_mode(folder_id, "shared")
    token = await deps.repos.access.create_token(folder_id, ttl)

    me = await deps.bot.get_me()
    username = me.username or "bot"
    link = f"https://t.me/{username}?start=share_{token}"

    await message.answer(
        f"✅ 已共享文件夹「{folder.name}」(#{folder_id})\n\n"
        f"把下面链接发给对方，对方点开即可访问：\n{link}"
    )
