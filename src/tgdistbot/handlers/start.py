"""/start、/help、/channel。"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from ..deps import Deps
from .auth import IsAdmin, is_admin
from .share import handle_share_start

router = Router()

HELP = (
    "📖 命令清单\n\n"
    "浏览：\n"
    "  /files 或 /ls — 查看当前目录\n"
    "  /cd <id> — 进入目录（0=根目录）\n"
    "  /up — 返回上级\n"
    "  /tree — 查看完整目录树\n"
    "  /channel — 打开媒体存储频道（直接翻看媒体）\n\n"
    "目录：\n"
    "  /mkdir <名称> — 在当前目录新建\n"
    "  /rename <id> <新名>\n"
    "  /rmdir <id> — 删除目录（软删除）\n\n"
    "文件：\n"
    "  直接发照片/视频/文件 = 上传到当前目录\n"
    "  /mv <文件id> <目录id> — 移动（0=根）\n"
    "  /rm <文件id> — 删除（软删除）\n"
    "  /purge — 一键清除失效索引（频道里已删的）\n\n"
    "标签与搜索：\n"
    "  /tag <文件id> <标签...>\n"
    "  /untag <文件id> <标签>\n"
    "  /tags [文件id] — 列出标签\n"
    "  /find <标签> — 按标签列出文件\n"
    "  /search <关键词> — 搜文件名/目录名/标签\n\n"
    "分享：\n"
    "  /share <目录id> [有效秒数] — 生成访问链接\n"
)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, deps: Deps) -> None:
    # deep-link 分享入口：/start share_<token>
    if command.args and command.args.startswith("share_"):
        await handle_share_start(message, command.args[len("share_"):], deps)
        return

    if is_admin(deps, message.from_user.id):
        await message.answer(
            "👋 你好，我是你的个人网盘 bot。\n"
            "直接发照片/视频即可上传到当前目录。\n\n" + HELP
        )
    else:
        await message.answer("❌ 你不是本 bot 的用户。")


@router.message(Command("help"))
async def cmd_help(message: Message, deps: Deps) -> None:
    if is_admin(deps, message.from_user.id):
        await message.answer(HELP)


@router.message(Command("channel"), IsAdmin())
async def cmd_channel(message: Message, deps: Deps) -> None:
    """返回媒体存储频道的链接，用户点进去用 Telegram 原生画廊查看媒体。"""
    try:
        chat = await deps.bot.get_chat(deps.settings.channel_id)
        if chat.username:
            link = f"https://t.me/{chat.username}"
        else:
            link = chat.invite_link or await deps.bot.export_chat_invite_link(
                deps.settings.channel_id
            )
        await message.answer(
            f"📺 媒体存储频道：\n{link}\n\n"
            f"点进去即可用 Telegram 原生的画廊/时间线查看所有照片视频。"
        )
    except Exception:
        await message.answer("❌ 获取频道链接失败。请确认 bot 是该频道的管理员。")
