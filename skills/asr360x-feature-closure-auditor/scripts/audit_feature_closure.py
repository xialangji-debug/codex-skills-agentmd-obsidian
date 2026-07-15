#!/usr/bin/env python3
"""Read-only ASR360x feature-closure scanner with Markdown output."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_EXCLUDED_DIRS = {
    ".git", ".repo", "build", "out", "prebuilts", "external",
    "node_modules", "__pycache__",
}
TEXT_SUFFIXES = {
    ".c", ".cc", ".cpp", ".h", ".hh", ".hpp", ".inc", ".cmake",
    ".mk", ".txt", ".json", ".yml", ".yaml",
}
MAX_FILE_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class Hit:
    surface: str
    path: str
    line_no: int
    text: str
    kind: str
    guard: str = ""


@dataclass(frozen=True)
class Surface:
    key: str
    label: str


SURFACES = (
    Surface("build", "构建/CMake"),
    Surface("menu", "菜单/工模/UI"),
    Surface("init-task", "初始化/周期任务/事件"),
    Surface("protocol-link-pro", "协议 link/pro"),
    Surface("protocol-sender-cap", "协议 sender/cap"),
    Surface("id-nv", "ID/NV/枚举兼容项"),
    Surface("other", "其他命中"),
)


def run_git(repo: Path, *args: str) -> str:
    try:
        cp = subprocess.run(
            ["git", "-C", str(repo), *args], check=False,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            encoding="utf-8", errors="replace",
        )
    except OSError:
        return ""
    return cp.stdout.strip() if cp.returncode == 0 else ""


def git_fingerprint(repo: Path) -> dict[str, str]:
    root_text = run_git(repo, "rev-parse", "--show-toplevel")
    root = Path(root_text).resolve() if root_text else repo.resolve()
    branch = run_git(root, "branch", "--show-current") or "DETACHED/未识别"
    commit = run_git(root, "rev-parse", "--short=9", "HEAD") or "未识别"
    upstream = run_git(root, "rev-parse", "--abbrev-ref", "@{upstream}") or "未配置"
    dirty_lines = [line for line in run_git(root, "status", "--porcelain").splitlines() if line]
    ahead_behind = "未配置"
    if upstream != "未配置":
        counts = run_git(root, "rev-list", "--left-right", "--count", f"{upstream}...HEAD").split()
        if len(counts) == 2:
            ahead_behind = f"ahead {counts[1]} / behind {counts[0]}"
    return {
        "repository": str(root), "branch": branch, "commit": commit,
        "upstream": upstream, "ahead_behind": ahead_behind,
        "worktree": "clean" if not dirty_lines else f"dirty ({len(dirty_lines)} entries)",
    }


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None
    for encoding in ("utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def iter_source_files(repo: Path, extra_excludes: set[str]) -> Iterable[Path]:
    excluded = {name.casefold() for name in DEFAULT_EXCLUDED_DIRS | extra_excludes}
    try:
        cp = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-co", "--exclude-standard", "-z"],
            check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace",
        )
    except OSError:
        cp = None
    if cp is not None and cp.returncode == 0:
        for relative in sorted({item for item in cp.stdout.split("\0") if item}):
            path = repo / relative
            if any(part.casefold() in excluded for part in Path(relative).parts):
                continue
            lower = path.name.casefold()
            if path.is_file() and (lower in {"makefile", "kconfig"} or path.suffix.casefold() in TEXT_SUFFIXES):
                yield path
        return
    for root, dirs, files in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d.casefold() not in excluded)
        base = Path(root)
        for name in sorted(files):
            path = base / name
            lower = name.casefold()
            if lower in {"makefile", "kconfig"} or path.suffix.casefold() in TEXT_SUFFIXES:
                yield path


def split_feature_aliases(feature: str) -> list[str]:
    return [token.strip() for token in re.split(r"[/,，、;；\s]+", feature) if len(token.strip()) >= 2]


def unique_casefold(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        value = raw.strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def find_define(text: str, name: str) -> str:
    match = re.search(
        rf"^\s*#\s*define\s+{re.escape(name)}\s+([^/\r\n]+)", text, re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def variant_field(text: str, name: str) -> str:
    match = re.search(rf"^- `?{re.escape(name)}`?：`([^`]*)`", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def infer_variant(repo: Path, fingerprint: dict[str, str], files: Sequence[Path]) -> dict[str, str]:
    values = {"yl_device_name": "未识别", "yl_device_ver": "未识别", "yl_hw_ver": "未识别"}
    preferred = [repo / "gui/lv_watch/lv_apps/yl/yl.h"]
    preferred.extend(path for path in files if path.name.casefold() == "yl.h" and path not in preferred)
    for path in preferred:
        text = read_text(path)
        if text is None:
            continue
        for key in tuple(values):
            found = find_define(text, key)
            if found:
                values[key] = found.strip('"')
        if values["yl_device_ver"] != "未识别":
            break

    canonical_path = repo / ".codex-project" / "variant.md"
    canonical = read_text(canonical_path) if canonical_path.exists() else None
    if canonical:
        for key in tuple(values):
            current = variant_field(canonical, key)
            if current:
                values[key] = current

    identity = " ".join((fingerprint["branch"], values["yl_device_ver"], values["yl_hw_ver"]))
    chip_match = re.search(r"ASR(?:3601|3602)|(?<!\d)360[12](?!\d)", identity, re.IGNORECASE)
    chip = chip_match.group(0).upper() if chip_match else "未识别"
    if chip in {"3601", "3602"}:
        chip = "ASR" + chip
    os_name = "RTOS" if re.search(r"RTOS|ALIOS", identity, re.IGNORECASE) else "未识别"
    branch = fingerprint["branch"]
    protocol = "未识别"
    for marker, label in (("乐智", "乐智"), ("小程序", "XCX/小程序"), ("XCX", "XCX/小程序"), ("APP", "APP")):
        if marker.casefold() in branch.casefold():
            protocol = label
            break
    customer = "未识别"
    for marker in ("韫一", "阿科奇", "电信", "乐知", "乐智"):
        if marker in branch:
            customer = marker
            break

    build_params: list[str] = []
    make_text = read_text(repo / "Makefile") if (repo / "Makefile").exists() else None
    if make_text:
        for name in ("TARGET_OS", "PS_MODE", "CHIP_ID"):
            match = re.search(rf"^\s*{name}\s*(?:\?|:|\+)?=\s*([^#\r\n]+)", make_text, re.MULTILINE)
            if match:
                build_params.append(f"{name}={match.group(1).strip()}")
    if canonical:
        chip = variant_field(canonical, "CHIP_ID") or chip
        os_name = variant_field(canonical, "TARGET_OS") or os_name
        ps_mode = variant_field(canonical, "PS_MODE")
        protocol = variant_field(canonical, "协议") or protocol
        customer = variant_field(canonical, "客户/产品变体") or customer
        build_command = variant_field(canonical, "构建命令")
        canonical_build = ", ".join(filter(None, [f"CHIP_ID={chip}" if chip else "", f"TARGET_OS={os_name}" if os_name else "", f"PS_MODE={ps_mode}" if ps_mode else ""]))
        build_params = [build_command or canonical_build]
    return {
        **values, "chip": chip, "os": os_name, "protocol": protocol, "customer": customer,
        "build_params": ", ".join(build_params) if build_params else "未识别（以实际构建命令为准）",
        "fingerprint_source": str(canonical_path) if canonical else "live Git + yl.h + Makefile heuristic",
    }


def comment_only(line: str, keyword_re: re.Pattern[str]) -> bool:
    stripped = line.lstrip()
    if stripped.startswith(("//", "/*", "*")):
        return True
    slash = line.find("//")
    return slash >= 0 and keyword_re.search(line[:slash]) is None and keyword_re.search(line[slash:]) is not None


def classify_surfaces(relative: str, line: str) -> set[str]:
    path = relative.replace("\\", "/").casefold()
    name = path.rsplit("/", 1)[-1]
    lower = line.casefold()
    result: set[str] = set()
    if name in {"cmakelists.txt", "makefile", "kconfig"} or name.endswith((".cmake", ".mk")):
        result.add("build")
    if any(token in path for token in ("menu", "factory_mode", "ui_message")) or re.search(
        r"\b(icon_|watch_text_id_|create_event_cb|show_warn|activity)", lower,
    ):
        result.add("menu")
    if any(token in path for token in ("/yl_tool.", "/yl_main.", "/at_test.", "timer", "/task", "/init")) or re.search(
        r"\b(init_|task|timer|event|message|open\s*\(|close\s*\()", lower,
    ):
        result.add("init-task")
    if any(token in name for token in ("link", "_pro.")) or re.search(r"\b(message_recv|protocol|recv_|link_)", lower):
        result.add("protocol-link-pro")
    if any(token in name for token in ("sender", "_cap.")) or re.search(
        r"\b(sender|send_|package|upload|build_[a-z0-9_]*body)", lower,
    ):
        result.add("protocol-sender-cap")
    if any(token in path for token in ("/nvm/", "/nv/", "activity_id", "text_id")) or re.search(
        r"\b(nv_section_[a-z0-9_]+|watch_text_id_[a-z0-9_]+|app_[a-z0-9_]+|xcx_[a-z0-9_]+|activity_[a-z0-9_]*id)", lower,
    ):
        result.add("id-nv")
    return result or {"other"}


def directive_update(stripped: str, stack: list[str]) -> tuple[str, bool]:
    match = re.match(r"#\s*(if|ifdef|ifndef|elif|else|endif)\b\s*(.*)", stripped)
    if not match:
        return " && ".join(stack), False
    directive, expr = match.group(1), match.group(2).strip()
    current = " && ".join(stack)
    if directive in {"if", "ifdef", "ifndef"}:
        stack.append(expr if directive != "ifndef" else f"!defined({expr})")
        return " && ".join(stack), True
    if directive == "elif":
        if stack:
            stack[-1] = expr
        return " && ".join(stack), True
    if directive == "else":
        if stack:
            stack[-1] = f"else({stack[-1]})"
        return " && ".join(stack), True
    if directive == "endif":
        if stack:
            stack.pop()
        return current, True
    return current, True


def contains_guard(text: str, guards: Sequence[str]) -> bool:
    folded = text.casefold()
    return any(
        re.search(rf"(?<![a-z0-9_]){re.escape(guard.casefold())}(?![a-z0-9_])", folded)
        for guard in guards
    )


def alias_expression(alias: str) -> str:
    escaped = re.escape(alias)
    if re.fullmatch(r"[A-Za-z0-9_]{1,3}", alias):
        return rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    return escaped


def prefilter_files(repo: Path, files: Sequence[Path] | None, expression: str) -> Sequence[Path]:
    command = [
        "rg", "--files-with-matches", "--null", "--ignore-case", "--pcre2",
        "--regexp", expression,
    ]
    for suffix in sorted(TEXT_SUFFIXES):
        command.extend(["--glob", f"*{suffix}"])
    for name in sorted(DEFAULT_EXCLUDED_DIRS):
        command.extend(["--glob", f"!{name}/**"])
    command.extend(["--glob", "Makefile", "--glob", "Kconfig", str(repo)])
    try:
        cp = subprocess.run(
            command, check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace",
        )
    except OSError:
        return files if files is not None else list(iter_source_files(repo, set()))
    if cp.returncode not in (0, 1):
        return files if files is not None else list(iter_source_files(repo, set()))
    matches = [Path(raw).resolve() for raw in cp.stdout.split("\0") if raw]
    if files is None:
        return matches
    allowed = {path.resolve() for path in files}
    return [path for path in matches if path in allowed]


def scan(repo: Path, files: Sequence[Path] | None, aliases: Sequence[str], guards: Sequence[str]) -> tuple[list[Hit], dict[str, str]]:
    expression = "|".join(alias_expression(alias) for alias in sorted(aliases, key=len, reverse=True))
    keyword_re = re.compile(expression, re.IGNORECASE)
    hits: list[Hit] = []
    guard_values: dict[str, str] = {}
    for path in prefilter_files(repo, files, expression):
        text = read_text(path)
        if text is None or keyword_re.search(text) is None:
            continue
        relative = path.relative_to(repo).as_posix()
        stack: list[str] = []
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.lstrip()
            guard_expr, is_directive = directive_update(stripped, stack)
            if keyword_re.search(line) is None:
                continue
            define = re.match(r"#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s*([^/\r\n]*)", stripped)
            if define and contains_guard(define.group(1), guards):
                guard_values[define.group(1)] = define.group(2).strip() or "defined"
            if comment_only(line, keyword_re):
                kind = "commented"
            elif contains_guard(guard_expr, guards) or (is_directive and contains_guard(line, guards)) or (
                define is not None and contains_guard(define.group(1), guards)
            ):
                kind = "guarded"
            else:
                kind = "active"
            for surface in classify_surfaces(relative, line):
                hits.append(Hit(surface, relative, line_no, line.strip(), kind, guard_expr))
    return hits, guard_values


def status_for(surface: str, counts: dict[str, int], expected: str, compat_policy: str) -> str:
    active = counts.get("active", 0)
    guarded = counts.get("guarded", 0)
    commented = counts.get("commented", 0)
    if surface == "id-nv":
        if compat_policy == "retain":
            if active:
                return "compat-retained"
            if guarded:
                return "guarded"
            return "needs-review"
        if compat_policy == "remove":
            if active:
                return "present"
            return "removed" if commented or not guarded else "guarded"
        return "needs-review"
    if active:
        return "present"
    if guarded:
        return "guarded"
    return "removed" if expected == "removed" else "needs-review"


def md_escape(value: object) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def evidence_for(hits: Sequence[Hit], limit: int) -> str:
    if not hits:
        return "未发现关键词命中"
    ranked = sorted(hits, key=lambda h: ({"active": 0, "guarded": 1, "commented": 2}[h.kind], h.path, h.line_no))
    parts = []
    for hit in ranked[:limit]:
        snippet = hit.text if len(hit.text) <= 96 else hit.text[:93] + "..."
        parts.append(f"`{md_escape(hit.path)}:{hit.line_no}` {md_escape(snippet)}")
    if len(ranked) > limit:
        parts.append(f"另有 {len(ranked) - limit} 条")
    return "<br>".join(parts)


def render_report(
    feature: str, aliases: Sequence[str], guards: Sequence[str], expected: str,
    compat_policy: str, fingerprint: dict[str, str], variant: dict[str, str],
    hits: Sequence[Hit], guard_values: dict[str, str], evidence_limit: int,
) -> str:
    grouped: dict[str, list[Hit]] = defaultdict(list)
    for hit in hits:
        grouped[hit.surface].append(hit)
    rows: list[tuple[str, str, dict[str, int], str]] = []
    for surface in SURFACES:
        surface_hits = grouped.get(surface.key, [])
        counts: dict[str, int] = defaultdict(int)
        for hit in surface_hits:
            counts[hit.kind] += 1
        rows.append((
            surface.label, status_for(surface.key, counts, expected, compat_policy),
            counts, evidence_for(surface_hits, evidence_limit),
        ))
    blocking = [label for label, status, _, _ in rows if status in {"present", "needs-review"}]
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "# ASR360x 功能闭包审计", "", "## 审计输入", "",
        f"- 生成时间：`{md_escape(now)}`", f"- 功能：`{md_escape(feature)}`",
        f"- 期望：`{expected}`", f"- 兼容策略：`{compat_policy}`",
        f"- 关键词：{', '.join(f'`{md_escape(alias)}`' for alias in aliases)}",
        f"- 目标宏：{', '.join(f'`{md_escape(guard)}`' for guard in guards) if guards else '未指定'}",
        "", "## 变体指纹", "", "| 字段 | 值 |", "|---|---|",
        f"| repo | `{md_escape(fingerprint['repository'])}` |",
        f"| branch | `{md_escape(fingerprint['branch'])}` |",
        f"| short commit | `{md_escape(fingerprint['commit'])}` |",
        f"| upstream | `{md_escape(fingerprint['upstream'])}` |",
        f"| ahead/behind | `{md_escape(fingerprint['ahead_behind'])}` |",
        f"| worktree | `{md_escape(fingerprint['worktree'])}` |",
        f"| yl_device_name | `{md_escape(variant['yl_device_name'])}` |",
        f"| yl_device_ver | `{md_escape(variant['yl_device_ver'])}` |",
        f"| yl_hw_ver | `{md_escape(variant['yl_hw_ver'])}` |",
        f"| chip / OS | `{md_escape(variant['chip'])}` / `{md_escape(variant['os'])}` |",
        f"| protocol / customer | `{md_escape(variant['protocol'])}` / `{md_escape(variant['customer'])}` |",
        f"| build params | `{md_escape(variant['build_params'])}` |",
        f"| fingerprint source | `{md_escape(variant['fingerprint_source'])}` |",
        "", "## 功能闭包表", "",
        "| 环节 | 状态 | active | guarded | commented | 证据 |",
        "|---|---|---:|---:|---:|---|",
    ]
    for label, status, counts, evidence in rows:
        lines.append(
            f"| {label} | `{status}` | {counts.get('active', 0)} | {counts.get('guarded', 0)} | "
            f"{counts.get('commented', 0)} | {evidence} |"
        )
    lines.extend(["", "## 目标宏取值", ""])
    if guard_values:
        lines.extend(f"- `{md_escape(name)}` = `{md_escape(value)}`" for name, value in sorted(guard_values.items()))
    else:
        lines.append("- 未找到目标宏定义；确认宏来自编译参数还是其他配置头。")
    lines.extend([
        "", "## 状态定义", "",
        "- `present`：存在未受目标宏保护的有效命中。",
        "- `guarded`：源码仍保留，但受目标宏保护或统一开关显式关闭。",
        "- `removed`：该环节无有效命中或仅剩注释命中。",
        "- `compat-retained`：ID、NV 或协议枚举按兼容策略保留。",
        "- `needs-review`：证据不足或兼容项缺失，不能自动下结论。",
        "", "## 结论", "",
    ])
    if blocking:
        lines.append(f"- 需优先复核：{', '.join(blocking)}。")
    else:
        lines.append("- 未发现 `present` 或 `needs-review` 环节。")
    lines.extend([
        "- 本报告是只读静态扫描结果，不等同于编译、链接 map、真机或平台验证。",
        "- `removed` 依赖当前关键词集合；出现新别名时必须使用相同参数补扫。", "",
    ])
    return "\n".join(lines)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path, help="Git repository root")
    parser.add_argument("--feature", required=True, help="Human-readable feature name")
    parser.add_argument("--keyword", action="append", default=[], help="Repeatable literal feature alias")
    parser.add_argument("--guard", action="append", default=[], help="Repeatable preprocessor guard macro")
    parser.add_argument("--expected", choices=("removed", "present"), default="removed")
    parser.add_argument("--compat-policy", choices=("retain", "remove", "review"), default="retain")
    parser.add_argument("--exclude-dir", action="append", default=[], help="Additional directory basename to exclude")
    parser.add_argument("--evidence-limit", type=int, default=5)
    parser.add_argument("--output", type=Path, help="Write UTF-8 Markdown here; stdout otherwise")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        print(f"error: repository does not exist: {repo}", file=sys.stderr)
        return 2
    aliases = unique_casefold(args.keyword or split_feature_aliases(args.feature))
    if not aliases:
        print("error: provide --keyword or a feature name with a usable token", file=sys.stderr)
        return 2
    guards = unique_casefold(args.guard)
    fingerprint = git_fingerprint(repo)
    variant = infer_variant(repo, fingerprint, ())
    if args.exclude_dir:
        files: Sequence[Path] | None = list(iter_source_files(repo, set(args.exclude_dir)))
    else:
        files = None
    hits, guard_values = scan(repo, files, aliases, guards)
    report = render_report(
        args.feature, aliases, guards, args.expected, args.compat_policy,
        fingerprint, variant, hits, guard_values, max(1, args.evidence_limit),
    )
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8", newline="\n")
        print(output)
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
