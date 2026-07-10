import glob
import json
import os
import re
import subprocess
import sys
import time
import traceback


SERVER_NAME = "catstudio-online-log"
SERVER_VERSION = "0.1.0"
HOME = os.path.expanduser("~")
DEFAULT_CATSTUDIO_ROOT = os.environ.get(
    "CATSTUDIO_ROOT",
    os.path.join(HOME, "Desktop", "CATStudio_V3_1_4_89"),
)
DEFAULT_PROJECT_ROOT = os.environ.get(
    "CATSTUDIO_PROJECT_ROOT",
    os.getcwd(),
)
DEFAULT_CONFIG_FILE = "CATStudio_GenericTarget_Online.xml"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


DEFAULT_FILTER_PATTERNS = [
    "MMI",
    "HAL",
    "MSG_IPC",
    "APM",
    "APLP",
    "ATCMD",
    "ATCommand",
    "PRINTF",
    "WXP",
    "WXPAY",
    "CAMERA",
    "QRCODE",
    "QR",
    "QRDEC",
    "SCAN",
    "ZBAR",
]


TOOLS = [
    {
        "name": "catstudio_online_log_status",
        "description": "Inspect CATStudio online-log config, selected .mdb.txt database, process state, and latest log files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "catstudioRoot": {"type": "string"},
                "projectRoot": {"type": "string"},
            },
        },
    },
    {
        "name": "catstudio_prepare_online_log_viewer",
        "description": "After flashing, prepare CATStudio for online LogViewer: select Generic Target Online, ensure the current .mdb.txt database, and optionally apply the right-side filter whitelist.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "catstudioRoot": {"type": "string"},
                "projectRoot": {"type": "string"},
                "txtDbPath": {"type": "string"},
                "configFile": {"type": "string", "default": DEFAULT_CONFIG_FILE},
                "startCatstudio": {"type": "boolean", "default": True},
                "selectOnlineConfig": {"type": "boolean", "default": True},
                "applyConfig": {"type": "boolean", "default": True},
                "applyFilter": {"type": "boolean", "default": True},
                "filterPatterns": {"type": "array", "items": {"type": "string"}},
                "strictFilter": {"type": "boolean", "default": True},
                "dryRun": {"type": "boolean", "default": False},
                "timeoutSec": {"type": "integer", "minimum": 5, "maximum": 120, "default": 35},
            },
        },
    },
]


def norm(path):
    return os.path.abspath(os.path.expanduser(path))


def catstudio_paths(root):
    root = norm(root or DEFAULT_CATSTUDIO_ROOT)
    exec_dir = os.path.join(root, "Exec")
    return {
        "root": root,
        "execDir": exec_dir,
        "exe": os.path.join(exec_dir, "CATStudio.exe"),
        "configDir": os.path.join(exec_dir, "Config"),
        "onlineConfig": os.path.join(exec_dir, "Config", DEFAULT_CONFIG_FILE),
        "binLogs": os.path.join(exec_dir, "Bin Logs"),
    }


def find_default_txt_db(project_root):
    project_root = norm(project_root or DEFAULT_PROJECT_ROOT)
    patterns = [
        os.path.join(project_root, "out", "product", "**", "craneg_modem_watch.mdb.txt"),
        os.path.join(project_root, "out", "product", "**", "*.mdb.txt"),
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern, recursive=True))
    candidates = [p for p in candidates if os.path.isfile(p)]
    candidates = sorted(set(candidates), key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0] if candidates else None


def latest_logs(bin_logs, limit=5):
    items = []
    if not os.path.isdir(bin_logs):
        return items
    for path in glob.glob(os.path.join(bin_logs, "*.icl")) + glob.glob(os.path.join(bin_logs, "*.icld")):
        base, _ = os.path.splitext(path)
        item = {
            "path": path,
            "sizeBytes": os.path.getsize(path),
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path))),
        }
        ild = base + ".ild"
        if os.path.isfile(ild):
            item["ild"] = {
                "path": ild,
                "sizeBytes": os.path.getsize(ild),
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(ild))),
            }
        items.append(item)
    return sorted(items, key=lambda x: os.path.getmtime(x["path"]), reverse=True)[:limit]


def read_text_preserve_encoding(path):
    raw = open(path, "rb").read()
    for encoding in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace"), "utf-8"


def extract_tag(text, tag):
    match = re.search(r"<%s(?:\s[^>]*)?>(.*?)</%s>" % (re.escape(tag), re.escape(tag)), text, re.S)
    if match:
        return match.group(1)
    if re.search(r"<%s\s*/>" % re.escape(tag), text):
        return ""
    return None


def extract_tag_in_block(text, block_tag, tag):
    match = re.search(r"<%s(?:\s[^>]*)?>(.*?)</%s>" % (re.escape(block_tag), re.escape(block_tag)), text, re.S)
    if not match:
        return None
    return extract_tag(match.group(1), tag)


def replace_tag(text, tag, value):
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    full = re.compile(r"(<%s(?:\s[^>]*)?>)(.*?)(</%s>)" % (re.escape(tag), re.escape(tag)), re.S)
    if full.search(text):
        return full.sub(lambda match: match.group(1) + value + match.group(3), text, count=1)
    empty = re.compile(r"<%s\s*/>" % re.escape(tag))
    if empty.search(text):
        return empty.sub(lambda match: "<%s>%s</%s>" % (tag, value, tag), text, count=1)
    return text


def replace_tag_in_block(text, block_tag, tag, value):
    block = re.compile(r"(<%s(?:\s[^>]*)?>)(.*?)(</%s>)" % (re.escape(block_tag), re.escape(block_tag)), re.S)
    match = block.search(text)
    if not match:
        return text
    new_body = replace_tag(match.group(2), tag, value)
    return text[:match.start(2)] + new_body + text[match.end(2):]


def get_catstudio_processes():
    if os.name != "nt":
        return []
    script = (
        "Get-Process CATStudio -ErrorAction SilentlyContinue | "
        "Select-Object Id,MainWindowTitle,MainWindowHandle,StartTime | ConvertTo-Json -Depth 4"
    )
    result = run_process(["powershell.exe", "-NoProfile", "-Command", script], timeout=10)
    try:
        data = json.loads(result.get("stdout") or "null")
    except Exception:
        data = None
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


def read_online_config(root, config_file=DEFAULT_CONFIG_FILE):
    paths = catstudio_paths(root)
    config_path = os.path.join(paths["configDir"], config_file)
    info = {"path": config_path, "exists": os.path.isfile(config_path)}
    if not info["exists"]:
        return info
    try:
        text, encoding = read_text_preserve_encoding(config_path)
        info.update({
            "encoding": encoding,
            "isOnline": extract_tag_in_block(text, "Common", "IsOnline"),
            "isLogOnly": extract_tag_in_block(text, "Common", "IsLogOnly"),
            "logViewerDeviceId": extract_tag_in_block(text, "LogViewer", "DeviceID"),
            "filterDeviceId": extract_tag_in_block(text, "LogViewer", "DeviceIDForFilterDlg"),
            "lastCpTextDb": extract_tag_in_block(text, "Last_CP_DIAG_DB_Path_Device0", "Last_CP_DB_TEXT_PATH"),
            "lastApTextDb": extract_tag_in_block(text, "Last_CP_DIAG_DB_Path_Device0", "Last_AP_DB_Text_Path"),
            "txtCpPath1": extract_tag_in_block(text, "TXT_CP_DB_PATH_Device0", "Path_1"),
            "txtApPath1": extract_tag_in_block(text, "TXT_AP_DB_PATH_Device0", "Path_1"),
            "csvFilterFile": extract_tag_in_block(text, "LogViewer", "CSV_Filter_File"),
        })
    except Exception as exc:
        info["error"] = str(exc)
    return info


def update_online_config(root, txt_db_path, config_file=DEFAULT_CONFIG_FILE, dry_run=False):
    paths = catstudio_paths(root)
    config_path = os.path.join(paths["configDir"], config_file)
    if not os.path.isfile(config_path):
        return {"status": "ERROR", "error": "online config not found", "path": config_path}
    txt_db_path = norm(txt_db_path)
    if not os.path.isfile(txt_db_path):
        return {"status": "ERROR", "error": "txtDbPath not found", "path": txt_db_path}

    before = read_online_config(root, config_file)
    text, encoding = read_text_preserve_encoding(config_path)
    new_text = text
    new_text = replace_tag_in_block(new_text, "Common", "IsOnline", "true")
    new_text = replace_tag_in_block(new_text, "Common", "IsLogOnly", "false")
    new_text = replace_tag_in_block(new_text, "LogViewer", "DeviceID", "0")
    new_text = replace_tag_in_block(new_text, "LogViewer", "DeviceIDForFilterDlg", "0")
    new_text = replace_tag_in_block(new_text, "Last_CP_DIAG_DB_Path_Device0", "Last_CP_DB_TEXT_PATH", txt_db_path)
    new_text = replace_tag_in_block(new_text, "Last_CP_DIAG_DB_Path_Device0", "Last_AP_DB_Text_Path", txt_db_path)
    new_text = replace_tag_in_block(new_text, "TXT_CP_DB_PATH_Device0", "Path_1", txt_db_path)
    new_text = replace_tag_in_block(new_text, "TXT_AP_DB_PATH_Device0", "Path_1", txt_db_path)

    if dry_run:
        return {"status": "DRY_RUN", "path": config_path, "txtDbPath": txt_db_path, "before": before}

    backup_path = config_path + ".codex-bak"
    if not os.path.exists(backup_path):
        with open(config_path, "rb") as src, open(backup_path, "wb") as dst:
            dst.write(src.read())
    with open(config_path, "wb") as dst:
        dst.write(new_text.encode(encoding, errors="replace"))
    after = read_online_config(root, config_file)
    return {"status": "OK", "path": config_path, "backup": backup_path, "txtDbPath": txt_db_path, "before": before, "after": after}


def run_process(args, timeout=20, cwd=None):
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "args": args,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "args": args}


def powershell_exe(use_32bit=False):
    if use_32bit and os.name == "nt":
        exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe")
        if os.path.isfile(exe):
            return exe
    return "powershell.exe"


def run_powershell(script, timeout=30, use_32bit=False):
    result = run_process(
        [powershell_exe(use_32bit), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        timeout=timeout,
    )
    data = None
    stdout = (result.get("stdout") or "").strip()
    if stdout:
        try:
            data = json.loads(stdout)
        except Exception:
            data = None
    return result, data


def start_catstudio(root, dry_run=False):
    paths = catstudio_paths(root)
    if not os.path.isfile(paths["exe"]):
        return {"status": "ERROR", "error": "CATStudio.exe not found", "path": paths["exe"]}
    processes = get_catstudio_processes()
    if processes:
        return {"status": "ALREADY_RUNNING", "processes": processes}
    if dry_run:
        return {"status": "DRY_RUN", "wouldStart": paths["exe"], "cwd": paths["execDir"]}
    subprocess.Popen([paths["exe"]], cwd=paths["execDir"], creationflags=CREATE_NO_WINDOW)
    return {"status": "STARTED", "path": paths["exe"]}


def apply_treeview_filter_native(filter_patterns, strict_filter=True, dry_run=False, timeout_sec=20):
    if os.name != "nt":
        return {"status": "SKIPPED", "reason": "native TreeView filtering is Windows-only"}

    pattern_ps = "@(" + ",".join(json.dumps(str(item)) for item in filter_patterns) + ")"
    script = r"""
$ErrorActionPreference = "Stop"
$dryRun = __DRY_RUN__
$strictFilter = __STRICT_FILTER__
$filterPatterns = __FILTER_PATTERNS__

function New-Result($status, $message, $extra = @{}) {
    $obj = [ordered]@{ status = $status; message = $message }
    foreach ($key in $extra.Keys) { $obj[$key] = $extra[$key] }
    $obj | ConvertTo-Json -Depth 16
}

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;

public class CatStudioTreeWin32 {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr hWndParent, EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll", SetLastError = true)] public static extern IntPtr SendMessageTimeout(IntPtr hWnd, int Msg, IntPtr wParam, IntPtr lParam, uint fuFlags, uint uTimeout, out IntPtr lpdwResult);

    [DllImport("kernel32.dll", SetLastError = true)] public static extern IntPtr OpenProcess(uint dwDesiredAccess, bool bInheritHandle, uint dwProcessId);
    [DllImport("kernel32.dll", SetLastError = true)] public static extern bool CloseHandle(IntPtr hObject);
    [DllImport("kernel32.dll", SetLastError = true)] public static extern IntPtr VirtualAllocEx(IntPtr hProcess, IntPtr lpAddress, UIntPtr dwSize, uint flAllocationType, uint flProtect);
    [DllImport("kernel32.dll", SetLastError = true)] public static extern bool VirtualFreeEx(IntPtr hProcess, IntPtr lpAddress, UIntPtr dwSize, uint dwFreeType);
    [DllImport("kernel32.dll", SetLastError = true)] public static extern bool ReadProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, byte[] lpBuffer, int dwSize, out int lpNumberOfBytesRead);
    [DllImport("kernel32.dll", SetLastError = true)] public static extern bool WriteProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, byte[] lpBuffer, int nSize, out int lpNumberOfBytesWritten);
}
"@

$TV_FIRST = 0x1100
$TVM_GETNEXTITEM = $TV_FIRST + 10
$TVM_GETITEMW = $TV_FIRST + 62
$TVM_SETITEMW = $TV_FIRST + 63
$TVGN_ROOT = 0
$TVGN_NEXT = 1
$TVGN_CHILD = 4
$TVIF_TEXT = 0x0001
$TVIF_STATE = 0x0008
$TVIS_STATEIMAGEMASK = 0xF000
$PROCESS_VM_OPERATION = 0x0008
$PROCESS_VM_READ = 0x0010
$PROCESS_VM_WRITE = 0x0020
$MEM_COMMIT = 0x1000
$MEM_RESERVE = 0x2000
$MEM_RELEASE = 0x8000
$PAGE_READWRITE = 0x04

function New-UIntPtr([UInt32]$value) {
    return [UIntPtr]$value
}

function Set-U32([byte[]]$buf, [int]$offset, [UInt32]$value) {
    [BitConverter]::GetBytes($value).CopyTo($buf, $offset)
}

function Set-I32([byte[]]$buf, [int]$offset, [Int32]$value) {
    [BitConverter]::GetBytes($value).CopyTo($buf, $offset)
}

function Set-Ptr32([byte[]]$buf, [int]$offset, [IntPtr]$value) {
    [BitConverter]::GetBytes($value.ToInt32()).CopyTo($buf, $offset)
}

function Invoke-TreeMessage([IntPtr]$treeHwnd, [int]$msg, [IntPtr]$wParam, [IntPtr]$lParam) {
    $messageResult = [IntPtr]::Zero
    $ok = [CatStudioTreeWin32]::SendMessageTimeout($treeHwnd, $msg, $wParam, $lParam, 0x2, 1000, [ref]$messageResult)
    if ($ok -eq [IntPtr]::Zero) { return [IntPtr]::Zero }
    return $messageResult
}

function Write-RemoteBytes([IntPtr]$processHandle, [IntPtr]$address, [byte[]]$bytes) {
    [int]$written = 0
    return [CatStudioTreeWin32]::WriteProcessMemory($processHandle, $address, $bytes, $bytes.Length, [ref]$written)
}

function Read-RemoteBytes([IntPtr]$processHandle, [IntPtr]$address, [int]$length) {
    $bytes = New-Object byte[] $length
    [int]$read = 0
    [void][CatStudioTreeWin32]::ReadProcessMemory($processHandle, $address, $bytes, $length, [ref]$read)
    return $bytes
}

function Read-TreeItem([IntPtr]$treeHwnd, [IntPtr]$processHandle, [IntPtr]$remoteItem, [IntPtr]$remoteText, [IntPtr]$itemHandle, [int]$depth, [string]$parentPath) {
    $itemBytes = New-Object byte[] 40
    Set-U32 $itemBytes 0 ([UInt32]($TVIF_TEXT -bor $TVIF_STATE))
    Set-Ptr32 $itemBytes 4 $itemHandle
    Set-U32 $itemBytes 12 ([UInt32]$TVIS_STATEIMAGEMASK)
    Set-Ptr32 $itemBytes 16 $remoteText
    Set-I32 $itemBytes 20 512

    [void](Write-RemoteBytes $processHandle $remoteItem $itemBytes)
    [void](Invoke-TreeMessage $treeHwnd $TVM_GETITEMW ([IntPtr]::Zero) $remoteItem)

    $afterBytes = Read-RemoteBytes $processHandle $remoteItem 40
    $textBytes = Read-RemoteBytes $processHandle $remoteText 1024
    $state = [BitConverter]::ToUInt32($afterBytes, 8)
    $stateIndex = (($state -band $TVIS_STATEIMAGEMASK) -shr 12)
    $text = [System.Text.Encoding]::Unicode.GetString($textBytes)
    $nul = $text.IndexOf([char]0)
    if ($nul -ge 0) { $text = $text.Substring(0, $nul) }
    if ([string]::IsNullOrWhiteSpace($parentPath)) { $path = $text } else { $path = "$parentPath/$text" }

    return [pscustomobject]@{
        HItem = $itemHandle
        Text = $text
        Path = $path
        Depth = $depth
        State = $state
        StateIndex = $stateIndex
    }
}

function Set-TreeItemState([IntPtr]$treeHwnd, [IntPtr]$processHandle, [IntPtr]$remoteItem, [IntPtr]$itemHandle, [int]$stateIndex) {
    $itemBytes = New-Object byte[] 40
    Set-U32 $itemBytes 0 ([UInt32]$TVIF_STATE)
    Set-Ptr32 $itemBytes 4 $itemHandle
    Set-U32 $itemBytes 8 ([UInt32]($stateIndex -shl 12))
    Set-U32 $itemBytes 12 ([UInt32]$TVIS_STATEIMAGEMASK)
    [void](Write-RemoteBytes $processHandle $remoteItem $itemBytes)
    $res = Invoke-TreeMessage $treeHwnd $TVM_SETITEMW ([IntPtr]::Zero) $remoteItem
    return ($res -ne [IntPtr]::Zero)
}

function Test-WantedLogItem([string]$name, [string]$path) {
    if ([string]::IsNullOrWhiteSpace($name)) { return $false }
    $upperName = $name.ToUpperInvariant()
    $upperPath = $path.ToUpperInvariant()
    foreach ($pattern in $filterPatterns) {
        if ([string]::IsNullOrWhiteSpace($pattern)) { continue }
        $upperPattern = $pattern.ToUpperInvariant()
        if ($upperName -like ("*" + $upperPattern + "*") -or $upperPath -like ("*" + $upperPattern + "*")) {
            return $true
        }
    }
    return $false
}

function Get-TreeRect([IntPtr]$hwnd) {
    $rect = New-Object CatStudioTreeWin32+RECT
    [void][CatStudioTreeWin32]::GetWindowRect($hwnd, [ref]$rect)
    return [ordered]@{
        left = $rect.Left
        top = $rect.Top
        right = $rect.Right
        bottom = $rect.Bottom
        width = ($rect.Right - $rect.Left)
        height = ($rect.Bottom - $rect.Top)
    }
}

$proc = Get-Process CATStudio -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Sort-Object StartTime -Descending |
    Select-Object -First 1
if ($null -eq $proc) {
    New-Result "NO_PROCESS" "CATStudio main window was not found"
    exit 0
}

$script:treeHandles = New-Object System.Collections.ArrayList
$enumCallback = [CatStudioTreeWin32+EnumWindowsProc]{
    param([IntPtr]$hwnd, [IntPtr]$lParam)
    $className = New-Object System.Text.StringBuilder 256
    [void][CatStudioTreeWin32]::GetClassName($hwnd, $className, $className.Capacity)
    if ($className.ToString() -eq "SysTreeView32") {
        [void]$script:treeHandles.Add($hwnd)
    }
    return $true
}
[void][CatStudioTreeWin32]::EnumChildWindows([IntPtr]$proc.MainWindowHandle, $enumCallback, [IntPtr]::Zero)

if ($script:treeHandles.Count -eq 0) {
    New-Result "FILTER_NOT_APPLIED" "No SysTreeView32 controls were found in CATStudio" @{ processId = $proc.Id; treeCount = 0 }
    exit 0
}

$treeReports = New-Object System.Collections.ArrayList
foreach ($treeHwnd in $script:treeHandles) {
    [uint32]$treePid = 0
    [void][CatStudioTreeWin32]::GetWindowThreadProcessId($treeHwnd, [ref]$treePid)
    $processHandle = [CatStudioTreeWin32]::OpenProcess(($PROCESS_VM_OPERATION -bor $PROCESS_VM_READ -bor $PROCESS_VM_WRITE), $false, $treePid)
    if ($processHandle -eq [IntPtr]::Zero) {
        [void]$treeReports.Add([ordered]@{ hwnd = $treeHwnd.ToInt64(); error = "OpenProcess failed"; score = -1 })
        continue
    }
    $remoteItem = [CatStudioTreeWin32]::VirtualAllocEx($processHandle, [IntPtr]::Zero, (New-UIntPtr 64), ($MEM_COMMIT -bor $MEM_RESERVE), $PAGE_READWRITE)
    $remoteText = [CatStudioTreeWin32]::VirtualAllocEx($processHandle, [IntPtr]::Zero, (New-UIntPtr 1024), ($MEM_COMMIT -bor $MEM_RESERVE), $PAGE_READWRITE)
    if ($remoteItem -eq [IntPtr]::Zero -or $remoteText -eq [IntPtr]::Zero) {
        [void]$treeReports.Add([ordered]@{ hwnd = $treeHwnd.ToInt64(); error = "VirtualAllocEx failed"; score = -1 })
        [void][CatStudioTreeWin32]::CloseHandle($processHandle)
        continue
    }

    $items = New-Object System.Collections.ArrayList
    function Walk-TreeItems([IntPtr]$itemHandle, [int]$depth, [string]$parentPath) {
        while ($itemHandle -ne [IntPtr]::Zero) {
            $item = Read-TreeItem $treeHwnd $processHandle $remoteItem $remoteText $itemHandle $depth $parentPath
            [void]$items.Add($item)
            $child = Invoke-TreeMessage $treeHwnd $TVM_GETNEXTITEM ([IntPtr]$TVGN_CHILD) $itemHandle
            if ($child -ne [IntPtr]::Zero) {
                Walk-TreeItems $child ($depth + 1) $item.Path
            }
            $itemHandle = Invoke-TreeMessage $treeHwnd $TVM_GETNEXTITEM ([IntPtr]$TVGN_NEXT) $itemHandle
        }
    }

    $rootItem = Invoke-TreeMessage $treeHwnd $TVM_GETNEXTITEM ([IntPtr]$TVGN_ROOT) ([IntPtr]::Zero)
    if ($rootItem -ne [IntPtr]::Zero) {
        Walk-TreeItems $rootItem 0 ""
    }

    $matched = @($items | Where-Object { Test-WantedLogItem $_.Text $_.Path })
    $hasAll = @($items | Where-Object { $_.Text -match "^(All|全部)$" }).Count -gt 0
    $score = ($matched.Count * 100) + $(if ($hasAll) { 50 } else { 0 }) + $(if ($items.Count -gt 3) { 5 } else { 0 })
    $rect = Get-TreeRect $treeHwnd
    $sample = @($items | Select-Object -First 40 | ForEach-Object {
        [ordered]@{ text = $_.Text; path = $_.Path; stateIndex = $_.StateIndex; depth = $_.Depth }
    })
    [void]$treeReports.Add([pscustomobject]@{
        NativeHwnd = $treeHwnd
        ProcessHandle = $processHandle
        RemoteItem = $remoteItem
        RemoteText = $remoteText
        Items = $items
        hwnd = $treeHwnd.ToInt64()
        visible = [CatStudioTreeWin32]::IsWindowVisible($treeHwnd)
        rect = $rect
        itemCount = $items.Count
        matchedCount = $matched.Count
        hasAll = $hasAll
        score = $score
        sample = $sample
    })
}

$target = $treeReports | Where-Object { $_.score -ge 0 } | Sort-Object score -Descending | Select-Object -First 1
if ($null -eq $target -or $target.matchedCount -eq 0) {
    $reports = @($treeReports | ForEach-Object {
        [ordered]@{ hwnd = $_.hwnd; visible = $_.visible; rect = $_.rect; itemCount = $_.itemCount; matchedCount = $_.matchedCount; score = $_.score; sample = $_.sample; error = $_.error }
    })
    New-Result "FILTER_NOT_APPLIED" "SysTreeView32 controls were found, but no requested filter nodes matched" @{
        processId = $proc.Id
        treeCount = $script:treeHandles.Count
        patterns = $filterPatterns
        trees = $reports
    }
    exit 0
}

$matchedReport = New-Object System.Collections.ArrayList
$changedReport = New-Object System.Collections.ArrayList
$skippedReport = New-Object System.Collections.ArrayList

foreach ($item in $target.Items) {
    if ([string]::IsNullOrWhiteSpace($item.Text)) { continue }
    $wanted = Test-WantedLogItem $item.Text $item.Path
    if ($wanted) {
        [void]$matchedReport.Add([ordered]@{ text = $item.Text; path = $item.Path; oldStateIndex = $item.StateIndex })
    }
    if (-not $wanted -and -not $strictFilter) { continue }
    if ($item.StateIndex -eq 0) {
        [void]$skippedReport.Add([ordered]@{ text = $item.Text; path = $item.Path; reason = "no checkbox state" })
        continue
    }
    $desiredStateIndex = $(if ($wanted) { 2 } else { 1 })
    $changed = ($item.StateIndex -ne $desiredStateIndex)
    $setOk = $true
    $newStateIndex = $item.StateIndex
    if ($changed -and -not $dryRun) {
        $setOk = Set-TreeItemState $target.NativeHwnd $target.ProcessHandle $target.RemoteItem $item.HItem $desiredStateIndex
        if ($setOk) {
            $newStateIndex = $desiredStateIndex
        }
    } elseif ($changed -and $dryRun) {
        $newStateIndex = $desiredStateIndex
    }
    if ($changed -or -not $setOk) {
        [void]$changedReport.Add([ordered]@{
            text = $item.Text
            path = $item.Path
            wanted = $wanted
            oldStateIndex = $item.StateIndex
            desiredStateIndex = $desiredStateIndex
            newStateIndex = $newStateIndex
            setOk = $setOk
            dryRun = $dryRun
        })
    }
}

$reportsForJson = @($treeReports | ForEach-Object {
    [ordered]@{ hwnd = $_.hwnd; visible = $_.visible; rect = $_.rect; itemCount = $_.itemCount; matchedCount = $_.matchedCount; score = $_.score; sample = $_.sample; error = $_.error }
})

New-Result "OK" "CATStudio right-side filter tree was prepared" @{
    processId = $proc.Id
    title = $proc.MainWindowTitle
    dryRun = $dryRun
    strict = $strictFilter
    patterns = $filterPatterns
    method = "win32-32bit-systreeview32"
    selectedTree = [ordered]@{ hwnd = $target.hwnd; rect = $target.rect; itemCount = $target.itemCount; matchedCount = $target.matchedCount; score = $target.score }
    matchedCount = $matchedReport.Count
    changedCount = $changedReport.Count
    skippedCount = $skippedReport.Count
    matched = @($matchedReport | Select-Object -First 200)
    changed = @($changedReport | Select-Object -First 200)
    skipped = @($skippedReport | Select-Object -First 80)
    trees = $reportsForJson
}

foreach ($tree in $treeReports) {
    if ($tree.ProcessHandle -and $tree.ProcessHandle -ne [IntPtr]::Zero) {
        if ($tree.RemoteItem -and $tree.RemoteItem -ne [IntPtr]::Zero) { [void][CatStudioTreeWin32]::VirtualFreeEx($tree.ProcessHandle, $tree.RemoteItem, (New-UIntPtr 0), $MEM_RELEASE) }
        if ($tree.RemoteText -and $tree.RemoteText -ne [IntPtr]::Zero) { [void][CatStudioTreeWin32]::VirtualFreeEx($tree.ProcessHandle, $tree.RemoteText, (New-UIntPtr 0), $MEM_RELEASE) }
        [void][CatStudioTreeWin32]::CloseHandle($tree.ProcessHandle)
    }
}
"""
    replacements = {
        "__DRY_RUN__": "$true" if dry_run else "$false",
        "__STRICT_FILTER__": "$true" if strict_filter else "$false",
        "__FILTER_PATTERNS__": pattern_ps,
    }
    for key, value in replacements.items():
        script = script.replace(key, value)

    result, data = run_powershell(script, timeout=timeout_sec + 15, use_32bit=True)
    if data is not None:
        return data
    return {
        "status": "ERROR",
        "error": "native TreeView filtering did not return JSON",
        "process": result,
        "powershell": powershell_exe(use_32bit=True),
    }


def automate_catstudio_ui(args):
    root = norm(args.get("catstudioRoot") or DEFAULT_CATSTUDIO_ROOT)
    config_name = args.get("configName") or "Generic Target Online"
    config_file = args.get("configFile") or DEFAULT_CONFIG_FILE
    dry_run = bool(args.get("dryRun", False))
    select_online = bool(args.get("selectOnlineConfig", True))
    apply_filter = bool(args.get("applyFilter", True))
    strict_filter = bool(args.get("strictFilter", True))
    filter_patterns = args.get("filterPatterns") or DEFAULT_FILTER_PATTERNS
    timeout_sec = int(args.get("timeoutSec") or 35)
    start_status = args.get("_catstudioStartStatus")
    config_dialog_wait_sec = 12 if start_status == "STARTED" else 3
    pattern_ps = "@(" + ",".join(json.dumps(str(item)) for item in filter_patterns) + ")"
    script = r"""
$ErrorActionPreference = "Stop"
$configName = __CONFIG_NAME__
$configFile = __CONFIG_FILE__
$dryRun = __DRY_RUN__
$selectOnline = __SELECT_ONLINE__
$applyFilter = __APPLY_FILTER__
$strictFilter = __STRICT_FILTER__
$filterPatterns = __FILTER_PATTERNS__

function New-Result($status, $message, $extra = @{}) {
    $obj = [ordered]@{ status = $status; message = $message }
    foreach ($key in $extra.Keys) { $obj[$key] = $extra[$key] }
    $obj | ConvertTo-Json -Depth 12
}

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class CatStudioOnlineLogWin32 {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr hWndParent, EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern IntPtr SetFocus(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr hWnd, int Msg, IntPtr wParam, IntPtr lParam);
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
"@

function Click-Element($el) {
    $rect = $el.Current.BoundingRectangle
    $x = [int](($rect.Left + $rect.Right) / 2)
    $y = [int](($rect.Top + $rect.Bottom) / 2)
    [void][CatStudioOnlineLogWin32]::SetCursorPos($x, $y)
    [CatStudioOnlineLogWin32]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 60
    [CatStudioOnlineLogWin32]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
}

function Invoke-Or-Click($el) {
    try {
        $pattern = $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        $pattern.Invoke()
        return "invoke"
    } catch {
        Click-Element $el
        return "click"
    }
}

function Click-ButtonNative($el) {
    $handle = [IntPtr]$el.Current.NativeWindowHandle
    if ($handle -ne [IntPtr]::Zero) {
        [void][CatStudioOnlineLogWin32]::SendMessage($handle, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)
        return "bm_click"
    }
    return Invoke-Or-Click $el
}

function Find-ChildWindowByClass([IntPtr]$parent, [string]$className) {
    $script:foundChild = [IntPtr]::Zero
    $callback = [CatStudioOnlineLogWin32+EnumWindowsProc]{
        param([IntPtr]$hwnd, [IntPtr]$lParam)
        $buf = New-Object System.Text.StringBuilder 256
        [void][CatStudioOnlineLogWin32]::GetClassName($hwnd, $buf, $buf.Capacity)
        if ($buf.ToString() -eq $className) {
            $script:foundChild = $hwnd
            return $false
        }
        return $true
    }
    [void][CatStudioOnlineLogWin32]::EnumChildWindows($parent, $callback, [IntPtr]::Zero)
    return $script:foundChild
}

function Find-ChildWindowByTitle([IntPtr]$parent, [string]$titlePattern) {
    $script:foundChildByTitle = [IntPtr]::Zero
    $callback = [CatStudioOnlineLogWin32+EnumWindowsProc]{
        param([IntPtr]$hwnd, [IntPtr]$lParam)
        $buf = New-Object System.Text.StringBuilder 512
        [void][CatStudioOnlineLogWin32]::GetWindowText($hwnd, $buf, $buf.Capacity)
        if ($buf.ToString() -match $titlePattern -and [CatStudioOnlineLogWin32]::IsWindowVisible($hwnd)) {
            $script:foundChildByTitle = $hwnd
            return $false
        }
        return $true
    }
    [void][CatStudioOnlineLogWin32]::EnumChildWindows($parent, $callback, [IntPtr]::Zero)
    return $script:foundChildByTitle
}

function Count-VisibleChildWindowsByClass([IntPtr]$parent, [string]$className) {
    $script:classCount = 0
    $callback = [CatStudioOnlineLogWin32+EnumWindowsProc]{
        param([IntPtr]$hwnd, [IntPtr]$lParam)
        $buf = New-Object System.Text.StringBuilder 256
        [void][CatStudioOnlineLogWin32]::GetClassName($hwnd, $buf, $buf.Capacity)
        if ($buf.ToString() -eq $className -and [CatStudioOnlineLogWin32]::IsWindowVisible($hwnd)) {
            $script:classCount += 1
        }
        return $true
    }
    [void][CatStudioOnlineLogWin32]::EnumChildWindows($parent, $callback, [IntPtr]::Zero)
    return $script:classCount
}

function Open-LogViewerFilter([IntPtr]$mainHwnd) {
    $WM_COMMAND = 0x0111
    $ID_SHOW_FILTER = 35045
    $beforeTreeCount = Count-VisibleChildWindowsByClass $mainHwnd "SysTreeView32"
    if ($beforeTreeCount -gt 0) {
        return @{
            status = "ALREADY_OPEN"
            targetKind = "none"
            targetHwnd = 0
            commandId = $ID_SHOW_FILTER
            sendResult = 0
            visibleTreeCountBefore = $beforeTreeCount
            visibleTreeCountAfter = $beforeTreeCount
        }
    }
    $target = Find-ChildWindowByTitle $mainHwnd "^LogViewer$"
    $targetKind = "logviewer-child"
    if ($target -eq [IntPtr]::Zero) {
        $target = $mainHwnd
        $targetKind = "main-window-fallback"
    }
    $sendResult = 0
    if (-not $dryRun) {
        $sendResult = [CatStudioOnlineLogWin32]::SendMessage($target, $WM_COMMAND, [IntPtr]$ID_SHOW_FILTER, [IntPtr]::Zero).ToInt64()
        Start-Sleep -Milliseconds 700
    }
    $afterTreeCount = Count-VisibleChildWindowsByClass $mainHwnd "SysTreeView32"
    return @{
        status = "SENT_SHOW_FILTER"
        targetKind = $targetKind
        targetHwnd = $target.ToInt64()
        commandId = $ID_SHOW_FILTER
        sendResult = $sendResult
        visibleTreeCountBefore = $beforeTreeCount
        visibleTreeCountAfter = $afterTreeCount
    }
}

function Select-GenericTargetOnline($dlg) {
    $dlgHandle = [IntPtr]$dlg.Current.NativeWindowHandle
    if ($dlgHandle -eq [IntPtr]::Zero) {
        return @{ status = "NO_DIALOG_HANDLE" }
    }
    $listHandle = Find-ChildWindowByClass $dlgHandle "SysListView32"
    if ($listHandle -eq [IntPtr]::Zero) {
        return @{ status = "NO_LISTVIEW"; dialogHandle = $dlgHandle.ToInt64() }
    }
    $rect = New-Object CatStudioOnlineLogWin32+RECT
    [void][CatStudioOnlineLogWin32]::GetWindowRect($listHandle, [ref]$rect)
    if (-not $dryRun) {
        [void][CatStudioOnlineLogWin32]::SetFocus($listHandle)
        Start-Sleep -Milliseconds 80
        [System.Windows.Forms.SendKeys]::SendWait("{HOME}")
        Start-Sleep -Milliseconds 80
        [System.Windows.Forms.SendKeys]::SendWait("{DOWN}")
        Start-Sleep -Milliseconds 80
        $x = [int]($rect.Left + 90)
        $y = [int]($rect.Top + 42)
        [void][CatStudioOnlineLogWin32]::SetCursorPos($x, $y)
        [CatStudioOnlineLogWin32]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 40
        [CatStudioOnlineLogWin32]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 120
    }
    return @{
        status = "SELECTED_BY_KEYBOARD_AND_CLICK"
        dialogHandle = $dlgHandle.ToInt64()
        listHandle = $listHandle.ToInt64()
        listRect = @{ left = $rect.Left; top = $rect.Top; right = $rect.Right; bottom = $rect.Bottom }
        row = "Generic Target Online"
    }
}

function Set-Toggle($el, [bool]$wantOn) {
    try {
        $toggle = $el.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
        $state = $toggle.Current.ToggleState
        $isOn = ($state -eq [System.Windows.Automation.ToggleState]::On)
        if ($isOn -ne $wantOn) {
            if (-not $dryRun) { $toggle.Toggle() }
            return @{ changed = $true; old = "$state"; desired = $wantOn }
        }
        return @{ changed = $false; old = "$state"; desired = $wantOn }
    } catch {
        return @{ changed = $false; error = $_.Exception.Message; desired = $wantOn }
    }
}

$deadline = (Get-Date).AddSeconds(__TIMEOUT_SEC__)
$configDialogDeadline = (Get-Date).AddSeconds([Math]::Min(__TIMEOUT_SEC__, __CONFIG_DIALOG_WAIT_SEC__))
$rootEl = [System.Windows.Automation.AutomationElement]::RootElement
$steps = New-Object System.Collections.ArrayList

if ($selectOnline) {
    while ((Get-Date) -lt $configDialogDeadline) {
        $windows = $rootEl.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
        $dlg = $null
        foreach ($w in $windows) {
            if ($w.Current.Name -match "Select Configuration File") {
                $dlg = $w
                break
            }
        }
        if ($null -eq $dlg) {
            foreach ($w in $windows) {
                if ($w.Current.Name -notmatch "CATStudio") { continue }
                $desc = $w.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
                foreach ($el in $desc) {
                    if ($el.Current.Name -match "Select Configuration File" -and $el.Current.ControlType.ProgrammaticName -eq "ControlType.Window") {
                        $dlg = $el
                        break
                    }
                }
                if ($null -ne $dlg) { break }
            }
        }
        if ($null -ne $dlg) {
            [void]$steps.Add([ordered]@{ step = "select_config_dialog_found"; title = $dlg.Current.Name })
            if (-not $dryRun) {
                [void][CatStudioOnlineLogWin32]::SetForegroundWindow([IntPtr]$dlg.Current.NativeWindowHandle)
            }
            $selectResult = Select-GenericTargetOnline $dlg
            [void]$steps.Add([ordered]@{ step = "select_config_online"; result = $selectResult })
            $ok = $null
            $all = $dlg.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
            foreach ($el in $all) {
                if ($el.Current.Name -match "^(OK|确定)$") {
                    $ok = $el
                    break
                }
            }
            if ($null -ne $ok) {
                [void]$steps.Add([ordered]@{ step = "ok_button"; name = $ok.Current.Name })
                if (-not $dryRun) { [void](Click-ButtonNative $ok); Start-Sleep -Milliseconds 1800 }
            } elseif (-not $dryRun) {
                [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
                Start-Sleep -Milliseconds 1200
            }
            break
        }
        Start-Sleep -Milliseconds 500
    }
}

$proc = Get-Process CATStudio -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Sort-Object StartTime -Descending |
    Select-Object -First 1
if ($null -eq $proc) {
    New-Result "NO_PROCESS" "CATStudio main window was not found" @{ steps = $steps }
    exit 0
}

$hwnd = [IntPtr]$proc.MainWindowHandle
if (-not $dryRun) {
    [void][CatStudioOnlineLogWin32]::ShowWindowAsync($hwnd, 9)
    [void][CatStudioOnlineLogWin32]::SetForegroundWindow($hwnd)
}
Start-Sleep -Milliseconds 400
$main = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
$filterReport = [ordered]@{ requested = $applyFilter; strict = $strictFilter; patterns = $filterPatterns; openFilter = $null; matched = @(); changed = @(); skipped = @(); errors = @() }

if ($applyFilter) {
    $openFilterResult = Open-LogViewerFilter $hwnd
    $filterReport.openFilter = $openFilterResult
    [void]$steps.Add([ordered]@{ step = "open_logviewer_filter"; result = $openFilterResult })
    Start-Sleep -Milliseconds 300
    $all = $main.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($el in $all) {
        $name = $el.Current.Name
        if ([string]::IsNullOrWhiteSpace($name)) { continue }
        $type = $el.Current.ControlType.ProgrammaticName
        if ($type -notmatch "(CheckBox|TreeItem)") { continue }
        $upper = $name.ToUpperInvariant()
        $wanted = $false
        foreach ($p in $filterPatterns) {
            if ($upper -like ("*" + $p.ToUpperInvariant() + "*")) {
                $wanted = $true
                break
            }
        }
        if ($wanted) {
            $res = Set-Toggle $el $true
            $entry = [ordered]@{ name = $name; type = $type; result = $res }
            $filterReport.matched += $entry
            if ($res.changed) { $filterReport.changed += $entry }
        } elseif ($strictFilter -and $name -notmatch "^(All|全部|Expand/Collapse All)$") {
            $res = Set-Toggle $el $false
            if ($res.changed -or $res.error) {
                $filterReport.changed += [ordered]@{ name = $name; type = $type; result = $res }
            }
        }
    }
}

$finalStatus = "OK"
$finalMessage = "CATStudio online LogViewer preparation completed"
if ($applyFilter -and $filterReport.matched.Count -eq 0) {
    $finalStatus = "FILTER_NOT_APPLIED"
    $finalMessage = "CATStudio LogViewer is ready, but the right-side filter tree did not expose selectable log items"
}

New-Result $finalStatus $finalMessage @{
    processId = $proc.Id
    title = $proc.MainWindowTitle
    dryRun = $dryRun
    steps = $steps
    filter = $filterReport
}
"""
    replacements = {
        "__CONFIG_NAME__": json.dumps(config_name),
        "__CONFIG_FILE__": json.dumps(config_file),
        "__DRY_RUN__": "$true" if dry_run else "$false",
        "__SELECT_ONLINE__": "$true" if select_online else "$false",
        "__APPLY_FILTER__": "$true" if apply_filter else "$false",
        "__STRICT_FILTER__": "$true" if strict_filter else "$false",
        "__FILTER_PATTERNS__": pattern_ps,
        "__TIMEOUT_SEC__": str(timeout_sec),
        "__CONFIG_DIALOG_WAIT_SEC__": str(config_dialog_wait_sec),
    }
    for key, value in replacements.items():
        script = script.replace(key, value)
    result, data = run_powershell(script, timeout=timeout_sec + 10)
    if data is not None:
        if apply_filter:
            open_filter = None
            if isinstance(data.get("filter"), dict):
                open_filter = data["filter"].get("openFilter")
            native_filter = apply_treeview_filter_native(
                filter_patterns,
                strict_filter=strict_filter,
                dry_run=dry_run,
                timeout_sec=timeout_sec,
            )
            if open_filter is not None:
                native_filter["openFilter"] = open_filter
            data["nativeFilter"] = native_filter
            if native_filter.get("status") == "OK":
                data["status"] = "OK"
                data["message"] = "CATStudio online LogViewer preparation completed"
                data["filter"] = native_filter
            elif data.get("status") == "OK":
                data["status"] = native_filter.get("status", "FILTER_NOT_APPLIED")
                data["message"] = native_filter.get("message", data.get("message"))
                data["filter"] = native_filter
        return data
    return {"status": "ERROR", "error": "ui automation did not return JSON", "process": result}


def status(args):
    root = args.get("catstudioRoot") or DEFAULT_CATSTUDIO_ROOT
    project_root = args.get("projectRoot") or DEFAULT_PROJECT_ROOT
    paths = catstudio_paths(root)
    txt_db = args.get("txtDbPath") or find_default_txt_db(project_root)
    return {
        "catstudio": paths,
        "processes": get_catstudio_processes(),
        "defaultTxtDb": txt_db,
        "defaultTxtDbExists": bool(txt_db and os.path.isfile(txt_db)),
        "onlineConfig": read_online_config(root, args.get("configFile") or DEFAULT_CONFIG_FILE),
        "latestLogs": latest_logs(paths["binLogs"], 5),
    }


def prepare(args):
    root = args.get("catstudioRoot") or DEFAULT_CATSTUDIO_ROOT
    project_root = args.get("projectRoot") or DEFAULT_PROJECT_ROOT
    txt_db = args.get("txtDbPath") or find_default_txt_db(project_root)
    if not txt_db:
        return {"status": "ERROR", "error": "no .mdb.txt found under project out/product", "projectRoot": norm(project_root)}
    dry_run = bool(args.get("dryRun", False))
    result = {
        "txtDbPath": norm(txt_db),
        "configBefore": read_online_config(root, args.get("configFile") or DEFAULT_CONFIG_FILE),
    }
    if args.get("applyConfig", True):
        result["configUpdate"] = update_online_config(root, txt_db, args.get("configFile") or DEFAULT_CONFIG_FILE, dry_run=dry_run)
    else:
        result["configUpdate"] = {"status": "SKIPPED", "reason": "applyConfig=false"}
    if args.get("startCatstudio", True):
        result["start"] = start_catstudio(root, dry_run=dry_run)
    else:
        result["start"] = {"status": "SKIPPED", "reason": "startCatstudio=false"}
    if dry_run and result["start"].get("status") == "DRY_RUN":
        result["ui"] = {"status": "SKIPPED", "reason": "dryRun without existing CATStudio process"}
    else:
        ui_args = dict(args)
        ui_args["_catstudioStartStatus"] = result["start"].get("status")
        result["ui"] = automate_catstudio_ui(ui_args)
    result["configAfter"] = read_online_config(root, args.get("configFile") or DEFAULT_CONFIG_FILE)
    result["postStatus"] = status(args)
    result["status"] = "OK" if result["ui"].get("status") in ("OK", "NO_PROCESS") else result["ui"].get("status", "UNKNOWN")
    return result


def call_tool(name, args):
    args = args or {}
    if name == "catstudio_online_log_status":
        return status(args)
    if name == "catstudio_prepare_online_log_viewer":
        return prepare(args)
    raise ValueError("Unknown tool: %s" % name)


def content_result(payload, is_error=False):
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}], "isError": bool(is_error)}


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
        try:
            return content_result(call_tool(params.get("name"), params.get("arguments") or {}))
        except Exception as exc:
            return content_result({"error": str(exc), "traceback": traceback.format_exc()}, is_error=True)
    if method in ["ping", "notifications/initialized"]:
        return {}
    if method == "resources/list":
        return {"resources": []}
    if method == "prompts/list":
        return {"prompts": []}
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
    return json.loads(stdin.read(length).decode("utf-8"))


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


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print(json.dumps({"server": SERVER_NAME, "tools": [t["name"] for t in TOOLS], "status": status({})}, ensure_ascii=False, indent=2))
        return
    if len(sys.argv) > 2 and sys.argv[1] == "--tool":
        name = sys.argv[2]
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        print(json.dumps(call_tool(name, args), ensure_ascii=False, indent=2))
        return
    serve()


if __name__ == "__main__":
    main()
