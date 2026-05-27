"""
backgrounds router

GET /api/backgrounds/home        → 返回首页背景图（image_url 或 base64 数据）
GET /api/backgrounds/detail/{year} → 返回指定年份详情页背景图
"""
import base64
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_cursor
from ..schemas import BackgroundImage

router = APIRouter(tags=["背景图片"])


@router.get("/backgrounds/home", response_model=Optional[BackgroundImage])
async def get_home_background(cur=Depends(get_cursor)):
    await cur.execute(
        """
        SELECT id, scene_type, year, image_url, image_data, mime_type, title
        FROM background_images
        WHERE scene_type = 'home'
        ORDER BY sort_order ASC, id ASC
        LIMIT 1
        """
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="首页背景图未配置")
    return _to_schema(row)


@router.get("/backgrounds/detail/{year}", response_model=Optional[BackgroundImage])
async def get_detail_background(year: str, cur=Depends(get_cursor)):
    await cur.execute(
        """
        SELECT id, scene_type, year, image_url, image_data, mime_type, title
        FROM background_images
        WHERE scene_type = 'detail' AND year = %s
        ORDER BY sort_order ASC, id ASC
        LIMIT 1
        """,
        (year,),
    )
    row = await cur.fetchone()
    if not row:
        # 没有该年专属图，退回首页背景
        await cur.execute(
            """
            SELECT id, scene_type, year, image_url, image_data, mime_type, title
            FROM background_images
            WHERE scene_type = 'home'
            ORDER BY sort_order ASC, id ASC
            LIMIT 1
            """
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="背景图未配置")
    return _to_schema(row)


def _to_schema(row: dict) -> BackgroundImage:
    data_b64 = None
    if row.get("image_data"):
        raw = row["image_data"]
        if isinstance(raw, (bytes, bytearray)):
            data_b64 = base64.b64encode(raw).decode()
        else:
            data_b64 = raw  # already a string
    return BackgroundImage(
        id=row["id"],
        scene_type=row["scene_type"],
        year=row.get("year"),
        image_url=row.get("image_url"),
        image_data=data_b64,
        mime_type=row.get("mime_type", "image/jpeg"),
        title=row.get("title"),
    )
