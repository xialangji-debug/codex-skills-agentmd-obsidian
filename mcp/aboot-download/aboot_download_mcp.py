from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    "aboot-download",
    instructions=(
        "Tools for ASR AbootDownload flashing. Use for locating release packages, "
        "checking AbootDownload/adownload status, listing devices, building safe flashing commands, "
        "and running adownload only with explicit confirmation."
    ),
)

SERVER_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SERVER_DIR / "aboot_download_config.json"
EXAMPLE_CONFIG_PATH = SERVER_DIR / "aboot_download_config.example.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "aboot_root": r"C:\Path\To\aboot-tools-win-x64",
    "run_log_root": str(Path.home() / ".codex" / "aboot-download" / "runs"),
    "default_search_roots": [
        str(Path.home() / ".codex" / "worktrees"),
        str(Path.home() / "Downloads"),
    ],
    "default_baudrate": 115200,
    "default_timeout_sec": 900,
}

REQUIRED_RELEASE_MEMBERS = {"download.json", "firmware.bin", "flasher.img"}
SUPPORTED_BAUDRATES = {115200, 230400, 460800, 921600, 1842000, 3686400}


def _read_config_file() -> dict[str, Any]:
    for path in (CONFIG_PATH, EXAMPLE_CONFIG_PATH):
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    return {}


def _load_config() -> dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(_read_config_file())
    root = Path(os.path.expandvars(os.environ.get("ABOOT_ROOT") or cfg["aboot_root"]))
    cfg["aboot_root"] = str(root)
    cfg["aboot_gui"] = str(root / "aboot.exe")
    cfg["adownload"] = str(root / "adownload.exe")
    cfg["arelease"] = str(root / "arelease.exe")
    cfg["run_log_root"] = os.path.expandvars(os.environ.get("ABOOT_RUN_LOG_ROOT") or cfg["run_log_root"])
    search_roots = os.environ.get("ABOOT_SEARCH_ROOTS")
    if search_roots:
        cfg["default_search_roots"] = [item for item in search_roots.split(os.pathsep) if item]
    else:
        cfg["default_search_roots"] = [os.path.expandvars(str(item)) for item in cfg.get("default_search_roots", [])]
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
    except Exception as exc:  # noqa: BLE001 - tool errors should be visible.
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc), "command": args}


def _powershell(script: str, timeout: int = 20) -> dict[str, Any]:
    return _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], timeout=timeout)


def _parse_json_maybe(text: str) -> Any:
    if not text:
        return []
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        return [{"raw": text}]


def _aboot_processes() -> list[dict[str, Any]]:
    ps = (
        "$p = Get-Process -Name aboot,adownload,arelease,ASRFotaTools -ErrorAction SilentlyContinue | "
        "Select-Object Id,ProcessName,Path,StartTime; "
        "if ($p) { $p | ConvertTo-Json -Compress }"
    )
    out = _powershell(ps, timeout=8)
    return _parse_json_maybe(out.get("stdout", ""))


def _package_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "exists": path.exists(),
        "is_zip": path.suffix.lower() == ".zip",
        "is_source_package": "source" in path.name.lower(),
        "valid_release_package": False,
        "size": 0,
        "modified": "",
        "members_preview": [],
        "required_members_present": [],
        "required_members_missing": sorted(REQUIRED_RELEASE_MEMBERS),
        "download_json": None,
        "error": "",
    }
    if not path.exists():
        info["error"] = "file not found"
        return info
    try:
        stat = path.stat()
        info["size"] = stat.st_size
        info["modified"] = _jsonable_time(stat.st_mtime)
        if path.suffix.lower() != ".zip":
            info["error"] = "not a zip file"
            return info
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            normalized = {Path(name).name for name in names if not name.endswith("/")}
            info["members_preview"] = names[:80]
            present = sorted(REQUIRED_RELEASE_MEMBERS & normalized)
            missing = sorted(REQUIRED_RELEASE_MEMBERS - normalized)
            info["required_members_present"] = present
            info["required_members_missing"] = missing
            info["valid_release_package"] = not missing and not info["is_source_package"]
            download_member = next((name for name in names if Path(name).name == "download.json"), "")
            if download_member:
                try:
                    raw = zf.read(download_member).decode("utf-8", errors="replace")
                    info["download_json"] = json.loads(raw)
                except Exception as exc:  # noqa: BLE001
                    info["download_json"] = {"parse_error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        info["error"] = str(exc)
    return info


def _candidate_roots(extra_roots: list[str] | None = None) -> list[Path]:
    cfg = _load_config()
    roots = [Path(p) for p in cfg.get("default_search_roots", [])]
    for item in extra_roots or []:
        if item:
            roots.append(Path(item))
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve()) if root.exists() else str(root)
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def _find_release_packages(search_roots: list[str] | None = None, limit: int = 30) -> list[dict[str, Any]]:
    packages: list[Path] = []
    for root in _candidate_roots(search_roots):
        if not root.exists():
            continue
        try:
            for path in root.rglob("*.zip"):
                name = path.name.lower()
                if any(token in name for token in ["asr", "tw", "lt", "c10", "craneg", "aboot", "release", "3602"]):
                    packages.append(path)
        except OSError:
            continue
    packages.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    out: list[dict[str, Any]] = []
    for path in packages[:200]:
        info = _package_info(path)
        out.append(
            {
                "path": info["path"],
                "name": info["name"],
                "size": info["size"],
                "modified": info["modified"],
                "valid_release_package": info["valid_release_package"],
                "is_source_package": info["is_source_package"],
                "missing": info["required_members_missing"],
            }
        )
    out.sort(key=lambda item: (item["valid_release_package"], not item["is_source_package"], item["modified"]), reverse=True)
    return out[: max(1, min(limit, 200))]


def _build_adownload_args(
    package_path: str,
    ports: list[str] | None,
    usb_only: bool,
    auto_enable_usb: bool,
    baudrate: int,
    at_fallback: bool,
    reboot_after: bool,
    production_mode: bool,
    dump_enable: bool,
    quit_after: bool,
) -> list[str]:
    cfg = _load_config()
    args = [cfg["adownload"]]
    clean_ports = [p.strip() for p in (ports or []) if p and p.strip()]
    if clean_ports:
        args.extend(["-p", ",".join(clean_ports)])
    if usb_only:
        args.append("-u")
    if auto_enable_usb:
        args.append("-a")
    if at_fallback:
        args.append("-f")
    if reboot_after:
        args.append("-r")
    if production_mode:
        args.append("-m")
    if dump_enable:
        args.append("-d")
    if quit_after:
        args.append("-q")
    args.extend(["-s", str(baudrate), package_path])
    return args


def _safe_run_dir(package_path: Path) -> Path:
    cfg = _load_config()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in package_path.stem)[:80]
    return Path(cfg["run_log_root"]) / f"{stamp}_{safe_name}"


@mcp.tool()
def aboot_status() -> dict[str, Any]:
    """Return AbootDownload/adownload paths, help text, running processes, and recent release-package candidates."""
    cfg = _load_config()
    root = Path(cfg["aboot_root"])
    adownload = Path(cfg["adownload"])
    help_result = _run([str(adownload), "--help"], timeout=10, cwd=str(root)) if adownload.exists() else {"ok": False, "stderr": "adownload not found"}
    return {
        "aboot_root": str(root),
        "aboot_root_exists": root.exists(),
        "aboot_gui": cfg["aboot_gui"],
        "aboot_gui_exists": Path(cfg["aboot_gui"]).exists(),
        "adownload": cfg["adownload"],
        "adownload_exists": adownload.exists(),
        "arelease": cfg["arelease"],
        "arelease_exists": Path(cfg["arelease"]).exists(),
        "processes": _aboot_processes(),
        "help": help_result,
        "recent_packages": _find_release_packages(limit=8),
    }


@mcp.tool()
def list_release_packages(search_roots: list[str] | None = None, limit: int = 30) -> dict[str, Any]:
    """Find likely AbootDownload release .zip packages and mark valid flashing packages."""
    return {"packages": _find_release_packages(search_roots=search_roots, limit=limit)}


@mcp.tool()
def inspect_release_package(package_path: str) -> dict[str, Any]:
    """Inspect a release package zip and verify required AbootDownload members."""
    return _package_info(Path(package_path))


@mcp.tool()
def list_flash_devices(include_pnp: bool = True) -> dict[str, Any]:
    """List serial COM ports and likely ASR/USB/bootrom devices for flashing."""
    serial_ps = (
        "Get-CimInstance Win32_SerialPort | "
        "Select-Object DeviceID,Name,Description,PNPDeviceID | ConvertTo-Json -Compress"
    )
    serial_result = _powershell(serial_ps, timeout=8)
    result: dict[str, Any] = {
        "serial_ports": _parse_json_maybe(serial_result.get("stdout", "")),
        "serial_query": serial_result,
    }
    if include_pnp:
        pnp_ps = (
            "$d = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | "
            "Where-Object { $_.FriendlyName -match 'ASR|Aboot|Arom|Boot|USB|Serial|COM|Modem|MUSB|Android|Diag' } | "
            "Select-Object Class,FriendlyName,InstanceId,Status; "
            "if ($d) { $d | ConvertTo-Json -Compress }"
        )
        pnp_result = _powershell(pnp_ps, timeout=12)
        result["pnp_devices"] = _parse_json_maybe(pnp_result.get("stdout", ""))
        result["pnp_query"] = pnp_result
    return result


@mcp.tool()
def build_flash_command(
    package_path: str,
    ports: list[str] | None = None,
    usb_only: bool = True,
    auto_enable_usb: bool = True,
    baudrate: int = 115200,
    at_fallback: bool = False,
    reboot_after: bool = False,
    production_mode: bool = False,
    dump_enable: bool = False,
    quit_after: bool = True,
) -> dict[str, Any]:
    """Build the adownload.exe command without flashing."""
    baudrate = int(baudrate)
    if baudrate not in SUPPORTED_BAUDRATES:
        return {"ok": False, "error": f"unsupported baudrate: {baudrate}", "supported_baudrates": sorted(SUPPORTED_BAUDRATES)}
    info = _package_info(Path(package_path))
    args = _build_adownload_args(package_path, ports, usb_only, auto_enable_usb, baudrate, at_fallback, reboot_after, production_mode, dump_enable, quit_after)
    return {
        "ok": bool(info["valid_release_package"]),
        "command": args,
        "command_line": subprocess.list2cmdline(args),
        "package": info,
        "will_refuse_to_flash": not info["valid_release_package"],
    }


@mcp.tool()
def flash_release_package(
    package_path: str,
    confirm: bool = False,
    ports: list[str] | None = None,
    usb_only: bool = True,
    auto_enable_usb: bool = True,
    baudrate: int = 115200,
    at_fallback: bool = False,
    reboot_after: bool = False,
    production_mode: bool = False,
    dump_enable: bool = False,
    quit_after: bool = True,
    timeout_sec: int = 900,
) -> dict[str, Any]:
    """Flash a release package with adownload.exe. Refuses unless confirm=true and package is valid."""
    baudrate = int(baudrate)
    if baudrate not in SUPPORTED_BAUDRATES:
        return {"ok": False, "error": f"unsupported baudrate: {baudrate}", "supported_baudrates": sorted(SUPPORTED_BAUDRATES)}
    pkg = Path(package_path)
    info = _package_info(pkg)
    args = _build_adownload_args(str(pkg), ports, usb_only, auto_enable_usb, baudrate, at_fallback, reboot_after, production_mode, dump_enable, quit_after)
    if not confirm:
        return {
            "ok": False,
            "error": "refused: pass confirm=true to flash a device",
            "command": args,
            "command_line": subprocess.list2cmdline(args),
            "package": info,
        }
    if not info["valid_release_package"]:
        return {"ok": False, "error": "refused: package is not a valid non-source Aboot release zip", "package": info}
    run_dir = _safe_run_dir(pkg)
    run_dir.mkdir(parents=True, exist_ok=True)
    copied_package = run_dir / pkg.name
    try:
        shutil.copy2(pkg, copied_package)
    except OSError:
        copied_package = pkg
    args = _build_adownload_args(str(copied_package), ports, usb_only, auto_enable_usb, baudrate, at_fallback, reboot_after, production_mode, dump_enable, quit_after)
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    result = _run(args, timeout=max(30, min(int(timeout_sec), 7200)), cwd=str(Path(_load_config()["aboot_root"])))
    finished = datetime.now().astimezone().isoformat(timespec="seconds")
    run_meta = {
        "started": started,
        "finished": finished,
        "package_source": str(pkg),
        "package_used": str(copied_package),
        "package": info,
        "command": args,
        "result": result,
    }
    (run_dir / "flash_run.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "stdout.txt").write_text(result.get("stdout", ""), encoding="utf-8")
    (run_dir / "stderr.txt").write_text(result.get("stderr", ""), encoding="utf-8")
    return {"ok": result["ok"], "run_dir": str(run_dir), "result": result, "package_used": str(copied_package)}


@mcp.tool()
def open_aboot_gui(package_path: str = "") -> dict[str, Any]:
    """Open the AbootDownload GUI. This does not press Start or flash automatically."""
    cfg = _load_config()
    exe = Path(cfg["aboot_gui"])
    if not exe.exists():
        return {"ok": False, "error": f"aboot.exe not found: {exe}"}
    args = [str(exe)]
    if package_path:
        args.append(package_path)
    try:
        subprocess.Popen(args, cwd=str(exe.parent))
        return {"ok": True, "command": args, "note": "GUI opened; MCP did not press Start."}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "command": args}


if __name__ == "__main__":
    mcp.run()
