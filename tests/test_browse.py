"""浏览逻辑测试（目录树拼装）。"""

from __future__ import annotations

from unittest.mock import AsyncMock

from tgdistbot.config import Settings
from tgdistbot.deps import build_deps
from tgdistbot.handlers.browse import _build_tree


async def test_build_tree(session_factory):
    settings = Settings(bot_token="1:AA", channel_id=-100, owner_id=1)
    deps = build_deps(settings, AsyncMock(), session_factory)

    parent = await deps.repos.folders.create("旅行")
    await deps.repos.folders.create("2024", parent.id)
    await deps.repos.folders.create("家庭")

    tree = _build_tree(await deps.repos.folders.list_all())
    assert "旅行" in tree
    assert "2024" in tree
    assert "家庭" in tree
    # 子目录应缩进在父目录之后
    assert tree.index("旅行") < tree.index("2024")
