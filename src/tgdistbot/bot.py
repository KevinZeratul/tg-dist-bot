"""Dispatcher 装配。"""

from __future__ import annotations

import logging

from aiogram import Dispatcher
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types.error_event import ErrorEvent

from .deps import Deps
from .handlers import browse, folder, share, start, tag, upload
from .middleware import DepsMiddleware

logger = logging.getLogger(__name__)


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

    @dp.errors()
    async def errors_handler(error: ErrorEvent) -> None:
        """全局兜底：网络错误只记一条日志，不刷 traceback，程序继续跑。"""
        exception = error.exception
        if isinstance(exception, TelegramNetworkError):
            logger.warning("网络错误：%s", exception)
        else:
            logger.error("未处理异常：%s", exception, exc_info=exception)

    return dp
