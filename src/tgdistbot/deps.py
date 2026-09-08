"""依赖注入容器。"""

from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .config import Settings
from .db.repo.access import AccessRepo
from .db.repo.folders import FolderRepo
from .db.repo.media import MediaRepo
from .db.repo.tags import TagRepo
from .storage.channel import TelegramChannelStorage


@dataclass
class Repos:
    """聚合所有仓库，方便整体注入。"""

    folders: FolderRepo
    media: MediaRepo
    tags: TagRepo
    access: AccessRepo


@dataclass
class Deps:
    """依赖容器：handler 通过 ``deps: Deps`` 形参拿到所有需要的东西。

    由 :class:`DepsMiddleware` 在每次事件进入时注入到 handler 的 data 里。
    """

    settings: Settings
    bot: Bot
    storage: TelegramChannelStorage
    repos: Repos


def build_deps(
    settings: Settings,
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
) -> Deps:
    """装配依赖：所有实例在这里创建一次，避免散落各处 new。"""
    return Deps(
        settings=settings,
        bot=bot,
        storage=TelegramChannelStorage(bot, settings.channel_id),
        repos=Repos(
            folders=FolderRepo(session_factory),
            media=MediaRepo(session_factory),
            tags=TagRepo(session_factory),
            access=AccessRepo(session_factory),
        ),
    )
