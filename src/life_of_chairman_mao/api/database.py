"""
aiomysql 异步连接池，从项目 config 模块读取数据库配置。

settings.local.yml 中需包含:
    DATABASE:
      HOST:     127.0.0.1
      PORT:     3306
      USERNAME: root
      PASSWORD: your_password
      NAME:     jiaoyuan
"""
from typing import AsyncGenerator

import aiomysql

from ..config import settings

_pool: aiomysql.Pool | None = None


async def init_pool() -> None:
    global _pool
    _pool = await aiomysql.create_pool(
        host=settings.DATABASE.HOST,
        port=int(settings.DATABASE.PORT),
        user=settings.DATABASE.USERNAME,
        password=settings.DATABASE.PASSWORD,
        db=settings.DATABASE.NAME,
        charset="utf8mb4",
        autocommit=True,
        minsize=2,
        maxsize=10,
    )


async def close_pool() -> None:
    if _pool:
        _pool.close()
        await _pool.wait_closed()


async def get_cursor() -> AsyncGenerator[aiomysql.DictCursor, None]:
    """FastAPI Depends 依赖项，提供一个 DictCursor。"""
    async with _pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            yield cur
