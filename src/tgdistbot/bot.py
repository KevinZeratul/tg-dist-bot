"""Dispatcher 装配。"""

from __future__ import annotations

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .deps import Deps
from .handlers import browse, folder, share, start, tag, upload
from .middleware import DepsMiddleware


def build_dispatcher(deps: Deps) -> Dispatcher:
    """创建 Dispatcher 并注册所有 handler 与依赖注入中间件。"""
    dp = Dispatcher(storage=MemoryStorage())

    # outer middleware：在过滤器/处理器之前把 deps 注入 data（IsAdmin 过滤器也要用）
    dp.update.outer_middleware(DepsMiddleware(deps))

    for router in (
        start.router,
        upload.router,
        browse.router,
        folder.router,
        tag.router,
        share.router,
    ):
        dp.include_router(router)

    return dp
