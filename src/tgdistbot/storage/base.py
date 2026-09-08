"""存储接口（Protocol）。将来若想换成本地磁盘/S3，只需实现同样签名。"""

from __future__ import annotations

from typing import Protocol

from aiogram.types import Message, MessageId


class Storage(Protocol):
    """存储适配层约定。"""

    async def store(self, message: Message) -> tuple[int, int]:
        """把一条媒体消息存入后端，返回引用 ``(channel_id, msg_id)``。"""
        ...

    async def retrieve(self, user_id: int, channel_id: int, msg_id: int) -> MessageId:
        """把已存文件取回给 ``user_id``。"""
        ...
