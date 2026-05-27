"""
用户浏览历史路由

POST /api/visit                  → 记录（或更新）用户最后一次浏览
GET  /api/last-visit/{user_id}   → 查询用户上次浏览位置
"""
from fastapi import APIRouter, Depends

from ..database import get_cursor
from ..schemas import LastVisit, VisitRecord

router = APIRouter(tags=["浏览历史"])


@router.post("/visit", summary="记录用户最后一次浏览")
async def record_visit(body: VisitRecord, cur=Depends(get_cursor)):
    await cur.execute(
        """
        INSERT INTO user_visits (user_id, year, month, day)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            year       = VALUES(year),
            month      = VALUES(month),
            day        = VALUES(day),
            visited_at = CURRENT_TIMESTAMP
        """,
        (body.user_id, body.year, body.month, body.day),
    )
    return {"ok": True}


@router.get("/last-visit/{user_id}", summary="获取用户上次浏览位置", response_model=LastVisit)
async def get_last_visit(user_id: str, cur=Depends(get_cursor)):
    await cur.execute(
        "SELECT year, month, day FROM user_visits WHERE user_id = %s",
        (user_id,),
    )
    row = await cur.fetchone()
    if row is None:
        return LastVisit()
    return LastVisit(**row)
