"""/start 与 /help。"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from ..deps import Deps
from .auth import is_admin
from .share import handle_share_start

router = Router()

HELP = (
    "📖 命令清单\n\n"
    "浏览：\n"
    "  /files — 查看当前目录（含按钮）\n"
    "  /cd <id> — 进入目录（0=根目录）\n"
    "  /up — 返回上级\n\n"
    "目录：\n"
    "  /mkdir <名称> — 在当前目录新建\n"
    "  /rename <id> <新名>\n"
    "  /rmdir <id> — 删除目录（软删除）\n\n"
    "文件：\n"
    "  直接发照片/视频/文件 = 上传到当前目录\n"
    "  /mv <文件id> <目录id> — 移动（0=根）\n"
    "  /rm <文件id> — 删除（软删除）\n\n"
    "标签与搜索：\n"
    "  /tag <文件id> <标签...>\n"
    "  /untag <文件id> <标签>\n"
    "  /tags [文件id] — 列出标签\n"
    "  /find <标签> — 按标签列出文件\n"
    "  /search <关键词>\n\n"
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
            "直接发照片/视频给我即可上传，发送 /help 查看全部命令。"
        )
    else:
        await message.answer("❌ 你不是本 bot 的用户。")


@router.message(Command("help"))
async def cmd_help(message: Message, deps: Deps) -> None:
    if is_admin(deps, message.from_user.id):
        await message.answer(HELP)
