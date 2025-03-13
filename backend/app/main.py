from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(
    title="Kimi Chat API",
    description="API for Kimi AI Chat Assistant",
    version="1.0.0",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载API路由
app.include_router(api_router, prefix="/api")

# 创建音频文件存储目录
os.makedirs(settings.AUDIO_FILES_DIR, exist_ok=True)

# 挂载静态文件服务，用于音频文件访问
app.mount("/audio", StaticFiles(directory=settings.AUDIO_FILES_DIR), name="audio")

@app.get("/")
async def root():
    """健康检查端点"""
    return {"status": "ok", "message": "Kimi Chat API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)