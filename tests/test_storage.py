"""存储适配层测试（用 mock bot，不真正联网）。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramNetworkError
from aiogram.types import MessageId

from tgdistbot.storage.channel import TelegramChannelStorage


class _Chat:
    id = 111


class _Message:
    chat = _Chat()
    message_id = 5


def _net_err() -> TelegramNetworkError:
    return TelegramNetworkError(method=None, message="boom")


async def test_store_and_retrieve():
    bot = AsyncMock()
    bot.copy_message.return_value = MessageId(message_id=42)
    storage = TelegramChannelStorage(bot, channel_id=-100123)

    channel_id, msg_id = await storage.store(_Message())
    assert channel_id == -100123
    assert msg_id == 42
    bot.copy_message.assert_called_with(
        chat_id=-100123, from_chat_id=111, message_id=5, disable_notification=True
    )

    await storage.retrieve(999, -100123, 42)
    bot.copy_message.assert_called_with(
        chat_id=999, from_chat_id=-100123, message_id=42
    )


async def test_store_retries_then_succeeds():
    bot = AsyncMock()
    bot.copy_message.side_effect = [_net_err(), _net_err(), MessageId(message_id=7)]
    storage = TelegramChannelStorage(bot, channel_id=-100)

    with patch("tgdistbot.storage.channel.asyncio.sleep", new=AsyncMock()):
        channel_id, msg_id = await storage.store(_Message())

    assert (channel_id, msg_id) == (-100, 7)
    assert bot.copy_message.call_count == 3


async def test_store_gives_up_after_retries():
    bot = AsyncMock()
    bot.copy_message.side_effect = [_net_err(), _net_err(), _net_err()]
    storage = TelegramChannelStorage(bot, channel_id=-100)

    with patch("tgdistbot.storage.channel.asyncio.sleep", new=AsyncMock()):
        try:
            await storage.store(_Message())
        except TelegramNetworkError:
            pass
        else:
            raise AssertionError("应当抛出 TelegramNetworkError")

    assert bot.copy_message.call_count == 3
