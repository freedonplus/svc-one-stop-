"""日志环形缓冲区，进程停止后仍保留"""
from collections import deque

LOG_MAX_LINES = 2000
_store: dict[str, deque] = {}


def get_buffer(service_id: str) -> deque | None:
    return _store.get(service_id)


def create_buffer(service_id: str) -> deque:
    buf = deque(maxlen=LOG_MAX_LINES)
    _store[service_id] = buf
    return buf


def remove_buffer(service_id: str):
    _store.pop(service_id, None)


def get_logs(service_id: str, lines: int = 200) -> list[str]:
    buf = _store.get(service_id)
    if buf is None:
        return []
    log_list = list(buf)
    if lines > 0:
        log_list = log_list[-lines:]
    return log_list
