"""WebSocket 实时推送服务状态，替代前端 1s 轮询"""
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import config
import process_manager

router = APIRouter()

# 广播间隔（秒）
PUSH_INTERVAL = 5

# 所有活跃的 WebSocket 连接
_connections: set[WebSocket] = set()


@router.websocket("/ws")
async def service_ws(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    try:
        # 连接后先推送一次全量数据
        await _push(websocket)

        # 持续接收客户端消息（心跳/日志请求等）
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=PUSH_INTERVAL)
                # 可扩展：处理客户端发来的消息
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # 超时 = 正常，继续下一个 push 周期
                pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _connections.discard(websocket)


async def _push(ws: WebSocket | None = None):
    """推送一次全量服务状态到指定连接（或所有连接）"""
    try:
        services = config.load_all()
        ids = [s["id"] for s in services]
        statuses = process_manager.collect_statuses(ids, services)
        ports = process_manager.collect_ports(ids, services)
        payload = {
            "type": "services",
            "services": services,
            "statuses": statuses,
            "ports": ports,
            "timestamp": __import__("time").time(),
        }
        targets = [ws] if ws else list(_connections)
        for conn in targets:
            try:
                await conn.send_json(payload)
            except Exception:
                _connections.discard(conn)
    except Exception:
        pass  # 序列化失败不崩溃


async def broadcast_forever():
    """后台协程：有连接时每 PUSH_INTERVAL 秒广播一次，空闲时睡久点"""
    while True:
        if _connections:
            await asyncio.sleep(PUSH_INTERVAL)
            await _push()
        else:
            await asyncio.sleep(30)  # 没客户端连接，半小时后再看
