"""配置：集中从环境变量 / .env 读取，启动即校验（fail-fast）。"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。所有字段都从环境变量或 .env 文件读取。

    使用方式：``settings = Settings()`` —— 缺失或非法的必填字段会在
    实例化时立刻抛出异常，避免运行期才暴露问题。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Bot token，来自 @BotFather
    bot_token: str

    # 私有频道 ID（字节存储位置），机器人需是频道管理员
    channel_id: int

    # 所有者（你）的 Telegram 用户 ID
    owner_id: int

    # 额外管理员 ID，空格分隔的字符串，如 "123 456"（可选）
    admins: str = ""

    # SQLite 数据库地址
    database_url: str = "sqlite+aiosqlite:///tgdistbot.db"

    @property
    def admin_ids(self) -> set[int]:
        """所有能管理这个 bot 的用户 ID（owner 恒在内）。"""
        ids = {self.owner_id}
        for part in self.admins.split():
            part = part.strip()
            if part.isdigit():
                ids.add(int(part))
        return ids
