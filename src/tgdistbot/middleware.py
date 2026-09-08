"""中间件：把 Deps 注入 handler。"""

from __future__ import annotations

from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from .deps import Deps


class DepsMiddleware(BaseMiddleware):
    """把 Deps 放进 data，使 handler 能用 ``deps: Deps`` 形参接收。"""

    def __init__(self, deps: Deps) -> None:
        self.deps = deps

    async def __call__(
        self,
        handler: Any,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["deps"] = self.deps
        return await handler(event, data)
