"""浏览：目录树导航、文件取回、翻页（管理员 + 共享用户）。"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from ..db.repo.base import ROOT_FOLDER_ID, is_root
from ..db.schemas import FolderDTO
from ..deps import Deps
from ..keyboards import NavCB, build_browse_keyboard
from .auth import IsAdmin, can_access_folder, is_admin
from .nav import current_folder

router = Router()

PAGE_SIZE = 8


async def _granted_folders(deps: Deps, user_id: int) -> list[FolderDTO]:
    """列出某用户被授权访问的目录。"""
    ids = await deps.repos.access.list_granted_folder_ids(user_id)
    folders: list[FolderDTO] = []
    for fid in ids:
        folder = await deps.repos.folders.get(fid)
        if folder is not None:
            folders.append(folder)
    return folders


def _build_tree(folders: list[FolderDTO]) -> str:
    """把扁平目录列表拼成缩进树形文本。"""
    by_parent: dict[int | None, list[FolderDTO]] = {}
    for f in folders:
        by_parent.setdefault(f.parent_id, []).append(f)

    lines: list[str] = []

    def walk(parent: int | None, indent: str) -> None:
        for f in sorted(by_parent.get(parent, []), key=lambda x: x.name):
            lines.append(f"{indent}📁 #{f.id} {f.name}")
            walk(f.id, indent + "    ")

    walk(None, "")
    return "\n".join(lines) if lines else "（还没有目录）"


async def _compose(
    deps: Deps, user_id: int, folder_id: int | None, page: int
) -> tuple[str, InlineKeyboardMarkup | None] | None:
    """根据角色与目录计算「文本 + 键盘」。无权限返回 None。

    - 管理员：完整目录树导航；
    - 共享用户：先看到被授权的目录列表，点进去只看该目录下的文件。
    """
    if is_admin(deps, user_id):
        folders = await deps.repos.folders.list_children(folder_id)
        total = await deps.repos.media.count_in_folder(folder_id)
        files = await deps.repos.media.list_in_folder(
            folder_id, offset=page * PAGE_SIZE, limit=PAGE_SIZE
        )
        has_next = (page + 1) * PAGE_SIZE < total
        path = await deps.repos.folders.get_path(folder_id)
        page_hint = f" · 第 {page + 1} 页" if total else ""
        text = (
            f"📍 当前位置：{path}\n"
            f"子目录 {len(folders)} 个 · 文件 {total} 个{page_hint}\n\n"
            f"发照片/视频即上传到本目录。\n"
            f"/ls 列表 · /tree 总览 · /channel 看媒体 · /search 搜索"
        )
        return text, build_browse_keyboard(folders, files, page, has_next, folder_id)

    # —— 共享用户 ——
    if is_root(folder_id):
        granted = await _granted_folders(deps, user_id)
        if not granted:
            return "🔐 当前没有共享给你的文件夹。", build_browse_keyboard(
                [], [], 0, False, ROOT_FOLDER_ID
            )
        return "🔐 共享给你的文件夹：\n点击进入查看文件", build_browse_keyboard(
            granted, [], 0, False, ROOT_FOLDER_ID
        )

    if not await can_access_folder(deps, user_id, folder_id):
        return None
    folder = await deps.repos.folders.get(folder_id)
    if folder is None:
        return None
    total = await deps.repos.media.count_in_folder(folder_id)
    files = await deps.repos.media.list_in_folder(
        folder_id, offset=page * PAGE_SIZE, limit=PAGE_SIZE
    )
    has_next = (page + 1) * PAGE_SIZE < total
    text = f"📍 {folder.name}（共享） · 文件 {total} 个"
    return text, build_browse_keyboard([], files, page, has_next, folder_id)


async def _render_browse(
    deps: Deps,
    user_id: int,
    chat_id: int,
    folder_id: int | None,
    page: int,
    edit: Message | None,
) -> bool:
    """渲染一页浏览（发或编辑导航消息）。返回是否有权限。"""
    composed = await _compose(deps, user_id, folder_id, page)
    if composed is None:
        return False
    text, kb = composed

    if edit is not None:
        try:
            await edit.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            await deps.bot.send_message(chat_id, text, reply_markup=kb)
    else:
        await deps.bot.send_message(chat_id, text, reply_markup=kb)
    return True


# —— 命令 ——


@router.message(Command("files", "ls"))
async def cmd_files(message: Message, deps: Deps, state: FSMContext) -> None:
    folder_id = await current_folder(state)
    ok = await _render_browse(deps, message.from_user.id, message.chat.id, folder_id, 0, None)
    if not ok:
        await message.answer("❌ 没有可访问的内容。")


@router.message(Command("cd"), IsAdmin())
async def cmd_cd(
    message: Message, command: CommandObject, deps: Deps, state: FSMContext
) -> None:
    args = (command.args or "").strip()
    if not args.isdigit():
        await message.answer("用法：/cd <目录id>（0 = 根目录）")
        return
    folder_id = int(args)
    if folder_id != ROOT_FOLDER_ID:
        folder = await deps.repos.folders.get(folder_id)
        if folder is None:
            await message.answer("❌ 目录不存在。")
            return
    await state.update_data(folder_id=folder_id, page=0)
    ok = await _render_browse(deps, message.from_user.id, message.chat.id, folder_id, 0, None)
    if not ok:
        await message.answer("❌ 没有可访问的内容。")


@router.message(Command("up"), IsAdmin())
async def cmd_up(message: Message, deps: Deps, state: FSMContext) -> None:
    cur = await current_folder(state)
    parent = ROOT_FOLDER_ID
    folder = await deps.repos.folders.get(cur)
    if folder is not None and folder.parent_id is not None:
        parent = folder.parent_id
    await state.update_data(folder_id=parent, page=0)
    ok = await _render_browse(deps, message.from_user.id, message.chat.id, parent, 0, None)
    if not ok:
        await message.answer("❌ 没有可访问的内容。")


@router.message(Command("tree"), IsAdmin())
async def cmd_tree(message: Message, deps: Deps) -> None:
    folders = await deps.repos.folders.list_all()
    await message.answer("🌳 目录结构（#id 可用于 /cd 进入）：\n\n" + _build_tree(folders))


# —— 回调 ——


@router.callback_query(NavCB.filter(F.action == "open"))
async def cb_open(
    cb: CallbackQuery, callback_data: NavCB, deps: Deps, state: FSMContext
) -> None:
    user_id = cb.from_user.id
    folder_id = callback_data.folder_id if callback_data.folder_id is not None else ROOT_FOLDER_ID
    if is_admin(deps, user_id):
        await state.update_data(folder_id=folder_id, page=0)
    ok = await _render_browse(deps, user_id, cb.message.chat.id, folder_id, 0, cb.message)
    if not ok:
        await cb.answer("❌ 无权限访问该目录", show_alert=True)
        return
    await cb.answer()


@router.callback_query(NavCB.filter(F.action == "back"))
async def cb_back(
    cb: CallbackQuery, callback_data: NavCB, deps: Deps, state: FSMContext
) -> None:
    user_id = cb.from_user.id
    if is_admin(deps, user_id):
        cur = await current_folder(state)
        parent = ROOT_FOLDER_ID
        folder = await deps.repos.folders.get(cur)
        if folder is not None and folder.parent_id is not None:
            parent = folder.parent_id
        await state.update_data(folder_id=parent, page=0)
        target = parent
    else:
        # 共享用户点「返回上级」= 回到被授权目录列表
        target = ROOT_FOLDER_ID
    ok = await _render_browse(deps, user_id, cb.message.chat.id, target, 0, cb.message)
    if not ok:
        await cb.answer("❌ 无权限", show_alert=True)
        return
    await cb.answer()


@router.callback_query(NavCB.filter(F.action == "page"))
async def cb_page(cb: CallbackQuery, callback_data: NavCB, deps: Deps) -> None:
    user_id = cb.from_user.id
    folder_id = callback_data.folder_id if callback_data.folder_id is not None else ROOT_FOLDER_ID
    ok = await _render_browse(
        deps, user_id, cb.message.chat.id, folder_id, callback_data.page, cb.message
    )
    if not ok:
        await cb.answer("❌ 无权限", show_alert=True)
        return
    await cb.answer()


@router.callback_query(NavCB.filter(F.action == "send"))
async def cb_send(cb: CallbackQuery, callback_data: NavCB, deps: Deps) -> None:
    user_id = cb.from_user.id
    if callback_data.item_id is None:
        await cb.answer("❌ 无效操作", show_alert=True)
        return
    item = await deps.repos.media.get(callback_data.item_id)
    if item is None:
        await cb.answer("❌ 文件不存在", show_alert=True)
        return

    # 鉴权：管理员可发一切；共享用户只能发"被授权目录"里的文件
    if not is_admin(deps, user_id):
        if is_root(item.folder_id) or not await can_access_folder(deps, user_id, item.folder_id):
            await cb.answer("❌ 无权限", show_alert=True)
            return

    try:
        await deps.storage.retrieve(user_id, item.channel_id, item.msg_id)
    except TelegramBadRequest as exc:
        # 频道里的原消息被手动删掉了 → 索引失效，清除它
        if "not found" in str(exc.message).lower():
            await deps.repos.media.soft_delete(item.id)
            await cb.answer("⚠️ 该文件在频道里已被删除，索引已清除。", show_alert=True)
        else:
            await cb.answer("❌ 发送失败，请稍后重试。", show_alert=True)
        return
    await cb.answer("✅ 已发送")
