"""Telegram 频道存储实现。"""

from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.types import Message, MessageId


class TelegramChannelStorage:
    """把文件存进 Telegram 私有频道。

    为什么用 ``copy_message``（转发）而不是 ``get_file``（下载）：
    ``copy_message`` 是 Telegram 服务端的"复制引用"操作，字节始终留在
    Telegram 云端，因此**不受 Bot API 的 20MB 下载限制**，单文件上限就是
    Telegram 自身的 2GB（普通）/4GB（Premium）。取回时再从频道复制给用户，
    秒级直达，且服务器零存储成本。
    """

    MAX_RETRIES = 3

    def __init__(self, bot: Bot, channel_id: int) -> None:
        self.bot = bot
        self.channel_id = channel_id

    async def _copy(
        self,
        *,
        chat_id: int,
        from_chat_id: int,
        message_id: int,
        **kwargs,
    ) -> MessageId:
        """带重试的 copy_message：网络瞬断时最多重试 3 次，间隔递增（1s/2s）。"""
        last_exc: TelegramNetworkError | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return await self.bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    **kwargs,
                )
            except TelegramNetworkError as exc:
                last_exc = exc
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(1 + attempt)
        assert last_exc is not None  # 循环至少跑一次，且每次都失败才会走到这
        raise last_exc

    async def store(self, message: Message) -> tuple[int, int]:
        """把一条媒体消息复制进频道，返回 ``(channel_id, msg_id)``。"""
        copied = await self._copy(
            chat_id=self.channel_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            disable_notification=True,
        )
        return self.channel_id, copied.message_id

    async def retrieve(self, user_id: int, channel_id: int, msg_id: int) -> MessageId:
        """把频道里已存的消息复制回给 ``user_id``。"""
        return await self._copy(
            chat_id=user_id,
            from_chat_id=channel_id,
            message_id=msg_id,
        )

    async def message_exists(self, channel_id: int, msg_id: int) -> bool:
        """检查频道里某条消息是否还存在。

        做法：把消息 copy 到频道自身（成功说明原消息在），再删掉副本，无副作用。
        网络错误等无法判断时**保守返回 True**（宁可不删索引，也不误删）。
        """
        try:
            copied = await self.bot.copy_message(
                chat_id=channel_id,
                from_chat_id=channel_id,
                message_id=msg_id,
                disable_notification=True,
            )
        except TelegramBadRequest as exc:
            if "not found" in str(exc.message).lower():
                return False
            return True
        except Exception:
            return True

        try:
            await self.bot.delete_message(channel_id, copied.message_id)
        except Exception:
            pass  # 副本删不掉（无删除权限）也无妨，只是频道里多一条空消息
        return True
