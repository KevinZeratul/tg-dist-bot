"""鉴权：管理员的过滤器，以及访问控制辅助函数。"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from ..db.repo.base import is_root
from ..deps import Deps


class IsAdmin(BaseFilter):
    """只放行 owner 与额外管理员（用于管理类命令/上传）。"""

    async def __call__(self, message: Message, deps: Deps) -> bool:
        return message.from_user is not None and message.from_user.id in deps.settings.admin_ids


def is_admin(deps: Deps, user_id: int) -> bool:
    """判断某用户是否是管理员。"""
    return user_id in deps.settings.admin_ids


async def can_access_folder(deps: Deps, user_id: int, folder_id: int | None) -> bool:
    """判断某用户能否访问某目录。

    - 管理员：可访问一切；
    - 其他人：只能访问被明确授权（folder_access 里有记录）的目录。
    """
    if is_admin(deps, user_id):
        return True
    if is_root(folder_id):
        return False
    return await deps.repos.access.has_access(folder_id, user_id)
