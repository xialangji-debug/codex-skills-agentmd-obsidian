import json
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback


SERVER_NAME = "aboot-download"
SERVER_VERSION = "0.1.0"
HOME = os.path.expanduser("~")
DEFAULT_TOOL = os.environ.get(
    "ABOOT_DOWNLOAD_TOOL",
    os.path.join(HOME, "Desktop", "aboot-tools-2023.08.27-win-x64", "adownload.exe"),
)
FALLBACK_TOOL = os.path.join(
    HOME,
    "Desktop",
    "inside",
    "lt52_XCX_GB_WK",
    "prebuilts",
    "misc",
    "windows-x86",
    "adownload.exe",
)
DEFAULT_PORTS = os.environ.get("ABOOT_DEFAULT_PORTS", "COM14")
DEFAULT_SEARCH_ROOT = os.path.join(HOME, "Desktop", "inside")
LOG_DIR = os.path.join(HOME, ".codex", "aboot-download", "logs")
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


TOOLS = [
    {
        "name": "aboot_status",
        "description": "Inspect local Aboot/adownload readiness: tool path, ASR USB devices, visible COM ports, and CATStudio/adownload blockers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "releasePackage": {"type": "string", "description": "Optional firmware zip path to validate."},
                "adownloadPath": {"type": "string", "description": "Optional adownload.exe path."},
                "ports": {
                    "description": "Preferred serial ports, either comma-separated string or string array.",
                    "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                },
            },
        },
    },
    {
        "name": "aboot_list_release_packages",
        "description": "Find recent ASR release package zip files under a workspace root. Source zips are excluded by default.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "default": DEFAULT_SEARCH_ROOT},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "includeSource": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "aboot_kill_download_processes",
        "description": "Stop stale adownload.exe processes. CATStudio and AbootDownload GUI are closed only when explicitly requested.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "closeCatstudio": {"type": "boolean", "default": False},
                "closeAbootGui": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "aboot_flash",
        "description": "Run adownload.exe to flash an ASR release package. Saves stdout/stderr to a timestamped log and returns structured status.",
        "inputSchema": {
            "type": "object",
            "required": ["releasePackage"],
            "properties": {
                "releasePackage": {"type": "string", "description": "Firmware release zip. Do not use *_source.zip."},
                "ports": {
                    "description": "Serial ports, comma-separated string or string array. Default comes from ABOOT_DEFAULT_PORTS.",
                    "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                },
                "adownloadPath": {"type": "string", "description": "Optional adownload.exe path."},
                "baud": {"type": "integer", "default": 115200},
                "autoEnableUsb": {"type": "boolean", "default": True},
                "atFallback": {"type": "boolean", "default": True},
                "usbOnly": {"type": "boolean", "default": False},
                "reboot": {"type": "boolean", "default": True},
                "production": {"type": "boolean", "default": False},
                "quit": {"type": "boolean", "default": True},
                "closeCatstudio": {"type": "boolean", "default": False},
                "closeAbootGui": {"type": "boolean", "default": False},
                "killExistingAdownload": {"type": "boolean", "default": True},
                "timeoutSec": {"type": "integer", "minimum": 30, "maximum": 3600, "default": 900},
                "dryRun": {"type": "boolean", "default": False},
            },
        },
    },
]


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def normalize_ports(value):
    if value is None:
        value = DEFAULT_PORTS
    if isinstance(value, list):
        parts = value
    else:
        parts = str(value).split(",")
    clean = []
    for part in parts:
        port = str(part).strip()
        if port:
            clean.append(port.upper())
    return clean or [DEFAULT_PORTS]


def run_process(args, timeout=20):
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            universal_newlines=True,
            creationflags=CREATE_NO_WINDOW,
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": stdout, "stderr": stderr}
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass
        stdout, stderr = proc.communicate()
        return {"ok": False, "returncode": None, "stdout": stdout, "stderr": stderr, "timeout": True}
    except Exception as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}


def run_powershell(script, timeout=20):
    result = run_process(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        timeout=timeout,
    )
    if not result.get("stdout", "").strip():
        return result, None
    try:
        return result, json.loads(result["stdout"])
    except Exception:
        return result, None


def detect_adownload(path=None):
    candidates = []
    if path:
        candidates.append(path)
    candidates.append(DEFAULT_TOOL)
    candidates.append(FALLBACK_TOOL)
    for item in candidates:
        if item and os.path.exists(item):
            return os.path.abspath(item)
    return os.path.abspath(candidates[0]) if candidates else DEFAULT_TOOL


def get_processes():
    script = r"""
$items = Get-Process | Where-Object { $_.ProcessName -match '^(CATStudio|adownload|aboot)$' } |
    Select-Object ProcessName,Id,CPU,StartTime,Responding
$items | ConvertTo-Json -Depth 4
"""
    _, data = run_powershell(script, timeout=10)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    return data


def get_asr_devices():
    script = r"""
$items = Get-CimInstance Win32_PnPEntity |
    Where-Object { $_.Name -match 'ASR|Serial Download|USB Download|Modem|COM14|COM15|COM16|VID_2ECC|PID_3010' -or $_.DeviceID -match 'VID_2ECC|PID_3010' } |
    Select-Object Name,Status,ConfigManagerErrorCode,DeviceID
$items | ConvertTo-Json -Depth 4
"""
    _, data = run_powershell(script, timeout=15)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    return data


def get_serial_devices():
    script = r"""
$items = Get-CimInstance Win32_PnPEntity |
    Where-Object { $_.Name -match '\(COM[0-9]+\)' } |
    Select-Object Name,Status,ConfigManagerErrorCode,DeviceID
$items | ConvertTo-Json -Depth 4
"""
    _, data = run_powershell(script, timeout=15)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    return data


def get_visible_ports():
    script = r"""
[System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object | ConvertTo-Json
"""
    _, data = run_powershell(script, timeout=10)
    if data is None:
        return []
    if isinstance(data, str):
        return [data]
    return data


def validate_package(path):
    if not path:
        return {"path": None, "exists": False}
    abs_path = os.path.abspath(path)
    info = {"path": abs_path, "exists": os.path.exists(abs_path), "isSourceZip": abs_path.lower().endswith("_source.zip")}
    if info["exists"]:
        stat = os.stat(abs_path)
        info["sizeBytes"] = stat.st_size
        info["mtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
    return info


def status(args):
    tool = detect_adownload(args.get("adownloadPath"))
    package = validate_package(args.get("releasePackage"))
    ports = normalize_ports(args.get("ports"))
    processes = get_processes()
    catstudio = [p for p in processes if str(p.get("ProcessName", "")).lower() == "catstudio"]
    adownload = [p for p in processes if str(p.get("ProcessName", "")).lower() == "adownload"]
    aboot = [p for p in processes if str(p.get("ProcessName", "")).lower() == "aboot"]
    return {
        "adownloadPath": tool,
        "adownloadExists": os.path.exists(tool),
        "releasePackage": package,
        "requestedPorts": ports,
        "visiblePorts": get_visible_ports(),
        "serialDevices": get_serial_devices(),
        "asrDevices": get_asr_devices(),
        "processes": processes,
        "blockers": {
            "catstudioRunning": bool(catstudio),
            "adownloadRunning": bool(adownload),
            "abootGuiRunning": bool(aboot),
            "note": "CATStudio Logger/UeConsole and AbootDownload GUI can hold ASR COM ports or leave workers. Close them before flashing or call aboot_flash with closeCatstudio=true / closeAbootGui=true.",
        },
    }


def list_release_packages(args):
    root = os.path.abspath(args.get("root") or DEFAULT_SEARCH_ROOT)
    limit = int(args.get("limit") or 20)
    include_source = bool(args.get("includeSource", False))
    results = []
    if not os.path.isdir(root):
        return {"root": root, "exists": False, "packages": []}
    for dirpath, dirnames, filenames in os.walk(root):
        lower_dir = dirpath.lower()
        if any(part in lower_dir for part in [os.sep + ".git", os.sep + ".venv", os.sep + "node_modules"]):
            dirnames[:] = []
            continue
        if not any(key in lower_dir for key in ["out", "release", "upload", "product"]):
            if dirpath != root and len(results) >= limit:
                break
        for filename in filenames:
            lower = filename.lower()
            if not lower.endswith(".zip"):
                continue
            if not include_source and lower.endswith("_source.zip"):
                continue
            full = os.path.join(dirpath, filename)
            try:
                stat = os.stat(full)
            except OSError:
                continue
            results.append(
                {
                    "path": full,
                    "sizeBytes": stat.st_size,
                    "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                }
            )
    results.sort(key=lambda item: item["mtime"], reverse=True)
    return {"root": root, "exists": True, "packages": results[:limit]}


def kill_download_processes(args):
    close_catstudio = bool(args.get("closeCatstudio", False))
    close_aboot_gui = bool(args.get("closeAbootGui", False))
    names = ["adownload"]
    if close_catstudio:
        names.append("CATStudio")
    if close_aboot_gui:
        names.append("aboot")
    killed = []
    for proc in get_processes():
        name = str(proc.get("ProcessName", ""))
        pid = proc.get("Id")
        if name.lower() in [n.lower() for n in names] and pid:
            result = run_process(["powershell", "-NoProfile", "-Command", "Stop-Process -Id %s -Force" % int(pid)], timeout=10)
            killed.append({"processName": name, "pid": pid, "ok": result["ok"], "stderr": result.get("stderr", "")})
    return {"closeCatstudio": close_catstudio, "closeAbootGui": close_aboot_gui, "killed": killed, "remainingProcesses": get_processes()}


def build_flash_command(args, tool, package_path, ports):
    cmd = [tool]
    if ports:
        cmd += ["-p", ",".join(ports)]
    if bool(args.get("autoEnableUsb", True)):
        cmd.append("-a")
    if bool(args.get("usbOnly", False)):
        cmd.append("-u")
    if bool(args.get("atFallback", True)):
        cmd.append("-f")
    cmd += ["-s", str(int(args.get("baud") or 115200))]
    if bool(args.get("production", False)):
        cmd.append("-m")
    if bool(args.get("reboot", True)):
        cmd.append("-r")
    if bool(args.get("quit", True)):
        cmd.append("-q")
    cmd.append(package_path)
    return cmd


def flash(args):
    package_info = validate_package(args.get("releasePackage"))
    if not package_info["exists"]:
        return {"status": "ERROR", "error": "releasePackage does not exist", "releasePackage": package_info}
    if package_info.get("isSourceZip"):
        return {"status": "ERROR", "error": "refusing to flash *_source.zip", "releasePackage": package_info}

    tool = detect_adownload(args.get("adownloadPath"))
    if not os.path.exists(tool):
        return {"status": "ERROR", "error": "adownload.exe not found", "adownloadPath": tool}

    ports = normalize_ports(args.get("ports"))
    cmd = build_flash_command(args, tool, package_info["path"], ports)
    if bool(args.get("dryRun", False)):
        return {"status": "DRY_RUN", "command": cmd, "preflight": status(args)}

    if bool(args.get("killExistingAdownload", True)):
        kill_download_processes({"closeCatstudio": False, "closeAbootGui": False})

    if bool(args.get("closeCatstudio", False)):
        kill_download_processes({"closeCatstudio": True, "closeAbootGui": False})
    if bool(args.get("closeAbootGui", False)):
        kill_download_processes({"closeCatstudio": False, "closeAbootGui": True})

    blockers = []
    for proc in get_processes():
        name = str(proc.get("ProcessName", "")).lower()
        if name == "catstudio" and not bool(args.get("closeCatstudio", False)):
            blockers.append(proc)
        if name == "aboot" and not bool(args.get("closeAbootGui", False)):
            blockers.append(proc)
    if blockers:
        return {
            "status": "BLOCKED",
            "error": "CATStudio or AbootDownload GUI is running and may hold ASR COM ports. Re-run with closeCatstudio=true and/or closeAbootGui=true after saving logs.",
            "processes": blockers,
            "preflight": status(args),
        }

    ensure_log_dir()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(LOG_DIR, "aboot_flash_%s.log" % timestamp)
    timeout_sec = int(args.get("timeoutSec") or 900)
    start = time.time()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        universal_newlines=True,
        creationflags=CREATE_NO_WINDOW,
    )
    timed_out = False
    try:
        output, _ = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        output, _ = proc.communicate()

    elapsed = round(time.time() - start, 2)
    with open(log_path, "w", encoding="utf-8", errors="replace") as handle:
        handle.write("$ " + " ".join(cmd) + "\n")
        handle.write(output or "")

    success = (not timed_out) and proc.returncode == 0 and re.search(r'"?status"?\s*:\s*"?SUCCEEDED"?|SUCCEEDED', output or "", re.I)
    failed = re.search(r'"?status"?\s*:\s*"?FAILED"?|FAILED|ERROR', output or "", re.I)
    tail = (output or "")[-5000:]
    return {
        "status": "SUCCEEDED" if success else ("TIMEOUT" if timed_out else ("FAILED" if failed or proc.returncode else "UNKNOWN")),
        "returncode": proc.returncode,
        "timedOut": timed_out,
        "elapsedSec": elapsed,
        "command": cmd,
        "logPath": log_path,
        "outputTail": tail,
        "postStatus": status(args),
    }


def call_tool(name, args):
    args = args or {}
    if name == "aboot_status":
        return status(args)
    if name == "aboot_list_release_packages":
        return list_release_packages(args)
    if name == "aboot_kill_download_processes":
        return kill_download_processes(args)
    if name == "aboot_flash":
        return flash(args)
    raise ValueError("Unknown tool: %s" % name)


def content_result(payload, is_error=False):
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        ],
        "isError": bool(is_error),
    }


def handle_request(message):
    method = message.get("method")
    params = message.get("params") or {}
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            return content_result(call_tool(name, args))
        except Exception as exc:
            return content_result({"error": str(exc), "traceback": traceback.format_exc()}, is_error=True)
    if method in ("ping", "notifications/initialized"):
        return {}
    if method in ("resources/list", "prompts/list"):
        return {"resources": []} if method == "resources/list" else {"prompts": []}
    return {}


def read_message(stdin):
    headers = {}
    while True:
        line = stdin.readline()
        if not line:
            return None
        line = line.decode("utf-8")
        if line in ("\r\n", "\n"):
            break
        key, _, value = line.partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = stdin.read(length)
    return json.loads(body.decode("utf-8"))


def write_message(stdout, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    stdout.write(("Content-Length: %d\r\n\r\n" % len(body)).encode("ascii"))
    stdout.write(body)
    stdout.flush()


def serve():
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        message = read_message(stdin)
        if message is None:
            break
        if "id" not in message:
            continue
        response = {"jsonrpc": "2.0", "id": message.get("id")}
        try:
            response["result"] = handle_request(message)
        except Exception as exc:
            response["error"] = {"code": -32000, "message": str(exc), "data": traceback.format_exc()}
        write_message(stdout, response)


def self_test():
    print(json.dumps({"server": SERVER_NAME, "tools": [tool["name"] for tool in TOOLS], "status": status({})}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        self_test()
    else:
        serve()
