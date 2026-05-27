"""
年谱事件相关路由

GET /api/years               → 返回所有有记录的年份列表
GET /api/events/{year}       → 返回某年所有事件（按月日排序）
GET /api/search?q=关键词     → 全文搜索事件正文，最多返回 50 条
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..database import get_cursor
from ..schemas import Event

router = APIRouter(tags=["年谱"])


@router.get("/years", summary="获取所有有记录的年份")
async def list_years(cur=Depends(get_cursor)) -> list[str]:
    await cur.execute("SELECT DISTINCT year FROM chronology ORDER BY year")
    rows = await cur.fetchall()
    return [row["year"] for row in rows]


@router.get("/events/{year}", summary="获取某年所有事件", response_model=list[Event])
async def get_events_by_year(year: str, cur=Depends(get_cursor)):
    await cur.execute(
        """
        SELECT c.*, l.title AS literature_title
        FROM chronology c
        LEFT JOIN literature l ON c.literature_id = l.id
        WHERE c.year = %s
        ORDER BY c.month, c.day
        """,
        (year,),
    )
    return await cur.fetchall()


@router.get("/events/adjacent", summary="获取相邻日期（有数据的前一日和后一日）")
async def get_adjacent_days(
    year: str,
    month: str,
    day: str,
    cur=Depends(get_cursor),
):
    """
    返回 { prev: {year,month,day} | null, next: {year,month,day} | null }
    以 year·month·day 字符串拼接排序（数据库按年月日存中文，直接用 id 顺序更可靠）
    """
    # 取当前日期在 chronology 中最小的 id
    await cur.execute(
        "SELECT MIN(id) AS mid FROM chronology WHERE year=%s AND month=%s AND day=%s",
        (year, month, day),
    )
    row = await cur.fetchone()
    cur_id = row["mid"] if row else None

    if cur_id is None:
        return {"prev": None, "next": None}

    # prev: 找 id < cur_id 且 (year,month,day) 不同的最大 id 组
    await cur.execute(
        """
        SELECT year, month, day
        FROM chronology
        WHERE id < %s AND NOT (year=%s AND month=%s AND day=%s)
        ORDER BY id DESC
        LIMIT 1
        """,
        (cur_id, year, month, day),
    )
    prev_row = await cur.fetchone()

    # next: 找 id > cur_id 且 (year,month,day) 不同的最小 id 组
    await cur.execute(
        """
        SELECT year, month, day
        FROM chronology
        WHERE id > %s AND NOT (year=%s AND month=%s AND day=%s)
        ORDER BY id ASC
        LIMIT 1
        """,
        (cur_id, year, month, day),
    )
    next_row = await cur.fetchone()

    def to_dict(r):
        return {"year": r["year"], "month": r["month"], "day": r["day"]} if r else None

    return {"prev": to_dict(prev_row), "next": to_dict(next_row)}


@router.get("/search", summary="全文搜索事件正文", response_model=list[Event])
async def search_events(
    q: Annotated[str, Query(min_length=1, description="搜索关键词")],
    cur=Depends(get_cursor),
):
    like = f"%{q}%"
    await cur.execute(
        "SELECT * FROM chronology WHERE event LIKE %s OR annotation LIKE %s LIMIT 50",
        (like, like),
    )
    return await cur.fetchall()
