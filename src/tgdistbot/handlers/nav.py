"""浏览导航的 FSM 状态与"当前目录"辅助。"""

from __future__ import annotations

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..db.repo.base import ROOT_FOLDER_ID


class BrowseState(StatesGroup):
    """记录每个用户当前正在浏览的目录。"""

    current = State()


async def current_folder(state: FSMContext) -> int:
    """读取当前目录 id；没有记录时视为根目录（0）。"""
    data = await state.get_data()
    return int(data.get("folder_id", ROOT_FOLDER_ID))
