"""
FastAPI 应用入口

启动命令（开发）:
    uvicorn life_of_chairman_mao.api.main:app --reload --port 8000

启动命令（生产）:
    uvicorn life_of_chairman_mao.api.main:app --host 0.0.0.0 --port 8000 --workers 4
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import close_pool, init_pool
from .routers import chronology, visits, backgrounds


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(
    title="教员的一生 API",
    description="毛泽东年谱可视化网站后端接口",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chronology.router, prefix="/api")
app.include_router(visits.router, prefix="/api")
app.include_router(backgrounds.router, prefix="/api")


@app.get("/", tags=["健康检查"])
async def root():
    return {"status": "ok", "service": "life_of_chairman_mao"}
