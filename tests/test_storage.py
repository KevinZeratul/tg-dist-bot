"""存储适配层测试（用 mock bot，不真正联网）。"""

from __future__ import annotations

from unittest.mock import AsyncMock

from aiogram.types import MessageId

from tgdistbot.storage.channel import TelegramChannelStorage


class _Chat:
    id = 111


class _Message:
    chat = _Chat()
    message_id = 5


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
