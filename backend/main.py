"""
OneStopService Backend
本地服务一条龙管理工具 — Python 进程管理器
"""
import atexit
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 把 backend/ 加入路径，方便各模块互相导入
sys.path.insert(0, str(Path(__file__).parent))

import process_manager
from routers.health import router as health_router
from routers.services import router as services_router
from routers.processes import router as processes_router

app = FastAPI(title="OneStopService Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",    # Vite dev
        "http://localhost:8710",    # Backend self
        "tauri://localhost",        # Tauri webview
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(services_router, prefix="/api")
app.include_router(processes_router, prefix="/api")

atexit.register(process_manager.cleanup_all)

if __name__ == "__main__":
    import uvicorn
    print("=== OneStopService Backend 启动于 http://127.0.0.1:8710 ===")
    uvicorn.run(app, host="127.0.0.1", port=8710, log_level="info")
