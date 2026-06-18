"""服务配置 CRUD"""
from fastapi import APIRouter, HTTPException

from models import ServiceItem, ServiceConfig
import config
import process_manager
import log_store

router = APIRouter()


@router.get("/services")
def list_services():
    services = config.load_all()
    ids = [s["id"] for s in services]
    statuses = process_manager.collect_statuses(ids, services)
    ports = process_manager.collect_ports(ids, services)
    return {"services": services, "statuses": statuses, "ports": ports}


@router.post("/services")
def add_service(service: ServiceItem):
    if config.find_one(service.id):
        raise HTTPException(400, f"服务 '{service.id}' 已存在")
    config.add_one(service.model_dump())
    return {"ok": True}


@router.put("/services/{service_id}")
def update_service(service_id: str, service: ServiceConfig):
    result = config.update_one(service_id, service.model_dump())
    if result is None:
        raise HTTPException(404, f"服务 '{service_id}' 不存在")
    return {"ok": True}


@router.delete("/services/{service_id}")
def delete_service(service_id: str):
    process_manager.stop(service_id)
    log_store.remove_buffer(service_id)
    config.delete_one(service_id)
    return {"ok": True}
