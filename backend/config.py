"""服务配置的 JSON 文件读写"""
import json
import os
import threading
from pathlib import Path

# 数据文件始终在 backend/services.json
CONFIG_FILE = Path(__file__).parent / "services.json"

# 写锁：防止并发请求导致数据丢失
_write_lock = threading.Lock()

# ─── 迁移旧数据（从 %APPDATA%/OneStopService 搬到项目目录） ───
_old = Path(os.environ["APPDATA"]) / "OneStopService" / "services.json" if os.environ.get("APPDATA") else None
if _old and _old.exists() and not CONFIG_FILE.exists():
    try:
        data = json.loads(_old.read_text(encoding="utf-8"))
        if data:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[config] 已从 {_old} 迁移 {len(data)} 条服务配置")
    except Exception:
        pass


def load_all() -> list[dict]:
    if not CONFIG_FILE.exists():
        return []
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_all(services: list[dict]):
    with _write_lock:
        CONFIG_FILE.write_text(
            json.dumps(services, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def find_one(service_id: str) -> dict | None:
    services = load_all()
    for s in services:
        if s["id"] == service_id:
            return s
    return None


def add_one(service: dict) -> list[dict]:
    services = load_all()
    services.append(service)
    save_all(services)
    return services


def update_one(service_id: str, data: dict) -> dict | None:
    services = load_all()
    for s in services:
        if s["id"] == service_id:
            s.update(data)
            save_all(services)
            return s
    return None


def delete_one(service_id: str) -> list[dict]:
    services = load_all()
    services = [s for s in services if s["id"] != service_id]
    save_all(services)
    return services
