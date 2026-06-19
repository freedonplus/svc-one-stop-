"""进程管理 — 启动、停止、状态查询"""
import os
import re
import signal
import subprocess
import sys
import threading
import time
from fastapi import HTTPException

import log_store


# ─── Windows 控制台隐藏工具 ───
if sys.platform == "win32":
    import ctypes
    _kernel32 = ctypes.windll.kernel32
    _user32 = ctypes.windll.user32
    # DETACHED_PROCESS: 子进程不关联任何控制台
    # CREATE_NO_WINDOW:  子进程不创建控制台窗口
    _HIDE_FLAGS = 0x00000008 | 0x08000000

    # 隐藏控制台标志（防止占用后忘记释放）
    _console_hidden = False

    def _ensure_hidden_console():
        """在父进程中分配一个隐藏的控制台。

        部分 Windows 控制台程序（mysqld、erl.exe 等）启动时检测到没有
        控制台会主动 AllocConsole() 弹出新窗口。解决方式：让父进程
        预先分配一个隐藏控制台，子进程直接继承它就老实了。
        """
        global _console_hidden
        if _console_hidden:
            return
        try:
            # 如果已有控制台（python.exe 运行），直接隐藏它
            hwnd = _kernel32.GetConsoleWindow()
            if hwnd:
                _user32.ShowWindow(hwnd, 0)  # SW_HIDE
            else:
                # pythonw 运行，无控制台 → 分配一个隐藏的
                if _kernel32.AllocConsole():
                    _user32.ShowWindow(_kernel32.GetConsoleWindow(), 0)
            _console_hidden = True
        except Exception:
            pass

    pass
else:
    pass


def _run_hidden(args, **kwargs):
    """运行子进程并隐藏控制台窗口（Windows），默认 capture_output"""
    if sys.platform == "win32":
        kwargs.setdefault("creationflags", _HIDE_FLAGS)
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("timeout", 15)  # 系统繁忙时 netstat/tasklist 可能较慢
    return subprocess.run(args, **kwargs)


_lock = threading.RLock()
# { service_id: { proc, reader_thread } }
_running: dict[str, dict] = {}
# 外部已运行的服务（本工具未启动，但检测到已在运行）
_external_running: set[str] = set()
# 最近手动停止的服务（冷却期内不重新检测）
_recently_stopped: dict[str, float] = {}
_STOP_COOLDOWN = 15  # 秒
# 文件日志尾随线程 { service_id: stop_event }
_file_watchers: dict[str, threading.Event] = {}


def _file_log_watcher(file_path: str, service_id: str, stop: threading.Event):
    """后台线程：尾随日志文件，新行追加到日志缓冲区"""
    buffer = log_store.get_buffer(service_id)
    if buffer is None:
        return
    import time
    # 等文件出现（最长 ~15 秒）
    f = None
    for _ in range(30):
        if stop.is_set():
            return
        try:
            f = open(file_path, "r", encoding="utf-8", errors="replace")
            break
        except FileNotFoundError:
            time.sleep(0.5)
    if f is None:
        buffer.append(f"[系统] 日志文件不可用: {file_path}")
        return
    with f:
        # 先读末尾 20 行作为上下文
        try:
            lines = f.readlines()
            for line in lines[-20:]:
                if stop.is_set():
                    return
                text = line.rstrip("\r\n")
                if text:
                    buffer.append(text)
        except Exception:
            pass
        # 持续尾随
        while not stop.is_set():
            try:
                line = f.readline()
                if line:
                    text = line.rstrip("\r\n")
                    if text:
                        buffer.append(text)
                else:
                    time.sleep(0.5)
            except Exception:
                time.sleep(1)


def _log_reader(proc: subprocess.Popen, service_id: str):
    """后台线程：不断读取子进程输出，存入日志缓冲区"""
    buffer = log_store.get_buffer(service_id)
    if buffer is None:
        return
    for line in iter(proc.stdout.readline, ""):
        if not line:
            break
        text = line.rstrip("\r\n")
        if text:
            buffer.append(text)
    proc.stdout.close()


def get_status(service_id: str) -> str:
    with _lock:
        if service_id in _external_running:
            return "running"
        entry = _running.get(service_id)
        if entry and entry["proc"].poll() is None:
            return "running"
    return "stopped"


def is_running(service_id: str) -> bool:
    return get_status(service_id) == "running"


def _syslog(service_id: str, msg: str):
    """写入一条系统日志"""
    buf = log_store.get_buffer(service_id)
    if buf is not None:
        buf.append(f"[系统] {msg}")


def _start_file_watcher(service_id: str, svc: dict):
    """如果服务配置了 log_file，启动文件日志尾随线程"""
    log_file = svc.get("log_file")
    if not log_file:
        return
    # 停止已有的 watcher
    old_ev = _file_watchers.pop(service_id, None)
    if old_ev:
        old_ev.set()
    stop_ev = threading.Event()
    _file_watchers[service_id] = stop_ev
    t = threading.Thread(
        target=_file_log_watcher,
        args=(log_file, service_id, stop_ev),
        daemon=True,
    )
    t.start()


def start(service_id: str, svc: dict) -> dict:
    """启动一个服务进程"""
    with _lock:
        if is_running(service_id):
            return {"ok": True, "pid": _running[service_id]["proc"].pid}

    # 创建日志缓冲区，写入启动标记
    log_store.create_buffer(service_id)

    # 文件日志尾随（如果配置了 log_file 则尾随日志文件）
    _start_file_watcher(service_id, svc)

    # 启动前杀掉占用冲突端口的旧进程（只杀端口占用，不杀同名 exe）
    svc_name = svc.get("name", "").lower()
    # 通过端口杀旧进程
    svc_port = svc.get("port")
    if svc_port:
        _kill_process_by_port(int(svc_port))
    cmd_port = _detect_port_from_command(svc)
    if cmd_port and (not svc_port or cmd_port != int(svc_port)):
        _kill_process_by_port(cmd_port)
    # Nacos 清理 Derby 锁（从服务配置读取 data 目录）
    if "nacos" in svc_name:
        derby_dirs = svc.get("derby_dirs",
                             [r"D:\tool\nacos\nacos\data\derby-data"])
        if isinstance(derby_dirs, str):
            derby_dirs = [derby_dirs]
        for d in derby_dirs:
            import pathlib
            p = pathlib.Path(d)
            if p.exists():
                import shutil as _su
                _su.rmtree(p, ignore_errors=True)
                _syslog(service_id, f"已清理 Derby 数据库锁 ({d})")

    _syslog(service_id, "正在启动...")
    _syslog(service_id, f"命令: {svc['command']}")

    cwd = svc.get("cwd") or None
    command = svc["command"]
    env = os.environ.copy()
    if svc.get("env"):
        env.update(svc["env"])

    try:
        if sys.platform == "win32":
            # 部分程序（mysqld、erl.exe）检测到无控制台会自建弹窗，
            # 对它们先分配一个隐藏控制台再启动，且不加 _HIDE_FLAGS（否则仍会弹窗）
            _is_console_app = "mysqld" in command.lower()
            if _is_console_app:
                _ensure_hidden_console()

            _si = subprocess.STARTUPINFO()
            _si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            _si.wShowWindow = subprocess.SW_HIDE

            # 判断是否需要 shell 解释器
            _need_shell = (
                command.lower().endswith((".bat", ".cmd"))
                or " && " in command
                or " || " in command
                or command.strip().startswith("set ")
            )
            proc = subprocess.Popen(
                command,
                shell=_need_shell,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                startupinfo=_si,
                creationflags=0 if _is_console_app else _HIDE_FLAGS,
            )
        else:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
    except Exception as e:
        _syslog(service_id, f"启动失败: {e}")
        raise HTTPException(500, f"启动失败: {e}")

    thread = threading.Thread(
        target=_log_reader, args=(proc, service_id), daemon=True
    )
    _running[service_id] = {"proc": proc, "thread": thread}
    thread.start()
    _recently_stopped.pop(service_id, None)  # 启动成功，清除冷却

    # 快速检测进程是否立即退出（常见于端口被占用/后台模式），每 100ms 探一次
    for _ in range(10):
        time.sleep(0.1)
        if proc.poll() is not None:
            break
    if proc.poll() is not None:
        exit_code = proc.poll()
        logs = log_store.get_logs(service_id, 30)
        err_text = "\n".join(logs).lower()

        if "already in use" in err_text or "bind" in err_text or "address in use" in err_text or "must be writable" in err_text:
            _syslog(service_id, "检测到服务已在外部运行中")
            _external_running.add(service_id)
            _running.pop(service_id, None)
            return {"ok": True, "external": True}

        # 批处理/后台模式：进程退出但无报错 → 等待端口就绪
        svc_port = svc.get("port")
        if exit_code == 0 and svc_port:
            _syslog(service_id, f"后台启动中，等待端口 {svc_port}...")
            _running.pop(service_id, None)
            # 最长等 8 秒（每秒查一次端口）
            for _ in range(8):
                time.sleep(1)
                if _check_port(int(svc_port)):
                    _external_running.add(service_id)
                    _syslog(service_id, f"端口 {svc_port} 已就绪")
                    return {"ok": True, "external": True}
            _syslog(service_id, f"端口 {svc_port} 未就绪，可能启动较慢")
            # 即使没有立即就绪也返回成功——后台持续检测
            return {"ok": True, "external": True, "pending": True}

    return {"ok": True, "pid": proc.pid}


def detect_status(service_id: str, svc: dict) -> dict:
    """启动进程（不等待检测，检测由前端负责）"""
    result = start(service_id, svc)
    return {**result, "status": get_status(service_id)}


def _kill_process_by_port(port: int) -> bool:
    """通过监听端口终止进程"""
    try:
        out = _run_hidden(["netstat", "-ano"], timeout=3).stdout
        target_pid = None
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and "LISTENING" in line:
                addr = parts[1]
                pid = parts[4]
                if addr.endswith(f":{port}") and pid.isdigit():
                    target_pid = pid
                    break
        if target_pid:
            _run_hidden(["taskkill", "/F", "/PID", target_pid])
            return True
    except:
        pass
    return False


def _mark_stopped(service_id: str):
    """标记服务已手动停止，进入冷却"""
    _recently_stopped[service_id] = time.time()


def _is_on_cooldown(service_id: str) -> bool:
    """检查服务是否在停止冷却期内"""
    ts = _recently_stopped.get(service_id)
    return ts is not None and (time.time() - ts) < _STOP_COOLDOWN


def stop(service_id: str, svc: dict | None = None) -> dict:
    """停止一个服务进程（日志保留）"""
    _mark_stopped(service_id)
    # 停止文件日志尾随
    _stop_ev = _file_watchers.pop(service_id, None)
    if _stop_ev:
        _stop_ev.set()
    # 外部运行的服务 - 通过端口查进程并终止
    if service_id in _external_running:
        _external_running.discard(service_id)
        _syslog(service_id, "正在停止外部服务...")
        # 从日志或系统扫描找端口
        port = _detect_port_from_logs(service_id)
        if not port and svc:
            cmd = svc.get("command", "")
            exe = _get_exe_name(cmd)
            listening = _cached_scan("ports", _scan_system_ports)
            all_procs = _cached_scan("procs", _scan_system_processes)
            for pid in all_procs.get(exe, set()):
                for p in listening.get(pid, set()):
                    port = int(p)
                    break
                if port:
                    break
        if port:
            _kill_process_by_port(port)
        _syslog(service_id, "已停止")
        return {"ok": True, "message": "已停止"}

    _syslog(service_id, "正在停止...")

    with _lock:
        entry = _running.pop(service_id, None)
    if entry is None:
        _syslog(service_id, "未在运行")
        return {"ok": True, "message": "未在运行"}

    proc = entry["proc"]
    if proc.poll() is not None:
        _syslog(service_id, "进程已自行退出")
        return {"ok": True, "message": "已自行退出"}

    try:
        if sys.platform == "win32":
            _run_hidden(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            )
        else:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    except Exception:
        proc.kill()

    _syslog(service_id, "已停止")
    return {"ok": True}


def cleanup_all():
    """退出时清理所有子进程"""
    for sid in list(_running.keys()):
        try:
            stop(sid)
        except Exception:
            pass


def _check_port(port: int) -> bool:
    """检查本地端口是否已被占用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0
    except:
        return False
    finally:
        sock.close()


def _scan_system_ports() -> dict[str, set[str]]:
    """扫描系统所有监听端口 → {pid: {port, ...}}"""
    result = {}
    try:
        out = _run_hidden(["netstat", "-ano"], timeout=3).stdout
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and "LISTENING" in line:
                addr = parts[1]
                pid = parts[4]
                port = addr.split(":")[-1]
                if pid.isdigit() and port.isdigit():
                    result.setdefault(pid, set()).add(port)
    except:
        pass
    return result


def _scan_system_processes() -> dict[str, set[str]]:
    """扫描系统所有进程 → {exe_name: {pid, ...}}"""
    result = {}
    try:
        out = _run_hidden(["tasklist", "/FO", "CSV"]).stdout
        for line in out.splitlines()[1:]:
            parts = line.split(",")
            if len(parts) >= 2:
                exe = parts[0].strip('"').lower()
                pid = parts[1].strip('"')
                if pid.isdigit():
                    result.setdefault(exe, set()).add(pid)
    except:
        pass
    return result


def _get_exe_name(command: str) -> str:
    """从命令中提取可执行文件名"""
    exe = os.path.basename(command.split(None, 1)[0])
    if not exe.lower().endswith('.exe'):
        exe += '.exe'
    return exe.lower()


def collect_statuses(service_ids: list[str], services: list[dict] | None = None) -> dict[str, str]:
    """批量获取状态，同时清理已退出的残留记录。services 可选传入以做外部进程检测。"""
    # 全系统扫描一次，供所有服务复用
    listening = _cached_scan("ports", _scan_system_ports)   # {pid: {port,...}}
    all_procs = _cached_scan("procs", _scan_system_processes)  # {exe: {pid,...}}

    statuses = {}
    svc_map = {s["id"]: s for s in (services or [])}
    for sid in service_ids:
        # 冷却期内的服务不检测
        if _is_on_cooldown(sid):
            statuses[sid] = "stopped"
            continue
        # 外部运行的服务也要重新验证
        if sid in _external_running:
            if _check_service_running(sid, svc_map, listening, all_procs):
                statuses[sid] = "running"
                continue
            _external_running.discard(sid)
            statuses[sid] = "stopped"
            continue

        entry = _running.get(sid)
        if entry and entry["proc"].poll() is None:
            statuses[sid] = "running"
        else:
            _running.pop(sid, None)
            if _check_service_running(sid, svc_map, listening, all_procs):
                _external_running.add(sid)
                _recently_stopped.pop(sid, None)
                statuses[sid] = "running"
                continue
            statuses[sid] = "stopped"
    return statuses


# ─── 系统扫描缓存（避免每 5 秒重复 netstat 级开销） ───
_scan_cache: dict[str, tuple[float, object]] = {}
_SCAN_CACHE_TTL = 2.0  # 秒

def _cached_scan(key: str, fn, *args):
    now = time.time()
    cached = _scan_cache.get(key)
    if cached and now - cached[0] < _SCAN_CACHE_TTL:
        return cached[1]
    result = fn(*args)
    _scan_cache[key] = (now, result)
    return result


# 通用运行时 exe 名——不靠进程名匹配（多个服务共用一个 exe，无法区分）
_GENERIC_RUNTIME_EXES = {"java.exe", "javaw.exe", "python.exe", "python3.exe", "node.exe", "npm.exe"}


def _check_service_running(sid: str, svc_map: dict, listening: dict, all_procs: dict) -> bool:
    """综合检测服务是否在外部运行中"""
    svc = svc_map.get(sid)
    if not svc:
        return False

    cmd = svc.get("command", "")
    exe = _get_exe_name(cmd)

    # 1. 进程名匹配（跳过通用运行时，避免 java.exe 误匹配）
    if exe not in _GENERIC_RUNTIME_EXES:
        pids = all_procs.get(exe, set())
        for pid in pids:
            if listening.get(pid):
                return True

    # 2. 别名匹配：RabbitMQ 跑在 erl.exe 下
    svc_name = svc.get("name", "").lower()
    if "rabbit" in svc_name:
        for alias in ("erl.exe", "beam.exe"):
            for pid in all_procs.get(alias, set()):
                if listening.get(pid):
                    return True

    # 3. 日志提取端口检测
    log_port = _detect_port_from_logs(sid)
    if log_port and _check_port(log_port):
        return True

    # 4. 从命令中提取端口检测（如 --server.port=8888）
    cmd_port = _detect_port_from_command(svc)
    if cmd_port and _check_port(cmd_port):
        return True

    # 5. 纯端口检测：服务配置了 port 字段，直接检查端口是否在监听
    svc_port = svc.get("port")
    if svc_port and _check_port(int(svc_port)):
        return True

    return False


# ─── 端口检测 ───

# 精确匹配模式（高优先级）—— 显式指定的端口
_EXPLICIT_PORT_PATTERNS = [
    r"server\.port[=:](\d{4,5})",         # Spring Boot: --server.port=8888 或 server.port: 8888
    r"--port[=:](\d{4,5})",               # 命令行: --port=8888
    r"-Dcsp\.sentinel\.api\.port[=:](\d{4,5})",  # Sentinel API 端口（明确指定时）
]
# 通用匹配模式（低优先级）
_GENERIC_PORT_PATTERNS = [
    r"port[:\s]*(\d{4,5})",
    r"Port[:\s]*(\d{4,5})",
    r":(\d{4,5})\s*\)",                  # Redis: "on port 6379"
    r"listening on[^\d]*(\d{4,5})",
    r"bind-address[^:]*:[^\d]*(\d{4,5})",
]


def _detect_port_from_command(svc: dict) -> int | None:
    """从服务配置的 command 中提取端口参数（如 --server.port=8888）"""
    cmd = svc.get("command", "")
    for pattern in _EXPLICIT_PORT_PATTERNS:
        m = re.search(pattern, cmd)
        if m:
            port = int(m.group(1))
            if 1 <= port <= 65535:
                return port
    return None


def _detect_port_from_logs(service_id: str) -> int | None:
    """从日志中提取端口号
    优先级：精确匹配（server.port=） > 通用匹配（取最小端口避免 33060 干扰）
    """
    logs = log_store.get_logs(service_id, 200)
    text = "\n".join(logs)

    # 先试精确模式
    for pattern in _EXPLICIT_PORT_PATTERNS:
        for m in re.finditer(pattern, text):
            port = int(m.group(1))
            if 1 <= port <= 65535:
                return port

    # 再试通用模式，取最小端口（避免 MySQL 33060 抢在 3306 前）
    found = []
    for pattern in _GENERIC_PORT_PATTERNS:
        for m in re.finditer(pattern, text):
            port = int(m.group(1))
            if 1 <= port <= 65535:
                found.append(port)
    return min(found) if found else None


def collect_ports(service_ids: list[str], services: list[dict] | None = None) -> dict[str, int]:
    """批量检测各服务的端口号"""
    listening = _cached_scan("ports", _scan_system_ports)
    all_procs = _cached_scan("procs", _scan_system_processes)
    svc_map = {s["id"]: s for s in (services or [])}
    ports = {}
    for sid in service_ids:
        svc = svc_map.get(sid)
        if not svc:
            continue

        # 0. 优先使用服务配置中明确指定的 port
        configured_port = svc.get("port")
        if configured_port and _check_port(int(configured_port)):
            ports[sid] = int(configured_port)
            continue

        # 0.5 从命令中提取端口（如 --server.port=8888）
        cmd_port = _detect_port_from_command(svc)
        if cmd_port and _check_port(cmd_port):
            ports[sid] = cmd_port
            continue

        # 1. 日志检测
        p = _detect_port_from_logs(sid)
        if p:
            ports[sid] = p
            continue

        exe = _get_exe_name(svc.get("command", ""))

        # 2. 进程名匹配（跳过通用运行时，避免 java.exe 误匹配）
        if exe not in _GENERIC_RUNTIME_EXES:
            for pid in all_procs.get(exe, set()):
                port_list = sorted(int(p) for p in listening.get(pid, set()))
                if port_list:
                    ports[sid] = port_list[0]
                    break

        # 3. 别名匹配（RabbitMQ → erl.exe）
        if sid not in ports and "rabbit" in svc.get("name", "").lower():
            for alias in ("erl.exe", "beam.exe"):
                for pid in all_procs.get(alias, set()):
                    port_list = sorted(int(p) for p in listening.get(pid, set()))
                    if port_list:
                        ports[sid] = port_list[0]
                        break
                if sid in ports:
                    break

        # 4. 以上都检测不到时，尝试从命令提取端口
        if sid not in ports:
            cmd_port = _detect_port_from_command(svc)
            if cmd_port:
                ports[sid] = cmd_port

        # 5. 仍然没有，使用配置的 port 字段（即使不通也显示链接）
        if sid not in ports and svc.get("port"):
            ports[sid] = int(svc["port"])
    return ports


# 进程列表暴露给 routers 直接读取状态
def get_all_processes():
    return _running
