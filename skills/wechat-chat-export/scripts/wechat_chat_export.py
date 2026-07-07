#!/usr/bin/env python3
"""Export visible/scroll-loadable WeChat desktop chat text.

This script intentionally works through the logged-in desktop UI and clipboard.
It does not read, decrypt, or inspect WeChat databases or process memory.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
from ctypes import wintypes
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Iterable


if os.name != "nt":
    raise SystemExit("wechat_chat_export.py currently supports Windows only.")


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

SW_RESTORE = 9
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002

VK_CONTROL = 0x11
VK_A = 0x41
VK_C = 0x43
VK_ESCAPE = 0x1B


user32.EnumWindows.argtypes = [
    ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM),
    wintypes.LPARAM,
]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.mouse_event.argtypes = [
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(ctypes.c_ulong),
]
user32.mouse_event.restype = None
user32.keybd_event.argtypes = [
    wintypes.BYTE,
    wintypes.BYTE,
    wintypes.DWORD,
    ctypes.POINTER(ctypes.c_ulong),
]
user32.keybd_event.restype = None
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalSize.restype = ctypes.c_size_t


class Window:
    def __init__(self, hwnd: int, title: str, class_name: str, rect: tuple[int, int, int, int]):
        self.hwnd = hwnd
        self.title = title
        self.class_name = class_name
        self.rect = rect

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    def point(self, x_ratio: float, y_ratio: float) -> tuple[int, int]:
        left, top, _, _ = self.rect
        return (left + int(self.width * x_ratio), top + int(self.height * y_ratio))

    def as_dict(self) -> dict[str, object]:
        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "class_name": self.class_name,
            "rect": self.rect,
        }


def last_error(prefix: str) -> OSError:
    return ctypes.WinError(ctypes.get_last_error(), prefix)


def get_window_text(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, len(buf))
    return buf.value


def get_class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, len(buf))
    return buf.value


def get_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return (rect.left, rect.top, rect.right, rect.bottom)


def enum_windows() -> list[Window]:
    windows: list[Window] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        title = get_window_text(hwnd).strip()
        class_name = get_class_name(hwnd).strip()
        rect = get_rect(hwnd)
        if not rect:
            return True
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        if width < 200 or height < 200:
            return True
        if title or class_name:
            windows.append(Window(hwnd, title, class_name, rect))
        return True

    if not user32.EnumWindows(callback, 0):
        raise last_error("EnumWindows failed")
    return windows


def is_wechat_candidate(window: Window, title_hint: str | None = None) -> bool:
    haystack = f"{window.title} {window.class_name}".lower()
    if title_hint and title_hint.lower() not in haystack:
        return False
    needles = [
        "wechat",
        "微信",
        "weixin",
        "wechatmainwndforpc",
        "txguifoundation",
        "wework",
        "企业微信",
        "wxwork",
    ]
    return any(needle.lower() in haystack for needle in needles)


def find_wechat_window(title_hint: str | None = None) -> Window:
    windows = enum_windows()
    candidates = [w for w in windows if is_wechat_candidate(w, title_hint)]
    if not candidates and title_hint:
        candidates = [w for w in windows if title_hint.lower() in w.title.lower()]
    if not candidates:
        raise SystemExit("No WeChat-like window found. Open WeChat and select the target chat first.")
    candidates.sort(key=lambda w: (("wechat" not in (w.title + w.class_name).lower()), -w.width * w.height))
    return candidates[0]


def focus_window(window: Window) -> None:
    user32.ShowWindow(window.hwnd, SW_RESTORE)
    time.sleep(0.2)
    user32.SetForegroundWindow(window.hwnd)
    time.sleep(0.5)


def set_cursor(x: int, y: int) -> None:
    if not user32.SetCursorPos(x, y):
        raise last_error("SetCursorPos failed")


def click(x: int, y: int, delay: float = 0.05) -> None:
    set_cursor(x, y)
    time.sleep(delay)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
    time.sleep(delay)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)
    time.sleep(delay)


def drag(start: tuple[int, int], end: tuple[int, int], steps: int = 32) -> None:
    set_cursor(*start)
    time.sleep(0.08)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
    time.sleep(0.1)
    sx, sy = start
    ex, ey = end
    for i in range(1, steps + 1):
        x = sx + int((ex - sx) * i / steps)
        y = sy + int((ey - sy) * i / steps)
        set_cursor(x, y)
        time.sleep(0.01)
    time.sleep(0.08)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)
    time.sleep(0.1)


def wheel(delta: int) -> None:
    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, None)
    time.sleep(0.1)


def key_down(vk: int) -> None:
    user32.keybd_event(vk, 0, 0, None)


def key_up(vk: int) -> None:
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, None)


def hotkey(*keys: int) -> None:
    for key in keys:
        key_down(key)
        time.sleep(0.02)
    for key in reversed(keys):
        key_up(key)
        time.sleep(0.02)
    time.sleep(0.15)


def clipboard_text() -> str:
    if not user32.OpenClipboard(None):
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text: str) -> None:
    encoded = text.encode("utf-16-le") + b"\x00\x00"
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
    if not handle:
        raise last_error("GlobalAlloc failed")
    ptr = kernel32.GlobalLock(handle)
    if not ptr:
        raise last_error("GlobalLock failed")
    try:
        ctypes.memmove(ptr, encoded, len(encoded))
    finally:
        kernel32.GlobalUnlock(handle)
    if not user32.OpenClipboard(None):
        raise last_error("OpenClipboard failed")
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            raise last_error("SetClipboardData failed")
        handle = None
    finally:
        user32.CloseClipboard()


def sha1_text(text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    return hashlib.sha1(normalized.encode("utf-8", errors="replace")).hexdigest()


TIME_RE = re.compile(
    r"^("
    r"\d{1,2}:\d{2}"
    r"|昨天\s*\d{1,2}:\d{2}"
    r"|前天\s*\d{1,2}:\d{2}"
    r"|星期[一二三四五六日天]\s*\d{1,2}:\d{2}"
    r"|\d{4}[/-]\d{1,2}[/-]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?"
    r"|\d{1,2}[/-]\d{1,2}\s+\d{1,2}:\d{2}"
    r")$"
)


def is_time_line(line: str) -> bool:
    return bool(TIME_RE.match(line.strip()))


def looks_like_sender(line: str) -> bool:
    value = line.strip()
    if not value or len(value) > 40:
        return False
    if is_time_line(value):
        return False
    if value.startswith(("http://", "https://", "@")):
        return False
    if any(ch in value for ch in "\t\r\n"):
        return False
    return True


def parse_messages(raw_text: str) -> list[dict[str, object]]:
    lines = [line.strip() for line in raw_text.replace("\r\n", "\n").split("\n")]
    lines = [line for line in lines if line]
    messages: list[dict[str, object]] = []
    current: dict[str, object] = {"time": None, "sender": None, "content_lines": []}
    expect_sender = False

    def flush() -> None:
        nonlocal current
        content_lines = current.get("content_lines") or []
        if content_lines or current.get("sender") or current.get("time"):
            messages.append(
                {
                    "time": current.get("time"),
                    "sender": current.get("sender"),
                    "content": "\n".join(str(x) for x in content_lines).strip(),
                }
            )
        current = {"time": None, "sender": None, "content_lines": []}

    for line in lines:
        if is_time_line(line):
            flush()
            current["time"] = line
            expect_sender = True
            continue
        if expect_sender and looks_like_sender(line):
            current["sender"] = line
            expect_sender = False
            continue
        current.setdefault("content_lines", []).append(line)
        expect_sender = False
    flush()

    cleaned: list[dict[str, object]] = []
    seen: set[str] = set()
    for message in messages:
        key = json.dumps(message, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(message)
    return cleaned


def default_output_dir() -> Path:
    root = Path.cwd() / "outputs"
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return root / f"wechat-chat-export-{stamp}"


def ensure_output_dir(path: Path | None) -> Path:
    out_dir = path or default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_outputs(out_dir: Path, raw_chunks: list[str], warnings: list[str], window: Window | None = None) -> None:
    raw_text = "\n\n--- capture boundary ---\n\n".join(chunk.strip() for chunk in raw_chunks if chunk.strip()).strip()
    messages = parse_messages(raw_text)

    (out_dir / "raw.txt").write_text(raw_text + ("\n" if raw_text else ""), encoding="utf-8")

    with (out_dir / "messages.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for index, message in enumerate(messages, start=1):
            payload = {"index": index, **message}
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

    with (out_dir / "messages.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["index", "time", "sender", "content"])
        writer.writeheader()
        for index, message in enumerate(messages, start=1):
            writer.writerow({"index": index, **message})

    md_lines = ["# WeChat Chat Export", ""]
    for index, message in enumerate(messages, start=1):
        title_parts = [f"## {index}"]
        if message.get("time"):
            title_parts.append(str(message["time"]))
        if message.get("sender"):
            title_parts.append(str(message["sender"]))
        md_lines.append(" - ".join(title_parts))
        md_lines.append("")
        md_lines.append(str(message.get("content") or "").strip() or "(empty)")
        md_lines.append("")
    (out_dir / "messages.md").write_text("\n".join(md_lines).rstrip() + "\n", encoding="utf-8")

    manifest = {
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "output_dir": str(out_dir),
        "raw_capture_count": len(raw_chunks),
        "parsed_message_count": len(messages),
        "warnings": warnings,
        "window": window.as_dict() if window else None,
        "files": ["raw.txt", "messages.jsonl", "messages.md", "messages.csv", "manifest.json"],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def pane_points(window: Window, args: argparse.Namespace) -> dict[str, tuple[int, int]]:
    return {
        "center": window.point((args.pane_left + args.pane_right) / 2, (args.pane_top + args.pane_bottom) / 2),
        "drag_start": window.point(args.pane_right, args.pane_bottom),
        "drag_end": window.point(args.pane_left, args.pane_top),
        "scroll": window.point((args.pane_left + args.pane_right) / 2, args.pane_top + 0.10),
    }


def capture_once(window: Window, args: argparse.Namespace) -> str:
    points = pane_points(window, args)
    click(*points["center"])
    hotkey(VK_ESCAPE)
    set_clipboard_text("")
    if args.select == "ctrl-a":
        click(*points["center"])
        hotkey(VK_CONTROL, VK_A)
    else:
        drag(points["drag_start"], points["drag_end"], steps=args.drag_steps)
    hotkey(VK_CONTROL, VK_C)
    time.sleep(args.copy_wait)
    return clipboard_text().strip()


def countdown(yes: bool) -> None:
    if yes:
        return
    print("This will focus WeChat, move the mouse, select text, copy clipboard data, and scroll upward.")
    print("Open the target WeChat chat first. Press Ctrl+C to cancel.")
    for value in [5, 4, 3, 2, 1]:
        print(f"Starting in {value}...")
        time.sleep(1)


def command_discover(args: argparse.Namespace) -> int:
    windows = enum_windows()
    if args.all:
        candidates = windows
    else:
        candidates = [w for w in windows if is_wechat_candidate(w, args.title)]
    if not candidates and not args.all:
        candidates = [w for w in windows if args.title and args.title.lower() in w.title.lower()]
    print(json.dumps([w.as_dict() for w in candidates], ensure_ascii=False, indent=2))
    return 0


def command_from_clipboard(args: argparse.Namespace) -> int:
    out_dir = ensure_output_dir(args.out_dir)
    text = clipboard_text()
    warnings = []
    if not text.strip():
        warnings.append("Clipboard did not contain Unicode text.")
    write_outputs(out_dir, [text], warnings)
    print(f"Wrote export: {out_dir}")
    return 0


def command_export(args: argparse.Namespace) -> int:
    window = find_wechat_window(args.title)
    countdown(args.yes)
    focus_window(window)
    chunks: list[str] = []
    seen_hashes: set[str] = set()
    warnings: list[str] = []
    repeated = 0
    points = pane_points(window, args)

    for index in range(1, args.cycles + 1):
        text = capture_once(window, args)
        digest = sha1_text(text) if text else ""
        if text and digest not in seen_hashes:
            chunks.append(text)
            seen_hashes.add(digest)
            repeated = 0
            print(f"[{index}/{args.cycles}] captured {len(text)} chars")
        else:
            repeated += 1
            print(f"[{index}/{args.cycles}] empty or duplicate capture")

        if repeated >= args.stop_after_repeats:
            warnings.append(f"Stopped after {repeated} repeated/empty captures.")
            break

        set_cursor(*points["scroll"])
        for _ in range(args.scroll_ticks):
            wheel(args.scroll_delta)
        time.sleep(args.scroll_wait)

    if not chunks:
        warnings.append("No text was captured. Try --select ctrl-a, adjust pane ratios, or use from-clipboard.")

    out_dir = ensure_output_dir(args.out_dir)
    write_outputs(out_dir, list(reversed(chunks)) if args.oldest_first else chunks, warnings, window)
    print(f"Wrote export: {out_dir}")
    return 0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def ratio(value: str) -> float:
    parsed = float(value)
    if not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export visible WeChat desktop chat text.")
    sub = parser.add_subparsers(dest="command", required=True)

    discover = sub.add_parser("discover", help="List visible WeChat-like windows.")
    discover.add_argument("--title", help="Optional title/class substring.")
    discover.add_argument("--all", action="store_true", help="List all visible top-level windows.")
    discover.set_defaults(func=command_discover)

    from_clipboard = sub.add_parser("from-clipboard", help="Parse and export current clipboard text.")
    from_clipboard.add_argument("--out-dir", type=Path)
    from_clipboard.set_defaults(func=command_from_clipboard)

    export = sub.add_parser("export", help="Focus WeChat, copy visible chat text, scroll, and export.")
    export.add_argument("--title", help="Optional title/class substring for choosing the WeChat window.")
    export.add_argument("--out-dir", type=Path)
    export.add_argument("--cycles", type=positive_int, default=60)
    export.add_argument("--select", choices=["drag", "ctrl-a"], default="drag")
    export.add_argument("--yes", action="store_true", help="Skip safety countdown.")
    export.add_argument("--oldest-first", action=argparse.BooleanOptionalAction, default=True)
    export.add_argument("--pane-left", type=ratio, default=0.39)
    export.add_argument("--pane-top", type=ratio, default=0.08)
    export.add_argument("--pane-right", type=ratio, default=0.98)
    export.add_argument("--pane-bottom", type=ratio, default=0.88)
    export.add_argument("--drag-steps", type=positive_int, default=34)
    export.add_argument("--copy-wait", type=float, default=0.4)
    export.add_argument("--scroll-wait", type=float, default=0.35)
    export.add_argument("--scroll-ticks", type=positive_int, default=6)
    export.add_argument("--scroll-delta", type=int, default=720, help="Positive scrolls upward.")
    export.add_argument("--stop-after-repeats", type=positive_int, default=8)
    export.set_defaults(func=command_export)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
