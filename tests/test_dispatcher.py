"""Dispatcher 端到端测试：验证命令路由、依赖注入与 IsAdmin 门禁。

用 ``patch.object(Bot, "__call__")`` 拦截所有 Telegram API 调用，从而
无需联网即可验证 handler 是否真的被触发。

注意：handler 模块使用模块级 ``router`` 单例（aiogram 标准写法），所以
``build_dispatcher`` 在同一个进程里只能调用一次——因此这里把多个场景
合并进一个测试函数，共用一个 dispatcher。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

from aiogram import Bot
from aiogram.types import Chat, Message, Update, User

from tgdistbot.bot import build_dispatcher
from tgdistbot.config import Settings
from tgdistbot.db.engine import create_engine_and_sessionmaker
from tgdistbot.db.models import Base
from tgdistbot.deps import build_deps


def _update(uid: int, text: str) -> Update:
    user = User(id=uid, is_bot=False, first_name="U")
    chat = Chat(id=uid, type="private")
    message = Message(
        message_id=1, date=datetime.now(), chat=chat, from_user=user, text=text
    )
    return Update(update_id=uid, message=message)


async def _feed(bot: Bot, dp, update: Update) -> AsyncMock:
    """拦截 API 调用，喂一条 update，返回拦截器以便断言。"""
    interceptor = AsyncMock(return_value=None)
    with patch.object(Bot, "__call__", interceptor):
        await dp.feed_update(bot, update)
    return interceptor


async def test_dispatcher_routing_and_auth(tmp_path):
    settings = Settings(bot_token="1:AA", channel_id=-100123, owner_id=42)
    engine, sf = create_engine_and_sessionmaker(f"sqlite+aiosqlite:///{tmp_path}/t.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = Bot(token=settings.bot_token)
    dp = build_dispatcher(build_deps(settings, bot, sf))

    try:
        # 1) owner 的 /help 应被响应
        help_interceptor = await _feed(bot, dp, _update(42, "/help"))
        assert help_interceptor.called

        # 2) 非 owner 调用带 IsAdmin 的命令应被拦截（不触发任何 handler）
        blocked = await _feed(bot, dp, _update(999, "/mkdir 测试"))
        assert not blocked.called

        # 3) owner 调用 /mkdir 应被放行
        allowed = await _feed(bot, dp, _update(42, "/mkdir 旅行"))
        assert allowed.called
    finally:
        await bot.session.close()
        await engine.dispose()
