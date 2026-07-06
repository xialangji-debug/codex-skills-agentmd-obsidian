from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    "catstudio-device",
    instructions=(
        "Tools for ASR CATStudio logs and local test device control. "
        "Use to find/copy/export CATStudio .icl/.ild logs, inspect local ADB/serial devices, "
        "and reboot a connected device through explicit ADB or serial commands."
    ),
)

SERVER_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SERVER_DIR / "catstudio_device_config.json"
EXAMPLE_CONFIG_PATH = SERVER_DIR / "catstudio_device_config.example.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "catstudio_root": r"C:\Path\To\CATStudio_V3_1_4_89",
    "snapshot_root": str(Path.home() / ".codex" / "catstudio-device" / "captures"),
    "extractor_script": str(Path.home() / ".codex" / "skills" / "catstudio-log-extractor" / "scripts" / "extract_catstudio_logs.py"),
    "serial_reboot_command": "AT+CFUN=1,1",
    "serial_baudrate": 115200,
}


def _read_config_file() -> dict[str, Any]:
    for path in (CONFIG_PATH, EXAMPLE_CONFIG_PATH):
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    return {}


def _load_config() -> dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(_read_config_file())
    root = Path(os.path.expandvars(os.environ.get("CATSTUDIO_ROOT") or cfg["catstudio_root"]))
    cfg["catstudio_root"] = str(root)
    cfg["snapshot_root"] = os.path.expandvars(os.environ.get("CATSTUDIO_SNAPSHOT_ROOT") or cfg["snapshot_root"])
    cfg["extractor_script"] = os.path.expandvars(os.environ.get("CATSTUDIO_EXTRACTOR_SCRIPT") or cfg["extractor_script"])
    cfg["exec_dir"] = str(root / "Exec")
    cfg["log_dir"] = str(root / "Exec" / "Bin Logs")
    cfg["debug_log_dir"] = str(root / "Exec" / "DebugLog")
    cfg["adb_path"] = str(root / "Exec" / "ADB" / "adb.exe")
    return cfg


def _jsonable_time(ts: float | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")


def _run(args: list[str], timeout: int = 20, cwd: str | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "command": args,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": f"timeout after {timeout}s",
            "command": args,
        }
    except Exception as exc:  # noqa: BLE001 - expose tool failure to caller.
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc), "command": args}


def _powershell(script: str, timeout: int = 20) -> dict[str, Any]:
    return _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], timeout=timeout)


def _catstudio_processes() -> list[dict[str, Any]]:
    ps = (
        "$p = Get-Process -Name CATStudio,bcat,DiagRecord,SuRecord -ErrorAction SilentlyContinue | "
        "Select-Object Id,ProcessName,Path,StartTime; "
        "if ($p) { $p | ConvertTo-Json -Compress }"
    )
    out = _powershell(ps, timeout=10)
    if not out["ok"] or not out["stdout"]:
        return []
    try:
        parsed = json.loads(out["stdout"])
        if isinstance(parsed, dict):
            parsed = [parsed]
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return [{"raw": out["stdout"]}]


def _log_pairs(limit: int = 20, min_icl_size: int = 0) -> list[dict[str, Any]]:
    cfg = _load_config()
    log_dir = Path(cfg["log_dir"])
    if not log_dir.exists():
        return []
    now = time.time()
    pairs: list[dict[str, Any]] = []
    for icl in log_dir.glob("*.icl"):
        try:
            stat = icl.stat()
        except OSError:
            continue
        if stat.st_size < min_icl_size:
            continue
        ild = icl.with_suffix(".ild")
        ild_stat = None
        if ild.exists():
            try:
                ild_stat = ild.stat()
            except OSError:
                ild_stat = None
        pairs.append(
            {
                "stem": icl.stem,
                "icl_path": str(icl),
                "ild_path": str(ild) if ild.exists() else "",
                "icl_size": stat.st_size,
                "ild_size": ild_stat.st_size if ild_stat else 0,
                "modified": _jsonable_time(stat.st_mtime),
                "modified_epoch": stat.st_mtime,
                "active_guess": (now - stat.st_mtime) < 180,
            }
        )
    pairs.sort(key=lambda item: item["modified_epoch"], reverse=True)
    for item in pairs:
        item.pop("modified_epoch", None)
    return pairs[: max(1, min(limit, 200))]


def _latest_debug_dir() -> dict[str, Any] | None:
    cfg = _load_config()
    debug_dir = Path(cfg["debug_log_dir"])
    if not debug_dir.exists():
        return None
    dirs = [p for p in debug_dir.iterdir() if p.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    p = dirs[0]
    return {"path": str(p), "modified": _jsonable_time(p.stat().st_mtime)}


def _default_capture_dir(prefix: str = "capture") -> Path:
    cfg = _load_config()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = Path(cfg["snapshot_root"])
    return root / f"{stamp}_{prefix}"


def _copy_log_pair(pair: dict[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, Any]] = []
    for key in ("icl_path", "ild_path"):
        src_text = pair.get(key) or ""
        if not src_text:
            continue
        src = Path(src_text)
        if not src.exists():
            continue
        dst = output_dir / src.name
        shutil.copy2(src, dst)
        copied.append({"source": str(src), "path": str(dst), "size": dst.stat().st_size})
    return copied


def _run_extractor(log_path: str, output_dir: Path, profile: str, keywords: list[str]) -> dict[str, Any]:
    cfg = _load_config()
    extractor = Path(cfg["extractor_script"])
    if not extractor.exists():
        return {"ok": False, "error": f"extractor not found: {extractor}"}
    args = ["python", str(extractor), log_path, "--output-dir", str(output_dir)]
    if profile == "none":
        return {"ok": True, "skipped": True}
    if profile == "fast-evidence":
        args.append("--fast-evidence")
    elif profile == "evidence-pack":
        args.append("--evidence-pack")
    else:
        for name in [p.strip() for p in profile.split(",") if p.strip()]:
            args.extend(["--profile", name])
        args.append("--summary")
    for keyword in keywords:
        args.extend(["--keyword", keyword])
    result = _run(args, timeout=180)
    files = []
    if output_dir.exists():
        files = [
            {"path": str(p), "size": p.stat().st_size, "modified": _jsonable_time(p.stat().st_mtime)}
            for p in sorted(output_dir.glob("*"), key=lambda x: x.name)
            if p.is_file()
        ]
    return {"ok": result["ok"], "stdout": result["stdout"], "stderr": result["stderr"], "files": files}


@mcp.tool()
def catstudio_status() -> dict[str, Any]:
    """Return CATStudio paths, process status, latest log pair, latest debug directory, and local device hints."""
    cfg = _load_config()
    root = Path(cfg["catstudio_root"])
    latest = _log_pairs(limit=1)
    return {
        "catstudio_root": str(root),
        "catstudio_exists": root.exists(),
        "exec_dir": cfg["exec_dir"],
        "log_dir": cfg["log_dir"],
        "log_dir_exists": Path(cfg["log_dir"]).exists(),
        "debug_log_dir": cfg["debug_log_dir"],
        "processes": _catstudio_processes(),
        "latest_log": latest[0] if latest else None,
        "latest_debug_dir": _latest_debug_dir(),
        "adb_path": cfg["adb_path"],
        "snapshot_root": cfg["snapshot_root"],
    }


@mcp.tool()
def list_catstudio_logs(limit: int = 10, min_icl_size: int = 0) -> dict[str, Any]:
    """List recent CATStudio Bin Logs .icl/.ild pairs sorted by modified time."""
    return {"logs": _log_pairs(limit=limit, min_icl_size=min_icl_size)}


@mcp.tool()
def grab_latest_catstudio_log(
    wait_seconds: int = 0,
    min_icl_size: int = 1024,
    output_dir: str = "",
    export_profile: str = "fast-evidence",
    keywords: list[str] | None = None,
    include_debug_dir: bool = False,
) -> dict[str, Any]:
    """Copy the latest CATStudio .icl/.ild pair and optionally export AI-friendly evidence files."""
    wait_seconds = max(0, min(int(wait_seconds), 3600))
    if wait_seconds:
        time.sleep(wait_seconds)
    logs = _log_pairs(limit=1, min_icl_size=min_icl_size)
    if not logs:
        return {"ok": False, "error": "no CATStudio .icl log found", "status": catstudio_status()}
    pair = logs[0]
    dest = Path(output_dir) if output_dir else _default_capture_dir("catstudio_log")
    copied = _copy_log_pair(pair, dest)
    metadata = {
        "captured_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source_pair": pair,
        "copied": copied,
    }
    debug_copy = None
    if include_debug_dir:
        latest_debug = _latest_debug_dir()
        if latest_debug:
            src = Path(latest_debug["path"])
            debug_dest = dest / "DebugLog" / src.name
            if debug_dest.exists():
                shutil.rmtree(debug_dest)
            shutil.copytree(src, debug_dest)
            debug_copy = {"source": str(src), "path": str(debug_dest)}
            metadata["debug_copy"] = debug_copy
    meta_path = dest / "capture.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    copied_icl = next((item["path"] for item in copied if item["path"].lower().endswith(".icl")), "")
    export = {"ok": True, "skipped": True}
    if copied_icl and export_profile != "none":
        export_dir = dest / "evidence"
        export = _run_extractor(copied_icl, export_dir, export_profile, keywords or [])
    return {
        "ok": True,
        "output_dir": str(dest),
        "metadata": str(meta_path),
        "copied": copied,
        "debug_copy": debug_copy,
        "export": export,
    }


@mcp.tool()
def export_catstudio_log(
    log_path: str,
    output_dir: str = "",
    profile: str = "fast-evidence",
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Export an existing CATStudio .icl log to TSV/evidence using the local catstudio-log-extractor skill."""
    src = Path(log_path)
    if not src.exists():
        return {"ok": False, "error": f"log not found: {src}"}
    dest = Path(output_dir) if output_dir else _default_capture_dir("exported_evidence")
    dest.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "output_dir": str(dest), "export": _run_extractor(str(src), dest, profile, keywords or [])}


@mcp.tool()
def list_connected_devices(include_pnp: bool = False) -> dict[str, Any]:
    """List local ADB devices and serial COM ports; optionally include slower USB/PnP diagnostic scan."""
    cfg = _load_config()
    adb_path = Path(cfg["adb_path"])
    adb_result = _run([str(adb_path), "devices", "-l"], timeout=8) if adb_path.exists() else {"ok": False, "stderr": "adb not found"}
    serial_ps = (
        "Get-CimInstance Win32_SerialPort | "
        "Select-Object DeviceID,Name,Description,PNPDeviceID | ConvertTo-Json -Compress"
    )
    serial_result = _powershell(serial_ps, timeout=8)
    def parse_json(text: str) -> Any:
        if not text:
            return []
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            return [{"raw": text}]
    result = {
        "adb": adb_result,
        "serial_ports": parse_json(serial_result.get("stdout", "")),
        "serial_query": serial_result,
    }
    if include_pnp:
        pnp_ps = (
            "$d = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | "
            "Where-Object { $_.FriendlyName -match 'ASR|Diag|ADB|Android|USB|Serial|COM|Modem|MDiag|MUSB' } | "
            "Select-Object Class,FriendlyName,InstanceId,Status; "
            "if ($d) { $d | ConvertTo-Json -Compress }"
        )
        pnp_result = _powershell(pnp_ps, timeout=12)
        result["pnp_devices"] = parse_json(pnp_result.get("stdout", ""))
        result["pnp_query"] = pnp_result
    return result


@mcp.tool()
def reboot_device(
    method: str = "adb",
    confirm: bool = False,
    serial_port: str = "",
    serial_command: str = "",
    baudrate: int = 0,
    wait_after_seconds: int = 5,
) -> dict[str, Any]:
    """Reboot a connected device via adb or serial AT command. Requires confirm=true."""
    if not confirm:
        return {
            "ok": False,
            "error": "refused: pass confirm=true to reboot a device",
            "supported_methods": ["adb", "serial_at"],
        }
    cfg = _load_config()
    wait_after_seconds = max(0, min(int(wait_after_seconds), 120))
    method = method.lower().strip()
    if method == "adb":
        adb_path = Path(cfg["adb_path"])
        if not adb_path.exists():
            return {"ok": False, "error": f"adb not found: {adb_path}"}
        result = _run([str(adb_path), "reboot"], timeout=20)
        if wait_after_seconds:
            time.sleep(wait_after_seconds)
        return {"ok": result["ok"], "method": "adb", "result": result}
    if method == "serial_at":
        if not serial_port:
            return {"ok": False, "error": "serial_port is required for serial_at"}
        command = serial_command or cfg.get("serial_reboot_command") or "AT+CFUN=1,1"
        baud = int(baudrate or cfg.get("serial_baudrate") or 115200)
        serial_payload = json.dumps({"port": serial_port, "baud": baud, "command": command}, ensure_ascii=False)
        ps = f"""
$ErrorActionPreference = 'Stop'
$cfg = ConvertFrom-Json @'
{serial_payload}
'@
$port = New-Object System.IO.Ports.SerialPort($cfg.port, [int]$cfg.baud, 'None', 8, 'One')
$port.NewLine = "`r`n"
$port.ReadTimeout = 1200
$port.WriteTimeout = 1200
$port.Open()
$port.WriteLine($cfg.command)
Start-Sleep -Milliseconds 500
$resp = ''
try {{ $resp = $port.ReadExisting() }} catch {{ }}
$port.Close()
@{{ port=$cfg.port; baud=[int]$cfg.baud; command=$cfg.command; response=$resp }} | ConvertTo-Json -Compress
"""
        result = _powershell(ps, timeout=15)
        if wait_after_seconds:
            time.sleep(wait_after_seconds)
        parsed = None
        if result["stdout"]:
            try:
                parsed = json.loads(result["stdout"])
            except json.JSONDecodeError:
                parsed = {"raw": result["stdout"]}
        return {"ok": result["ok"], "method": "serial_at", "result": result, "parsed": parsed}
    return {"ok": False, "error": f"unsupported reboot method: {method}", "supported_methods": ["adb", "serial_at"]}


if __name__ == "__main__":
    mcp.run()
