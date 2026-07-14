"""Pydantic 数据模型（请求体 / 响应体）"""
from typing import Optional

from pydantic import BaseModel, Field


class Event(BaseModel):
    id: int
    age: int
    year: str
    month: str
    day: str
    event: str
    annotation: Optional[str] = None
    literature_id: Optional[int] = None
    literature_title: Optional[str] = None
    literature_order: Optional[int] = None

    model_config = {"from_attributes": True}


class VisitRecord(BaseModel):
    user_id: str = Field(..., description="前端生成的匿名 UUID")
    year: str = Field(..., description="浏览的年份，如 1905")
    month: str = Field(default="", description="浏览的月份（中文），如 四月")
    day: str = Field(default="", description="浏览的日（中文），如 初一")


class LastVisit(BaseModel):
    year: Optional[str] = None
    month: Optional[str] = None
    day: Optional[str] = None


class BackgroundImage(BaseModel):
    id: int
    scene_type: str
    year: Optional[str] = None
    image_url: Optional[str] = None
    image_data: Optional[str] = None   # base64 编码的图片数据
    mime_type: str = "image/jpeg"
    title: Optional[str] = None
