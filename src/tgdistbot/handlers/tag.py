"""标签与检索命令（管理员专用）。"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from ..deps import Deps
from .auth import IsAdmin

router = Router()

PAGE_SIZE = 10


@router.message(Command("tag"), IsAdmin())
async def cmd_tag(message: Message, command: CommandObject, deps: Deps) -> None:
    parts = (command.args or "").split()
    if len(parts) < 2 or not parts[0].isdigit():
        await message.answer("用法：/tag <文件id> <标签...>")
        return
    item_id = int(parts[0])
    item = await deps.repos.media.get(item_id)
    if item is None:
        await message.answer("❌ 文件不存在")
        return
    added: list[str] = []
    for name in parts[1:]:
        tag = await deps.repos.tags.get_or_create(name)
        await deps.repos.media.add_tag(item_id, tag.id)
        added.append(tag.name)
    await message.answer(f"✅ 已给 #{item_id} 打标签：{'、'.join(added)}")


@router.message(Command("untag"), IsAdmin())
async def cmd_untag(message: Message, command: CommandObject, deps: Deps) -> None:
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[0].isdigit():
        await message.answer("用法：/untag <文件id> <标签>")
        return
    item_id = int(parts[0])
    name = parts[1]
    tag = await deps.repos.tags.get_by_name(name)
    if tag is None:
        await message.answer(f"❌ 标签「{name}」不存在")
        return
    await deps.repos.media.remove_tag(item_id, tag.id)
    await message.answer(f"✅ 已移除标签「{name}」")


@router.message(Command("tags"), IsAdmin())
async def cmd_tags(message: Message, command: CommandObject, deps: Deps) -> None:
    args = (command.args or "").strip()
    if args.isdigit():
        item = await deps.repos.media.get(int(args))
        if item is None:
            await message.answer("❌ 文件不存在")
            return
        names = item.tag_names or []
        await message.answer(f"#{item.id} 的标签：{'、'.join(names) if names else '（无）'}")
        return
    tags = await deps.repos.tags.list_all()
    if not tags:
        await message.answer("（还没有任何标签）")
        return
    await message.answer("🏷 全部标签：\n" + "、".join(f"{t.name}(#{t.id})" for t in tags))


@router.message(Command("find"), IsAdmin())
async def cmd_find(message: Message, command: CommandObject, deps: Deps) -> None:
    tag = (command.args or "").strip()
    if not tag:
        await message.answer("用法：/find <标签>")
        return
    items = await deps.repos.media.list_by_tag(tag, limit=PAGE_SIZE)
    if not items:
        await message.answer(f"标签「{tag}」下没有文件。")
        return
    lines = [f"#{i.id} {i.filename or i.mime_type or '文件'}" for i in items]
    await message.answer(f"🏷 「{tag}」下的文件：\n" + "\n".join(lines))


@router.message(Command("search"), IsAdmin())
async def cmd_search(message: Message, command: CommandObject, deps: Deps) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("用法：/search <关键词>（同时搜文件名、文件夹名、标签）")
        return
    files = await deps.repos.media.search(query, limit=PAGE_SIZE)
    folders = await deps.repos.folders.search(query, limit=PAGE_SIZE)
    tags = await deps.repos.tags.search(query, limit=PAGE_SIZE)
    if not (files or folders or tags):
        await message.answer(f"没有找到与「{query}」相关的结果。")
        return

    blocks: list[str] = []
    if folders:
        blocks.append(
            "📁 目录（/cd <id> 进入）：\n"
            + "\n".join(f"#{f.id} {f.name}" for f in folders)
        )
    if files:
        blocks.append("🖼 文件（/mv /rm /tag 操作）：\n" + "\n".join(
            f"#{i.id} {i.filename or i.mime_type or '文件'}" for i in files
        ))
    if tags:
        blocks.append("🏷 标签（/find <标签> 看文件）：\n" + "\n".join(t.name for t in tags))
    await message.answer(f"🔍 「{query}」的结果：\n\n" + "\n\n".join(blocks))
