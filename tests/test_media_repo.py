"""文件仓库测试。"""

from __future__ import annotations

from tgdistbot.db.repo.folders import FolderRepo
from tgdistbot.db.repo.media import MediaRepo
from tgdistbot.db.repo.tags import TagRepo


async def _mk(media: MediaRepo):
    return await media.create(
        channel_id=-100,
        msg_id=1,
        filename="a.jpg",
        mime_type="image/jpeg",
        file_size=100,
    )


async def test_create_and_list(session_factory):
    media = MediaRepo(session_factory)
    await _mk(media)

    items = await media.list_in_folder(None)
    assert len(items) == 1
    assert items[0].filename == "a.jpg"
    assert items[0].tag_names == []


async def test_tagging(session_factory):
    media = MediaRepo(session_factory)
    tags = TagRepo(session_factory)

    item = await _mk(media)
    tag = await tags.get_or_create("travel")
    await media.add_tag(item.id, tag.id)

    got = await media.get(item.id)
    assert got.tag_names == ["travel"]

    by_tag = await media.list_by_tag("travel")
    assert [x.id for x in by_tag] == [item.id]


async def test_move(session_factory):
    media = MediaRepo(session_factory)
    folders = FolderRepo(session_factory)

    item = await _mk(media)
    folder = await folders.create("旅行")

    assert await media.move(item.id, folder.id) is True
    got = await media.get(item.id)
    assert got.folder_id == folder.id

    # 移回根目录
    assert await media.move(item.id, 0) is True
    assert (await media.get(item.id)).folder_id is None


async def test_search_and_soft_delete(session_factory):
    media = MediaRepo(session_factory)
    item = await _mk(media)

    assert len(await media.search("a.jpg")) == 1
    assert await media.soft_delete(item.id) is True
    assert await media.get(item.id) is None
    assert await media.search("a.jpg") == []
