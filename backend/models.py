"""Pydantic 数据模型"""
from typing import Optional
from pydantic import BaseModel


class ServiceConfig(BaseModel):
    """新增/更新服务时的请求体"""
    name: str
    command: str
    cwd: Optional[str] = None
    port: Optional[int] = None
    env: Optional[dict] = None
    color: Optional[str] = None
    group: Optional[str] = None
    version: Optional[str] = None
    url: Optional[str] = None


class ServiceItem(ServiceConfig):
    """带 id 的完整服务记录"""
    id: str


class ServiceListResponse(BaseModel):
    services: list[dict]
    statuses: dict[str, str]
