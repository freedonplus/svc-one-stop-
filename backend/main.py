"""
OneStopService Backend
本地服务一条龙管理工具 — Python 进程管理器
"""
import atexit
import os
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
from routers.ws import router as ws_router, broadcast_forever

app = FastAPI(title="OneStopService Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(services_router, prefix="/api")
app.include_router(processes_router, prefix="/api")
app.include_router(ws_router, prefix="/api")  # WebSocket 需加 /api 前缀

# 启动后台广播协程
@app.on_event("startup")
async def _start_broadcaster():
    import asyncio
    asyncio.create_task(broadcast_forever())

atexit.register(process_manager.cleanup_all)

if __name__ == "__main__":
    import logging
    import uvicorn

    # --noconsole 模式下 stderr/stdout 为 None，补一个兜底
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")

    # 隐藏当前控制台窗口（dev 模式下 python.exe 启动时闪现的黑框）
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), 0  # SW_HIDE
            )
        except Exception:
            pass

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("=== OneStopService Backend 启动于 http://127.0.0.1:8710 ===")
    uvicorn.run(app, host="127.0.0.1", port=8710, log_level="info",
                log_config=None)
