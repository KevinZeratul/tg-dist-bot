"""目录与文件的管理命令（管理员专用）。"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..db.repo.base import ROOT_FOLDER_ID
from ..deps import Deps
from .auth import IsAdmin
from .nav import current_folder

router = Router()


@router.message(Command("mkdir"), IsAdmin())
async def cmd_mkdir(
    message: Message, command: CommandObject, deps: Deps, state: FSMContext
) -> None:
    name = (command.args or "").strip()
    if not name:
        await message.answer("用法：/mkdir <名称>")
        return
    parent = await current_folder(state)
    folder = await deps.repos.folders.create(name, parent)
    path = await deps.repos.folders.get_path(folder.id)
    await message.answer(f"✅ 已新建目录 #{folder.id}「{folder.name}」于 {path}")


@router.message(Command("rename"), IsAdmin())
async def cmd_rename(message: Message, command: CommandObject, deps: Deps) -> None:
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[0].isdigit():
        await message.answer("用法：/rename <目录id> <新名称>")
        return
    folder_id = int(parts[0])
    name = parts[1].strip()
    ok = await deps.repos.folders.rename(folder_id, name)
    await message.answer("✅ 已重命名" if ok else "❌ 目录不存在")


@router.message(Command("rmdir"), IsAdmin())
async def cmd_rmdir(message: Message, command: CommandObject, deps: Deps) -> None:
    args = (command.args or "").strip()
    if not args.isdigit():
        await message.answer("用法：/rmdir <目录id>")
        return
    ok = await deps.repos.folders.soft_delete(int(args))
    await message.answer("✅ 已删除目录（软删除，频道文件保留）" if ok else "❌ 目录不存在")


@router.message(Command("mv"), IsAdmin())
async def cmd_mv(message: Message, command: CommandObject, deps: Deps) -> None:
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await message.answer("用法：/mv <文件id> <目录id>（目录id 用 0 表示根）")
        return
    item_id = int(parts[0])
    folder_id = int(parts[1])
    if folder_id != ROOT_FOLDER_ID:
        folder = await deps.repos.folders.get(folder_id)
        if folder is None:
            await message.answer("❌ 目标目录不存在")
            return
    ok = await deps.repos.media.move(item_id, folder_id)
    await message.answer("✅ 已移动" if ok else "❌ 文件不存在")


@router.message(Command("rm"), IsAdmin())
async def cmd_rm(message: Message, command: CommandObject, deps: Deps) -> None:
    args = (command.args or "").strip()
    if not args.isdigit():
        await message.answer("用法：/rm <文件id>")
        return
    ok = await deps.repos.media.soft_delete(int(args))
    await message.answer("✅ 已删除（软删除，频道文件保留）" if ok else "❌ 文件不存在")
