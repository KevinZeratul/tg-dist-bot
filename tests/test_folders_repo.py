"""目录仓库测试。"""

from __future__ import annotations

from tgdistbot.db.repo.folders import FolderRepo
from tgdistbot.db.repo.media import MediaRepo


async def test_create_and_list_children(session_factory):
    repo = FolderRepo(session_factory)
    root = await repo.create("旅行")
    assert root.id > 0
    assert root.parent_id is None

    children = await repo.list_children(None)
    assert [c.name for c in children] == ["旅行"]


async def test_nested_and_path(session_factory):
    repo = FolderRepo(session_factory)
    parent = await repo.create("旅行")
    child = await repo.create("2024", parent.id)

    assert (await repo.get_path(child.id)) == "/旅行/2024"
    assert (await repo.get_path(None)) == "/"


async def test_rename(session_factory):
    repo = FolderRepo(session_factory)
    folder = await repo.create("旧名")
    assert await repo.rename(folder.id, "新名") is True
    assert (await repo.get(folder.id)).name == "新名"


async def test_soft_delete_removes_descendants_and_media(session_factory):
    folders = FolderRepo(session_factory)
    media = MediaRepo(session_factory)

    parent = await folders.create("A")
    child = await folders.create("B", parent.id)
    item = await media.create(channel_id=-100, msg_id=1, folder_id=child.id)

    assert await folders.soft_delete(parent.id) is True
    assert await folders.get(child.id) is None
    assert await media.get(item.id) is None
