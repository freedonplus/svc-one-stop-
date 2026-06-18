"""服务配置的 JSON 文件读写"""
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "services.json"


def load_all() -> list[dict]:
    if not CONFIG_FILE.exists():
        return []
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_all(services: list[dict]):
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
