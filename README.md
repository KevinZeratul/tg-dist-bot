# tg-dist-bot

把 Telegram 当成你的**个人网盘**：管理照片/视频，支持目录、标签、文件夹级鉴权。

## 工作原理

文件的**字节存在 Telegram 私有频道里**（用 `copy_message` 转发进去，服务器零存储成本、无限容量、任意设备秒级取回）；而**目录、标签、鉴权等元数据存在本地 SQLite**。

关键点：`copy_message` 是 Telegram 服务端操作，**不受 Bot API 的 20MB 下载限制**，单文件上限就是 Telegram 自身的 2GB（普通）/4GB（Premium）。所以用纯 Bot API 即可实现，无需用户机器人（userbot）。

```
Telegram 用户
   ↕ Bot API (long polling)
aiogram 3 Bot
   ├─ handlers/  上传 · 浏览 · 目录 · 标签 · 分享
   ├─ storage/   TelegramChannelStorage（copy 进频道 / copy 回用户）
   └─ db/        SQLAlchemy async + SQLite（folders / media_items / tags / folder_access / share_tokens）
```

## 功能

- 上传照片/视频/文件到当前目录（自动记录相册分组）
- 目录树：创建 / 重命名 / 删除（软删除）/ 移动 / 导航，`/tree` 看全貌
- 标签：打标 / 去标 / 按标签查找
- 搜索：一个关键词同时搜文件名、目录名、标签
- 鉴权：默认仅 owner；`/share` 生成 deep-link，受邀者只能访问被授权文件夹（只读）
- 健壮性：网络瞬断自动重试；频道里被手动删掉的文件会自动识别并清理失效索引（`/purge` 一键批量清理）

## 快速开始

### 1. 前置准备

1. 在 [@BotFather](https://t.me/BotFather) 创建一个 bot，拿到 **token**。
2. 在 Telegram 里创建一个**私有频道**，把 bot 设为该频道的**管理员**。记下频道 ID（把频道里的一条消息转发给 [@userinfobot](https://t.me/userinfobot) 即可看到形如 `-100...` 的 ID）。
3. 用 [@userinfobot](https://t.me/userinfobot) 查你自己的 **user ID**。

### 2. 配置

```bash
cp .env.example .env
```

编辑 `.env` 填入 `BOT_TOKEN`、`CHANNEL_ID`、`OWNER_ID`。

### 3. 安装与启动

```bash
uv sync                 # 安装依赖（或 pip install -e .）
uv run python -m tgdistbot
```

启动后第一次会自动建表（`tgdistbot.db`）。给 bot 发 `/help` 看全部命令。

## 命令清单

| 命令 | 说明 |
|---|---|
| `/files` 或 `/ls` | 查看当前目录（含按钮导航） |
| `/cd <id>` / `/up` | 进入目录 / 返回上级（0=根） |
| `/tree` | 查看完整目录树 |
| `/channel` | 打开媒体存储频道（直接翻看媒体） |
| `/mkdir <名称>` | 在当前目录新建目录 |
| `/rename <id> <新名>` | 重命名目录 |
| `/rmdir <id>` | 删除目录（软删除，不删频道文件） |
| 发照片/视频/文件 | 上传到当前目录 |
| `/mv <文件id> <目录id>` | 移动文件（0=根） |
| `/rm <文件id>` | 删除文件（软删除） |
| `/purge` | 一键清除失效索引（频道里已删的） |
| `/tag <文件id> <标签...>` | 打标签 |
| `/untag <文件id> <标签>` | 去标签 |
| `/tags [文件id]` | 列出标签 |
| `/find <标签>` | 按标签列出文件 |
| `/search <关键词>` | 搜文件名/目录名/标签 |
| `/share <目录id> [秒]` | 生成分享链接 |

## 使用约定

**三个角色分工**：bot = 操作界面，channel = 仓库（存字节），SQLite = 账本（元数据）。日常只跟 bot 说话，channel 用来翻看媒体。

- **上传 / 删除都走 bot**：手动往频道塞文件，bot 的账本不知道，等于"看不见"。
- **频道里手动删了文件没关系**：点它时 bot 会自动识别并清除失效索引；或用 `/purge` 批量清理。
- **别手动改频道**：频道里的消息是字节的唯一存放处，删了就真没了。

## 目录结构

```
src/tgdistbot/
  __main__.py        入口
  config.py          配置（pydantic-settings，读 .env，启动即校验）
  bot.py             Dispatcher 装配
  deps.py            依赖注入容器（Deps / Repos）
  middleware.py      把 Deps 注入 handler
  keyboards.py       内联键盘 + 回调数据
  handlers/          消息处理器（start/upload/browse/folder/tag/share/auth/nav）
  storage/           存储适配层（channel.py 为核心）
  db/                SQLAlchemy 模型、引擎、仓库（repo/*.py 每个实体一个）
```

分层依赖单向：`handlers → storage / db.repo → db.models`。

## 如何扩展

- **加一条命令**：在对应 `handlers/*.py` 里用 `@router.message(Command("xxx"), IsAdmin())` 写 handler，通过 `deps.repos.*` 访问数据。若涉及当前目录，用 `from .nav import current_folder`。
- **加一个字段**：改 `db/models.py` 对应模型 → 同步 `db/schemas.py` 的 DTO 与仓库的 `_to_dto` 转换。注意：MVP 用 `create_all` 建表，**有数据后再改表需引入 Alembic 迁移**。
- **换存储后端**：实现 `storage/base.py` 里 `Storage` 协议的两个方法，再在 `deps.py` 里替换 `TelegramChannelStorage`。
- **换数据库**：改 `DATABASE_URL`（如 Postgres），其余代码不变。

## 测试

```bash
uv run pytest
```

覆盖仓库层与存储适配层（不联网）。handler 层建议手动端到端验证。

## 技术栈

Python 3.11+ · aiogram 3 · SQLAlchemy 2.0 (async) · aiosqlite · pydantic-settings · pytest
