"""程序入口：``python -m tgdistbot``。"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from .bot import build_dispatcher
from .config import Settings
from .db.engine import create_engine_and_sessionmaker
from .db.models import Base
from .deps import build_deps


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    settings = Settings()
    engine, session_factory = create_engine_and_sessionmaker(settings.database_url)

    # 建表（MVP 用 create_all；日后 schema 有数据后演进时再引入 Alembic 迁移）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = Bot(token=settings.bot_token)
    deps = build_deps(settings, bot, session_factory)
    dispatcher = build_dispatcher(deps)

    # long polling 前清掉遗留的 webhook 与未处理更新
    await bot.delete_webhook(drop_pending_updates=True)
    logging.getLogger(__name__).info("tg-dist-bot 启动")

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
