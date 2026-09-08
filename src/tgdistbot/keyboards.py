"""内联键盘与回调数据。"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .db.repo.base import is_root
from .db.schemas import FolderDTO, MediaDTO


class NavCB(CallbackData, prefix="nav"):
    """浏览器的所有回调动作统一走这一个工厂，便于理解与扩展。"""

    action: str  # open | back | page | send
    folder_id: int | None = None
    item_id: int | None = None
    page: int = 0


def _folder_btn(folder: FolderDTO) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=f"📁 #{folder.id} {folder.name}",
        callback_data=NavCB(action="open", folder_id=folder.id).pack(),
    )


def _file_btn(item: MediaDTO) -> InlineKeyboardButton:
    label = item.filename or item.mime_type or "文件"
    return InlineKeyboardButton(
        text=f"🖼 #{item.id} {label}",
        callback_data=NavCB(action="send", item_id=item.id).pack(),
    )


def build_browse_keyboard(
    folders: list[FolderDTO],
    files: list[MediaDTO],
    page: int,
    has_next: bool,
    current_folder_id: int | None,
) -> InlineKeyboardMarkup | None:
    """构造浏览键盘：目录在上、文件在下，底部是翻页与返回上级。

    若没有任何按钮（例如空目录），返回 None，调用方据此省略 reply_markup。
    """
    rows: list[list[InlineKeyboardButton]] = []
    for folder in folders:
        rows.append([_folder_btn(folder)])
    for item in files:
        rows.append([_file_btn(item)])

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="‹ 上一页",
                callback_data=NavCB(
                    action="page", folder_id=current_folder_id, page=page - 1
                ).pack(),
            )
        )
    if has_next:
        nav.append(
            InlineKeyboardButton(
                text="下一页 ›",
                callback_data=NavCB(
                    action="page", folder_id=current_folder_id, page=page + 1
                ).pack(),
            )
        )
    if nav:
        rows.append(nav)

    if not is_root(current_folder_id):
        rows.append(
            [
                InlineKeyboardButton(
                    text="⬆ 返回上级",
                    callback_data=NavCB(action="back").pack(),
                )
            ]
        )

    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)
