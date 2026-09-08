"""鉴权仓库测试。"""

from __future__ import annotations

from tgdistbot.db.repo.access import AccessRepo
from tgdistbot.db.repo.folders import FolderRepo


async def test_grant_and_token(session_factory):
    folders = FolderRepo(session_factory)
    access = AccessRepo(session_factory)

    folder = await folders.create("私有")
    token = await access.create_token(folder.id)

    assert (await access.get_folder_by_token(token)) == folder.id
    assert await access.get_folder_by_token("不存在的token") is None

    await access.grant(folder.id, 123)
    assert await access.has_access(folder.id, 123) is True
    assert await access.has_access(folder.id, 999) is False
    assert (await access.list_granted_folder_ids(123)) == [folder.id]
