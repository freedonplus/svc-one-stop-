"""进程启停、日志、批量操作"""
from fastapi import APIRouter, HTTPException

import config
import process_manager
import log_store

router = APIRouter()


@router.post("/services/{service_id}/start")
def start_service(service_id: str):
    svc = config.find_one(service_id)
    if not svc:
        raise HTTPException(404, f"服务 '{service_id}' 不存在")
    return process_manager.detect_status(service_id, svc)


@router.post("/services/{service_id}/stop")
def stop_service(service_id: str):
    svc = config.find_one(service_id)
    return process_manager.stop(service_id, svc)


@router.get("/services/{service_id}/logs")
def get_logs(service_id: str, lines: int = 200):
    running = process_manager.is_running(service_id)
    logs = log_store.get_logs(service_id, lines)
    return {"logs": logs, "running": running}


@router.delete("/services/{service_id}/logs")
def clear_logs(service_id: str):
    log_store.remove_buffer(service_id)
    return {"ok": True}


@router.post("/services/batch/start")
def batch_start(ids: list[str]):
    results = {}
    for sid in ids:
        svc = config.find_one(sid)
        if svc:
            try:
                results[sid] = process_manager.start(sid, svc)
            except Exception as e:
                results[sid] = {"ok": False, "error": str(e)}
        else:
            results[sid] = {"ok": False, "error": "未找到"}
    return {"results": results}


@router.post("/services/batch/stop")
def batch_stop(ids: list[str]):
    results = {}
    for sid in ids:
        svc = config.find_one(sid)
        results[sid] = process_manager.stop(sid, svc)
    return {"results": results}
