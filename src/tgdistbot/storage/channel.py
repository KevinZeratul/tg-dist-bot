"""Telegram 频道存储实现。"""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import Message, MessageId


class TelegramChannelStorage:
    """把文件存进 Telegram 私有频道。

    为什么用 ``copy_message``（转发）而不是 ``get_file``（下载）：
    ``copy_message`` 是 Telegram 服务端的"复制引用"操作，字节始终留在
    Telegram 云端，因此**不受 Bot API 的 20MB 下载限制**，单文件上限就是
    Telegram 自身的 2GB（普通）/4GB（Premium）。取回时再从频道复制给用户，
    秒级直达，且服务器零存储成本。
    """

    def __init__(self, bot: Bot, channel_id: int) -> None:
        self.bot = bot
        self.channel_id = channel_id

    async def store(self, message: Message) -> tuple[int, int]:
        """把一条媒体消息复制进频道，返回 ``(channel_id, msg_id)``。"""
        copied = await self.bot.copy_message(
            chat_id=self.channel_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            disable_notification=True,
        )
        return self.channel_id, copied.message_id

    async def retrieve(self, user_id: int, channel_id: int, msg_id: int) -> MessageId:
        """把频道里已存的消息复制回给 ``user_id``。"""
        return await self.bot.copy_message(
            chat_id=user_id,
            from_chat_id=channel_id,
            message_id=msg_id,
        )
