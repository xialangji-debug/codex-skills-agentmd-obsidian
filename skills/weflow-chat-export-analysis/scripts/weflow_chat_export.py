#!/usr/bin/env python3
"""Export local WeFlow chats through WeFlow's own worker and derive analysis files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from collections import Counter
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any


SCRIPT_VERSION = "0.1.0"


def eprint(message: str) -> None:
    print(message, file=sys.stderr)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def safe_filename(value: str, fallback: str = "chat") -> str:
    value = str(value or "").strip() or fallback
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:96] or fallback


def clean_wxid(raw: str) -> str:
    raw = str(raw or "").strip()
    if raw.lower().startswith("wxid_"):
        m = re.match(r"^(wxid_[^_]+)", raw, flags=re.I)
        return m.group(1) if m else raw
    m = re.match(r"^(.+)_([A-Za-z0-9]{4})$", raw)
    return m.group(1) if m else raw


def default_paths() -> dict[str, Path]:
    home = Path.home()
    appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    localapp = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    user_data = appdata / "weflow"
    install_dir = localapp / "Programs" / "WeFlow"
    return {
        "home": home,
        "appdata": appdata,
        "localapp": localapp,
        "user_data": user_data,
        "config": user_data / "WeFlow-config.json",
        "local_state": user_data / "Local State",
        "install_dir": install_dir,
        "resources": install_dir / "resources" / "resources",
        "app_asar": install_dir / "resources" / "app.asar",
        "cache_app_src": localapp / "Codex" / "weflow-chat-export-analysis" / "app-asar-src",
        "legacy_app_src": home / "Documents" / "WeFlow-Export-Agent合成反应堆" / "app-asar-src",
        "exports_root": home / "Documents" / "WeFlow-Exports",
        "emoji_cache": home / "Documents" / "WeFlow" / "Emojis",
    }


def ps_single_quote(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def decrypt_weflow_secrets(config_path: Path, local_state_path: Path) -> dict[str, str]:
    exe = shutil.which("pwsh") or shutil.which("powershell")
    if not exe:
        raise RuntimeError("未找到 PowerShell，无法用 Windows DPAPI 解密 WeFlow safe 字段")

    script = f"""
$ErrorActionPreference = 'Stop'
$WarningPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Security
$ConfigPath = {ps_single_quote(config_path)}
$LocalStatePath = {ps_single_quote(local_state_path)}
$cfg = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$state = Get-Content -LiteralPath $LocalStatePath -Raw | ConvertFrom-Json
$encryptedKeyB64 = [string]$state.os_crypt.encrypted_key
if (-not $encryptedKeyB64) {{ throw 'Local State missing os_crypt.encrypted_key' }}
[byte[]]$encryptedKey = [Convert]::FromBase64String($encryptedKeyB64)
if ($encryptedKey.Length -gt 5) {{
  $prefix = [Text.Encoding]::ASCII.GetString($encryptedKey[0..4])
  if ($prefix -eq 'DPAPI') {{
    $encryptedKey = $encryptedKey[5..($encryptedKey.Length - 1)]
  }}
}}
$masterKey = [Security.Cryptography.ProtectedData]::Unprotect($encryptedKey, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)

function Read-Prop($obj, [string]$name) {{
  if ($null -eq $obj) {{ return '' }}
  $prop = $obj.PSObject.Properties[$name]
  if ($null -eq $prop -or $null -eq $prop.Value) {{ return '' }}
  return [string]$prop.Value
}}

function Get-ConfigValue([string]$name) {{
  $v = Read-Prop $cfg $name
  if ($v) {{ return $v }}
  $myWxid = Read-Prop $cfg 'myWxid'
  if ($myWxid -and $cfg.wxidConfigs) {{
    $entry = $cfg.wxidConfigs.PSObject.Properties[$myWxid]
    if ($entry) {{
      $vv = Read-Prop $entry.Value $name
      if ($vv) {{ return $vv }}
    }}
  }}
  return ''
}}

function Decrypt-Safe([string]$value) {{
  if (-not $value) {{ return '' }}
  if (-not $value.StartsWith('safe:')) {{ return $value }}
  [byte[]]$raw = [Convert]::FromBase64String($value.Substring(5))
  if ($raw.Length -lt 31) {{ throw 'safe payload too short' }}
  $version = [Text.Encoding]::ASCII.GetString($raw[0..2])
  if ($version -ne 'v10') {{ throw "unsupported safe payload version: $version" }}
  [byte[]]$nonce = $raw[3..14]
  $cipherLen = $raw.Length - 15 - 16
  if ($cipherLen -lt 0) {{ throw 'invalid safe payload length' }}
  [byte[]]$cipher = New-Object byte[] $cipherLen
  if ($cipherLen -gt 0) {{ [Array]::Copy($raw, 15, $cipher, 0, $cipherLen) }}
  [byte[]]$tag = New-Object byte[] 16
  [Array]::Copy($raw, 15 + $cipherLen, $tag, 0, 16)
  [byte[]]$plain = New-Object byte[] $cipherLen
  $aes = [Security.Cryptography.AesGcm]::new($masterKey, 16)
  try {{
    $aes.Decrypt($nonce, $cipher, $tag, $plain, $null)
  }} finally {{
    $aes.Dispose()
  }}
  return [Text.Encoding]::UTF8.GetString($plain)
}}

$out = [ordered]@{{
  decryptKey = Decrypt-Safe (Get-ConfigValue 'decryptKey')
  imageXorKey = Decrypt-Safe (Get-ConfigValue 'imageXorKey')
  imageAesKey = Decrypt-Safe (Get-ConfigValue 'imageAesKey')
}}
$out | ConvertTo-Json -Compress
"""
    with tempfile.TemporaryDirectory(prefix="weflow-dpapi-") as td:
        ps1 = Path(td) / "decrypt-weflow-safe.ps1"
        ps1.write_text(script, encoding="utf-8")
        proc = subprocess.run(
            [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=60,
        )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"WeFlow secret 解密失败：{err}")
    stdout = (proc.stdout or "").strip()
    json_start = stdout.find("{")
    json_end = stdout.rfind("}")
    if json_start >= 0 and json_end > json_start:
        stdout = stdout[json_start : json_end + 1]
    try:
        secrets = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "WeFlow secret 解密输出不是 JSON"
            f" (stdout_len={len(proc.stdout or '')}, json_len={len(stdout)}, pos={exc.pos}, msg={exc.msg})"
        ) from exc
    missing = [k for k in ("decryptKey", "imageXorKey", "imageAesKey") if not secrets.get(k)]
    if missing:
        raise RuntimeError("WeFlow 配置缺少必要字段：" + ", ".join(missing))
    return {k: str(secrets[k]) for k in ("decryptKey", "imageXorKey", "imageAesKey")}


def has_export_worker(app_src: Path) -> bool:
    return (app_src / "dist-electron" / "exportWorker.js").is_file()


def safe_rmtree(path: Path, allowed_root: Path) -> None:
    path = path.resolve()
    allowed_root = allowed_root.resolve()
    if path == allowed_root or allowed_root not in path.parents:
        raise RuntimeError(f"拒绝删除非缓存目录：{path}")
    shutil.rmtree(path, ignore_errors=True)


def validate_clean_output_path(path: Path, paths: dict[str, Path]) -> None:
    resolved = path.resolve(strict=False)
    forbidden = {
        Path(resolved.anchor).resolve(strict=False),
        paths["home"].resolve(strict=False),
        (paths["home"] / "Documents").resolve(strict=False),
        paths["exports_root"].resolve(strict=False),
        paths["localapp"].resolve(strict=False),
        paths["appdata"].resolve(strict=False),
    }
    if resolved in forbidden or len(resolved.parts) < 4:
        raise RuntimeError(f"拒绝清空过大的输出目录：{resolved}")


def resolve_app_src(args: argparse.Namespace, paths: dict[str, Path]) -> Path:
    if args.app_src:
        app_src = Path(args.app_src)
        if not has_export_worker(app_src):
            raise RuntimeError(f"--app-src 中没有 dist-electron\\exportWorker.js：{app_src}")
        return app_src

    cache = paths["cache_app_src"]
    if args.refresh_app_src and cache.exists():
        safe_rmtree(cache, paths["localapp"] / "Codex" / "weflow-chat-export-analysis")

    candidates = [cache, paths["legacy_app_src"]]
    for candidate in candidates:
        if has_export_worker(candidate):
            return candidate

    app_asar = paths["app_asar"]
    if not app_asar.is_file():
        raise RuntimeError(f"未找到 WeFlow app.asar：{app_asar}")
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("未找到 npx，无法自动解包 WeFlow app.asar；可手动传 --app-src")
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        safe_rmtree(cache, paths["localapp"] / "Codex" / "weflow-chat-export-analysis")
    cmd = [npx, "--yes", "@electron/asar", "extract", str(app_asar), str(cache)]
    proc = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError("解包 app.asar 失败：" + (proc.stderr or proc.stdout or "").strip())
    if not has_export_worker(cache):
        raise RuntimeError(f"解包完成但仍找不到 exportWorker.js：{cache}")
    return cache


def parse_bound(value: str | None, end: bool = False) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            if fmt == "%Y-%m-%d":
                return datetime.combine(parsed.date(), dt_time.max if end else dt_time.min)
            return parsed
        except ValueError:
            pass
    raise ValueError(f"无法解析时间：{value}")


def parse_message_time(message: dict[str, Any]) -> datetime | None:
    formatted = str(message.get("formattedTime") or "").strip()
    if formatted:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(formatted, fmt)
            except ValueError:
                pass
    return None


def build_contact_map(config: Any) -> dict[str, str]:
    mapping: dict[str, str] = {}

    def choose(obj: dict[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def add_from_obj(obj: dict[str, Any]) -> None:
        username = choose(obj, ("username", "userName", "wxid", "id"))
        display = choose(obj, ("remark", "displayName", "nickname", "name", "alias"))
        if username and display and display != username and not display.startswith("safe:"):
            mapping.setdefault(username, display)

    def walk(value: Any, depth: int = 0) -> None:
        if depth > 8:
            return
        if isinstance(value, dict):
            add_from_obj(value)
            for child in value.values():
                walk(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                walk(child, depth + 1)

    walk(config)
    return mapping


def content_clean(message: dict[str, Any]) -> str:
    content = str(message.get("content") or "")
    local_type = int(message.get("localType") or 0) if str(message.get("localType") or "").isdigit() else message.get("localType")
    msg_type = str(message.get("type") or "")
    if local_type == 3 or "图片" in msg_type:
        return "[图片]"
    return content.replace("\r\n", "\n").replace("\r", "\n").strip()


def resolve_image_path(session_dir: Path, message: dict[str, Any]) -> Path | None:
    content = str(message.get("content") or "").strip()
    if not content:
        return None
    if not ("media" in content.lower() or re.search(r"\.(png|jpe?g|gif|webp|bmp)$", content, flags=re.I)):
        return None
    p = Path(content)
    if not p.is_absolute():
        p = session_dir / content.replace("\\", os.sep)
    return p if p.is_file() else None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_messages(
    raw_json: Path,
    contact_map: dict[str, str],
    my_wxid_clean: str,
    chat_name: str | None,
    since_dt: datetime | None,
    until_dt: datetime | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = load_json(raw_json)
    session = data.get("session") or {}
    messages = list(data.get("messages") or [])
    session_dir = raw_json.parent
    normalized: list[dict[str, Any]] = []
    for index, message in enumerate(messages, start=1):
        if not isinstance(message, dict):
            continue
        msg_dt = parse_message_time(message)
        if since_dt and msg_dt and msg_dt < since_dt:
            continue
        if until_dt and msg_dt and msg_dt > until_dt:
            continue
        row = dict(message)
        row["index"] = index
        sender = str(row.get("senderUsername") or "").strip()
        display = str(row.get("senderDisplayName") or "").strip()
        if int(row.get("isSend") or 0) == 1:
            resolved = "我"
        elif sender == session.get("wxid") and (chat_name or session.get("displayName")):
            resolved = chat_name or session.get("displayName")
        else:
            resolved = contact_map.get(sender) or (display if display and display != sender else sender)
        row["senderResolvedName"] = resolved
        clean = content_clean(row)
        row["contentClean"] = clean
        image_path = resolve_image_path(session_dir, row)
        row["imageExists"] = bool(image_path)
        row["imageFullPath"] = str(image_path) if image_path else ""
        if image_path:
            row["imageRelativePath"] = str(image_path.relative_to(session_dir)).replace("\\", "/")
        else:
            row["imageRelativePath"] = ""
        normalized.append(row)
    return session, normalized


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "index",
        "formattedTime",
        "type",
        "localType",
        "senderResolvedName",
        "senderUsername",
        "isSend",
        "contentClean",
        "imageExists",
        "imageFullPath",
        "platformMessageId",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def md_escape_text(value: str) -> str:
    return value.replace("\n", "\n  ")


def write_markdown(path: Path, session: dict[str, Any], rows: list[dict[str, Any]], chat_name: str | None) -> None:
    title = chat_name or session.get("displayName") or session.get("nickname") or session.get("wxid") or "WeFlow Chat"
    lines = [
        f"# {title} 聊天记录",
        "",
        f"- 会话：{session.get('wxid', '')}",
        f"- 消息数：{len(rows)}",
        "",
        "## 时间线",
        "",
    ]
    for row in rows:
        idx = int(row.get("index") or 0)
        sender = row.get("senderResolvedName") or row.get("senderUsername") or ""
        formatted = row.get("formattedTime") or ""
        msg_type = row.get("type") or row.get("localType") or ""
        lines.append(f"### {idx:03d}｜{formatted}｜{sender}｜{msg_type}")
        if row.get("imageExists") and row.get("imageRelativePath"):
            rel = str(row["imageRelativePath"]).replace("\\", "/")
            lines.append(f"![{Path(rel).name}]({rel})")
        clean = str(row.get("contentClean") or "").strip()
        if clean and clean != "[图片]":
            lines.append(md_escape_text(clean))
        elif clean == "[图片]":
            lines.append("[图片]")
        if row.get("quotedContent"):
            lines.append("")
            lines.append("> 引用：" + str(row.get("quotedContent")).replace("\n", " "))
        lines.append("")
    write_text(path, "\n".join(lines).rstrip() + "\n")


def write_images_index(path: Path, rows: list[dict[str, Any]], session_dir: Path) -> list[str]:
    image_rows = [row for row in rows if row.get("imageExists") and row.get("imageFullPath")]
    lines = ["# 图片索引", "", f"- 图片数：{len(image_rows)}", ""]
    image_files: list[str] = []
    for row in image_rows:
        image_path = Path(str(row["imageFullPath"]))
        rel = str(image_path.relative_to(session_dir)).replace("\\", "/")
        image_files.append(str(image_path))
        size = image_path.stat().st_size if image_path.is_file() else 0
        digest = sha256_file(image_path) if image_path.is_file() else ""
        lines.extend(
            [
                f"## 消息 {int(row.get('index') or 0):03d}｜{row.get('formattedTime', '')}｜{row.get('senderResolvedName', '')}",
                f"![{image_path.name}]({rel})",
                f"- 文件：`{image_path.name}`",
                f"- 大小：{size} bytes",
                f"- SHA256：`{digest}`",
                "",
            ]
        )
    write_text(path, "\n".join(lines).rstrip() + "\n")
    return image_files


def extract_urls(rows: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for url in re.findall(r"https?://[^\s<>\]）)\"']+", str(row.get("content") or "")):
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def write_analysis_brief(
    path: Path,
    session: dict[str, Any],
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    chat_name: str | None,
) -> None:
    title = chat_name or session.get("displayName") or session.get("nickname") or session.get("wxid") or "WeFlow Chat"
    sender_counts = Counter(str(row.get("senderResolvedName") or row.get("senderUsername") or "") for row in rows)
    type_counts = Counter(str(row.get("type") or row.get("localType") or "") for row in rows)
    urls = extract_urls(rows)
    file_mentions = [str(row.get("contentClean") or "") for row in rows if "文件" in str(row.get("type") or "") or str(row.get("contentClean") or "").startswith("[文件]")]
    lines = [
        f"# {title} 快速分析材料",
        "",
        "## 范围",
        "",
        f"- 会话：{session.get('wxid', '')}",
        f"- 消息数：{manifest.get('messageCount', 0)}",
        f"- 图片数：{manifest.get('imageCount', 0)}",
        f"- 时间范围：{manifest.get('timeRange', ['',''])[0]} 到 {manifest.get('timeRange', ['',''])[-1]}",
        "",
        "## 主要发言人",
        "",
    ]
    for sender, count in sender_counts.most_common(12):
        lines.append(f"- {sender or '(未知)'}：{count}")
    lines.extend(["", "## 消息类型", ""])
    for msg_type, count in type_counts.most_common():
        lines.append(f"- {msg_type or '(未知)'}：{count}")
    if urls:
        lines.extend(["", "## 链接", ""])
        for url in urls[:30]:
            lines.append(f"- {url}")
    if file_mentions:
        lines.extend(["", "## 文件消息", ""])
        for item in file_mentions[:30]:
            lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## 建议给 Codex 的下一步",
            "",
            "- 先读 `messages-full.md` 获取完整上下文。",
            "- 再读 `images-index.md` 并查看关键图片。",
            "- 最后按用户问题输出主题归纳、争议点、结论和可操作事项。",
            "",
        ]
    )
    write_text(path, "\n".join(lines).rstrip() + "\n")


def postprocess_exports(
    worker_result: Path,
    config: Any,
    my_wxid_clean: str,
    chat_name: str | None,
    derived_format: str,
    analyze: bool,
    since_dt: datetime | None,
    until_dt: datetime | None,
) -> list[dict[str, Any]]:
    result = load_json(worker_result)
    session_outputs = result.get("sessionOutputPaths") or {}
    if not isinstance(session_outputs, dict) or not session_outputs:
        raise RuntimeError("worker-result.json 中没有 sessionOutputPaths")
    contact_map = build_contact_map(config)
    manifests: list[dict[str, Any]] = []
    for _session_id, raw_path_str in session_outputs.items():
        raw_json = Path(str(raw_path_str))
        if not raw_json.is_file():
            raise RuntimeError(f"导出的原始 JSON 不存在：{raw_json}")
        session, rows = normalize_messages(raw_json, contact_map, my_wxid_clean, chat_name, since_dt, until_dt)
        session_dir = raw_json.parent
        derived_files: list[str] = []
        if derived_format in ("all", "jsonl"):
            out = session_dir / "messages-full.jsonl"
            write_jsonl(out, rows)
            derived_files.append(str(out))
        if derived_format in ("all", "csv"):
            out = session_dir / "messages-full.csv"
            write_csv(out, rows)
            derived_files.append(str(out))
        if derived_format in ("all", "markdown", "md"):
            out = session_dir / "messages-full.md"
            write_markdown(out, session, rows, chat_name)
            derived_files.append(str(out))
        images_index = session_dir / "images-index.md"
        image_files = write_images_index(images_index, rows, session_dir)
        derived_files.append(str(images_index))
        time_values = [str(row.get("formattedTime") or "") for row in rows if row.get("formattedTime")]
        manifest = {
            "sourceJson": str(raw_json),
            "outputDir": str(session_dir),
            "session": session,
            "scriptVersion": SCRIPT_VERSION,
            "messageCount": len(rows),
            "imageCount": len(image_files),
            "typeCounts": dict(Counter(str(row.get("localType") or row.get("type") or "") for row in rows)),
            "senderCounts": dict(Counter(str(row.get("senderResolvedName") or row.get("senderUsername") or "") for row in rows)),
            "timeRange": [time_values[0], time_values[-1]] if time_values else ["", ""],
            "filters": {
                "since": since_dt.isoformat(sep=" ") if since_dt else "",
                "until": until_dt.isoformat(sep=" ") if until_dt else "",
            },
            "derivedFiles": derived_files,
            "imageFiles": image_files,
        }
        manifest_path = session_dir / "manifest-full.json"
        manifest["manifestPath"] = str(manifest_path)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        derived_files.append(str(manifest_path))
        if analyze:
            brief = session_dir / "analysis-brief.md"
            write_analysis_brief(brief, session, rows, manifest, chat_name)
            derived_files.append(str(brief))
            manifest["derivedFiles"] = derived_files
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        manifests.append(manifest)
    return manifests


def build_node_runner() -> str:
    return r"""
const { Worker } = require("worker_threads");
const fs = require("fs");
const path = require("path");

const cfg = JSON.parse(process.env.WEFLOW_EXPORT_CONFIG_JSON || "{}");

function requireEnv(name) {
  const value = String(process.env[name] || "").trim();
  if (!value) throw new Error(`Missing env ${name}`);
  return value;
}

if (cfg.cleanOutput === true) {
  fs.rmSync(cfg.outputDir, { recursive: true, force: true });
}
fs.mkdirSync(cfg.outputDir, { recursive: true });

const workerData = {
  sessionIds: cfg.sessionIds,
  outputDir: cfg.outputDir,
  options: cfg.options,
  taskId: cfg.taskId || `codex-${Date.now()}`,
  dbPath: cfg.dbPath,
  decryptKey: requireEnv("WEFLOW_DECRYPT_KEY"),
  myWxid: cfg.myWxid,
  accountDir: cfg.accountDir,
  imageXorKey: requireEnv("WEFLOW_IMAGE_XOR_KEY"),
  imageAesKey: requireEnv("WEFLOW_IMAGE_AES_KEY"),
  resourcesPath: cfg.resourcesPath,
  userDataPath: cfg.userDataPath,
  cachePath: cfg.cachePath || "",
  emojiCacheDir: cfg.emojiCacheDir,
  logEnabled: false,
  isPackaged: true,
};

const createdFiles = [];
const createdDirs = [];
let finished = false;
let lastProgressAt = 0;
let worker;

function finish(code) {
  if (finished) return;
  finished = true;
  const exitNow = () => process.exit(code);
  if (worker) {
    worker.terminate().then(exitNow, exitNow);
  } else {
    exitNow();
  }
}

function writeResult(data) {
  const result = {
    ...data,
    createdFiles,
    createdDirs,
    outputDir: cfg.outputDir,
    finishedAt: new Date().toISOString(),
  };
  fs.writeFileSync(path.join(cfg.outputDir, "worker-result.json"), JSON.stringify(result, null, 2), "utf8");
  console.log(JSON.stringify({
    success: result.success,
    successCount: result.successCount,
    failCount: result.failCount,
    sessionOutputPaths: result.sessionOutputPaths,
    outputDir: result.outputDir,
  }, null, 2));
  return result;
}

worker = new Worker(cfg.exportWorker, { workerData });

worker.on("message", (message) => {
  if (!message || typeof message !== "object") return;
  if (message.type === "export:createdFiles") {
    createdFiles.push(...(Array.isArray(message.filePaths) ? message.filePaths : []));
    return;
  }
  if (message.type === "export:createdDirs") {
    createdDirs.push(...(Array.isArray(message.dirPaths) ? message.dirPaths : []));
    return;
  }
  if (message.type === "export:progress") {
    const now = Date.now();
    if (!cfg.quiet && (now - lastProgressAt > 1000 || message.data?.phase === "complete")) {
      lastProgressAt = now;
      const data = message.data || {};
      const phase = data.phase || "";
      const current = data.current ?? "";
      const total = data.total ?? "";
      const collected = data.collectedMessages ?? "";
      const exported = data.exportedMessages ?? "";
      console.log(`[weflow] phase=${phase} current=${current}/${total} collected=${collected} exported=${exported}`);
    }
    return;
  }
  if (message.type === "export:error") {
    console.error(String(message.error || "WeFlow export worker error"));
    writeResult({ success: false, successCount: 0, failCount: cfg.sessionIds.length, error: String(message.error || "") });
    finish(1);
    return;
  }
  if (message.type === "export:result") {
    const result = writeResult(message.data || {});
    finish(result.success === false ? 1 : 0);
  }
});

worker.on("error", (error) => {
  console.error(error && error.stack ? error.stack : String(error));
  finish(1);
});

worker.on("exit", (code) => {
  if (!finished && code !== 0) {
    console.error(`worker exited with code ${code}`);
    finish(code || 1);
  } else if (!finished) {
    finish(0);
  }
});

if (cfg.timeoutMs > 0) {
  setTimeout(() => {
    console.error(`export timeout after ${cfg.timeoutMs}ms`);
    finish(124);
  }, cfg.timeoutMs).unref();
}
"""


def run_worker(
    args: argparse.Namespace,
    paths: dict[str, Path],
    config: Any,
    secrets: dict[str, str],
    app_src: Path,
    session_ids: list[str],
    output_dir: Path,
) -> Path:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("未找到 node，无法运行 WeFlow exportWorker.js")

    db_path = Path(str(config.get("dbPath") or ""))
    raw_wxid = str(config.get("myWxid") or "").strip()
    my_wxid = clean_wxid(raw_wxid)
    if not db_path:
        raise RuntimeError("WeFlow-config.json 缺少 dbPath")
    if not raw_wxid:
        raise RuntimeError("WeFlow-config.json 缺少 myWxid")

    export_worker = app_src / "dist-electron" / "exportWorker.js"
    options = {
        "format": "json",
        "useAllTime": True,
        "dateRange": None,
        "exportMedia": bool(args.include_images),
        "exportImages": bool(args.include_images),
        "exportVideos": False,
        "exportVoices": False,
        "exportEmojis": False,
        "exportFiles": False,
        "exportWriteLayout": "B",
        "sessionLayout": "per-session",
        "exportPathStyle": "windows",
        "exportConflictStrategy": "overwrite",
        "fileNamingMode": "classic",
    }
    runner_cfg = {
        "exportWorker": str(export_worker),
        "sessionIds": session_ids,
        "outputDir": str(output_dir),
        "options": options,
        "taskId": f"codex-{int(datetime.now().timestamp())}",
        "dbPath": str(db_path),
        "myWxid": my_wxid,
        "accountDir": str(db_path / raw_wxid),
        "resourcesPath": str(paths["resources"]),
        "userDataPath": str(paths["user_data"]),
        "cachePath": str(config.get("cachePath") or ""),
        "emojiCacheDir": str(paths["emoji_cache"]),
        "quiet": bool(args.quiet),
        "cleanOutput": bool(args.clean_output),
        "timeoutMs": int(args.timeout_seconds * 1000),
    }
    env = os.environ.copy()
    env.update(
        {
            "WEFLOW_EXPORT_CONFIG_JSON": json.dumps(runner_cfg, ensure_ascii=False),
            "WEFLOW_DECRYPT_KEY": secrets["decryptKey"],
            "WEFLOW_IMAGE_XOR_KEY": secrets["imageXorKey"],
            "WEFLOW_IMAGE_AES_KEY": secrets["imageAesKey"],
            "WEFLOW_USER_DATA_PATH": str(paths["user_data"]),
        }
    )
    with tempfile.TemporaryDirectory(prefix="weflow-export-") as td:
        runner = Path(td) / "run-weflow-export.js"
        runner.write_text(build_node_runner(), encoding="utf-8")
        proc = subprocess.run(
            [node, str(runner)],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
            cwd=str(app_src),
            timeout=args.timeout_seconds + 45,
        )
    if proc.stdout.strip() and not args.quiet:
        print(proc.stdout.strip())
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"WeFlow 导出失败，退出码 {proc.returncode}：{err}")
    worker_result = output_dir / "worker-result.json"
    if not worker_result.is_file():
        raise RuntimeError(f"导出结束但未生成 worker-result.json：{worker_result}")
    return worker_result


def resolve_session_ids(args: argparse.Namespace, config: Any) -> list[str]:
    ids = args.session_id or []
    if not ids:
        last = str(config.get("lastSession") or "").strip()
        if last:
            ids = [last]
    resolved: list[str] = []
    for sid in ids:
        sid = str(sid or "").strip()
        if not sid:
            continue
        if sid.lower() == "last":
            last = str(config.get("lastSession") or "").strip()
            if not last:
                raise RuntimeError("WeFlow 配置里没有 lastSession，无法使用 --session-id last")
            sid = last
        resolved.append(sid)
    if not resolved:
        raise RuntimeError("请提供 --session-id，或先在 WeFlow 打开一次目标聊天后使用 --session-id last")
    return resolved


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Export local WeFlow chat history and derive analysis files.")
    p.add_argument("--session-id", action="append", help="WeFlow session id, e.g. 45018762878@chatroom. Repeat for multiple sessions. Use 'last' for config lastSession.")
    p.add_argument("--chat-name", help="Human-readable chat name used in reports.")
    p.add_argument("--output-dir", help="Root output directory. Defaults to Documents\\WeFlow-Exports\\<timestamp>-<session>.")
    p.add_argument("--format", choices=["all", "jsonl", "csv", "markdown", "md"], default="all", help="Derived output format. Raw WeFlow JSON is always exported.")
    p.add_argument("--include-images", dest="include_images", action="store_true", default=True, help="Export image media. Default: on.")
    p.add_argument("--no-images", dest="include_images", action="store_false", help="Do not export image media.")
    p.add_argument("--analyze", action="store_true", help="Write analysis-brief.md with deterministic stats and leads.")
    p.add_argument("--since", help="Filter derived outputs from this local time, e.g. 2026-07-05 or '2026-07-05 10:00'.")
    p.add_argument("--until", help="Filter derived outputs until this local time.")
    p.add_argument("--app-src", help="Existing extracted WeFlow app.asar source directory.")
    p.add_argument("--refresh-app-src", action="store_true", help="Re-extract WeFlow app.asar into the script cache.")
    p.add_argument("--clean-output", action="store_true", help="Delete the output directory before export. Use only for a dedicated export folder.")
    p.add_argument("--quiet", action="store_true", help="Reduce progress output.")
    p.add_argument("--timeout-seconds", type=int, default=600, help="Export timeout in seconds.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    paths = default_paths()
    config_path = paths["config"]
    local_state_path = paths["local_state"]
    if not config_path.is_file():
        raise RuntimeError(f"未找到 WeFlow 配置：{config_path}")
    if not local_state_path.is_file():
        raise RuntimeError(f"未找到 WeFlow Local State：{local_state_path}")
    if not paths["resources"].exists():
        raise RuntimeError(f"未找到 WeFlow resources：{paths['resources']}")

    config = load_json(config_path)
    session_ids = resolve_session_ids(args, config)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = paths["exports_root"] / f"{stamp}-{safe_filename(args.chat_name or session_ids[0])}"
    if args.clean_output:
        validate_clean_output_path(output_dir, paths)
    output_dir.mkdir(parents=True, exist_ok=True)

    since_dt = parse_bound(args.since, end=False)
    until_dt = parse_bound(args.until, end=True)
    if since_dt and until_dt and since_dt > until_dt:
        raise RuntimeError("--since 不能晚于 --until")

    print(f"[weflow] sessionIds={', '.join(session_ids)}")
    print(f"[weflow] outputDir={output_dir}")
    app_src = resolve_app_src(args, paths)
    print(f"[weflow] appSrc={app_src}")
    secrets = decrypt_weflow_secrets(config_path, local_state_path)
    print("[weflow] secrets=loaded-in-memory")
    worker_result = run_worker(args, paths, config, secrets, app_src, session_ids, output_dir)
    my_wxid_clean = clean_wxid(str(config.get("myWxid") or ""))
    manifests = postprocess_exports(worker_result, config, my_wxid_clean, args.chat_name, args.format, args.analyze, since_dt, until_dt)
    print("[weflow] derived manifests:")
    for manifest in manifests:
        print(json.dumps({
            "manifestPath": manifest.get("manifestPath"),
            "messageCount": manifest.get("messageCount"),
            "imageCount": manifest.get("imageCount"),
            "timeRange": manifest.get("timeRange"),
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        eprint("已取消")
        raise SystemExit(130)
    except Exception as exc:
        eprint(f"[weflow] ERROR: {exc}")
        raise SystemExit(1)
