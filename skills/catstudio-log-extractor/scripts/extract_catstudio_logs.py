#!/usr/bin/env python3
"""
Extract CATStudio DIAG records from a CATStudio zip, extracted folder, or .icl.

The script is designed for AI triage. MMI/LOG keeps the compact text format used
for application debugging. Other profiles keep category metadata, DB format
strings, printable payload previews, and optional hex without trying to fully
emulate CATStudio's proprietary struct renderers.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import struct
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


TICKS_PER_SECOND = 32768
MAX_RECORD_PAYLOAD = 8 * 1024 * 1024
CACHE_VERSION = 1
DEFAULT_ID_MAP = {
    (57, 9603): ("MMI", "LOG", "uartCfgGetSetting", 'diagPrintf("%s ",logger_buffer)', "builtin"),
    (57, 9604): ("MMI", "LOG", "DUMP", 'diagPrintf("%s ",logger_buffer)', "builtin"),
    (57, 9605): ("MMI", "LOG", "uartlog", 'diagPrintf("%s ",logger_buffer)', "builtin"),
    (57, 9607): ("MMI", "LOG", "fatallog", 'diagPrintf("%s ",logger_buffer)', "builtin"),
}


PROFILE_RULES = {
    "mmi": {
        "description": "Device0 DIAG MMI/LOG text only",
        "includes": [("MMI", "LOG", None)],
        "terms": [],
    },
    "memory": {
        "description": "MMI plus memory and CPU/memory-pressure hints",
        "includes": [("MMI", "LOG", None), ("Csw_mem", None, None)],
        "terms": [
            "mem",
            "memory",
            "malloc",
            "alloc",
            "free",
            "heap",
            "stack",
            "available memory",
            "cpuusageinfo",
        ],
    },
    "system": {
        "description": "MMI plus platform, power, CPU, dump, reset, suspend hints",
        "includes": [("MMI", "LOG", None), ("PM", None, None), ("SW_PLAT", "Log", None)],
        "terms": [
            "cpuusageinfo",
            "freqchange",
            "dump_start",
            "dump_end",
            "reset",
            "reboot",
            "power",
            "sleep",
            "suspend",
            "resume",
            "wakeup",
            "watchdog",
        ],
    },
    "network": {
        "description": "MMI plus LTE/RRC/NAS/SIM/WiFi/MIFI/LWIP/AT/GPS/location traces",
        "includes": [
            ("MMI", "LOG", None),
            ("LTE_PS", None, None),
            ("PS_3G", None, None),
            ("PS_4G", None, None),
            ("PSNAS", None, None),
            ("PS_RR", None, None),
            ("LTE", None, None),
            ("RRC", None, None),
            ("USIMLOG", None, None),
            ("SAC", None, None),
            ("WIFI", None, None),
            ("MIFI", None, None),
            ("PCAC", None, None),
            ("ATCMD", None, None),
            ("ATCommand", None, None),
            ("GPS", None, None),
        ],
        "terms": ["location", "gps", "wifi", "lte", "rrc", "nas", "sim", "pdp", "apn", "socket", "dns"],
    },
    "crash": {
        "description": "MMI plus fatal/assert/reset/watchdog/dump/error hints",
        "includes": [("MMI", "LOG", None), ("Csw_mem", None, None), ("SW_PLAT", "Log", None)],
        "terms": [
            "fatal",
            "assert",
            "panic",
            "exception",
            "watchdog",
            "hardfault",
            "reset",
            "reboot",
            "dump",
            "fail",
            "error",
            "available memory",
        ],
    },
    "all": {
        "description": "Every recognized DIAG record; can be very large",
        "includes": [("*", None, None)],
        "terms": [],
    },
    "custom": {
        "description": "Only --include/--keyword/--cat filters",
        "includes": [],
        "terms": [],
    },
}

DEFAULT_FAST_KEYWORDS = [
    "recv message",
    "Received",
    "TXT",
    "CHAT1",
    "WeChat",
    "GPS",
    "location",
    "LBS",
    "fatal",
    "assert",
    "reset",
    "watchdog",
    "error",
]


@dataclass(frozen=True)
class DbEntry:
    cat1: str
    cat2: str
    cat3: str
    fmt: str
    source: str


@dataclass(frozen=True)
class LogRecord:
    timestamp_offset: int
    data_offset: int
    index: str
    pc_time: str
    comm_time: str
    cat1: str
    cat2: str
    cat3: str
    module_id: int
    message_id: int
    packet_counter: int
    length: int
    payload: bytes
    db_format: str
    db_source: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract CATStudio logs by AI-triage profile from zip/folder/.icl input."
    )
    parser.add_argument("input", nargs="?", help="CATStudio .zip, extracted folder, or .icl file")
    parser.add_argument(
        "--profile",
        action="append",
        choices=sorted(PROFILE_RULES),
        help="Extraction profile. Can be repeated. Default: mmi, or custom when only custom filters are used.",
    )
    parser.add_argument("-o", "--output", help="Output file for one profile, or output directory for multiple profiles.")
    parser.add_argument("--output-dir", help="Output directory. Overrides directory behavior of --output.")
    parser.add_argument("--summary", action="store_true", help="Also write observed category summary TSV.")
    parser.add_argument(
        "--evidence-pack",
        action="store_true",
        help="Write mmi/crash/network/memory/system outputs, category summary, and an AI triage _evidence.md.",
    )
    parser.add_argument(
        "--fast-evidence",
        action="store_true",
        help="Fast first-pass triage: write mmi, summary, evidence md, and keyword hits without broad profiles.",
    )
    parser.add_argument("--evidence-md", action="store_true", help="Also write an AI triage _evidence.md.")
    parser.add_argument("--evidence-limit", type=int, default=12, help="Records to show per profile in _evidence.md.")
    parser.add_argument("--include", action="append", default=[], help="Add category path: Cat1, Cat1/Cat2, Cat1/Cat2/Cat3. '*' is wildcard.")
    parser.add_argument("--keyword", action="append", default=[], help="Add records matching term in category, DB format, or payload preview.")
    parser.add_argument(
        "--require-keyword",
        action="append",
        default=[],
        help="Narrow selected records to those matching this term. Can be repeated.",
    )
    parser.add_argument("--cat1", help="Legacy custom Cat1 filter, e.g. MMI")
    parser.add_argument("--cat2", help="Legacy custom Cat2 filter, e.g. LOG")
    parser.add_argument("--cat3", help="Legacy custom Cat3 filter, e.g. uartlog")
    parser.add_argument("--year-start", type=int, default=2020, help="First PC timestamp year to scan, default: 2020")
    parser.add_argument("--year-end", type=int, default=2035, help="Last PC timestamp year to scan, default: 2035")
    parser.add_argument("--hex-limit", type=int, default=96, help="Bytes of payload hex to keep in extended output. 0 omits hex.")
    parser.add_argument("--full-hex", action="store_true", help="Keep full payload hex in extended output. Can make files large.")
    parser.add_argument("--extended", action="store_true", help="Use extended columns even for mmi profile.")
    parser.add_argument("--max-records", type=int, help="Stop after this many records per profile.")
    parser.add_argument("--no-cache", action="store_true", help="Disable fast-evidence output cache reuse.")
    parser.add_argument("--list-profiles", action="store_true", help="Print available profiles and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_profiles:
        for name in sorted(PROFILE_RULES):
            print(f"{name}: {PROFILE_RULES[name]['description']}")
        return 0

    if not args.input:
        print("Input is required unless --list-profiles is used.", file=sys.stderr)
        return 2

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input does not exist: {input_path}", file=sys.stderr)
        return 2

    custom_includes = parse_custom_includes(args)
    profiles = choose_profiles(args, custom_includes)
    output_paths = resolve_output_paths(input_path, args, profiles)
    if use_fast_cache(args) and cached_outputs_valid(input_path, args, profiles, output_paths):
        for profile in profiles:
            print(f"Using cached {profile}: {output_paths[profile]}")
        if should_write_summary(args):
            print(f"Using cached summary: {summary_path(input_path, args)}")
        if should_write_evidence(args):
            print(f"Using cached evidence: {evidence_path(input_path, args)}")
        return 0

    blob, id_map, icl_name = read_input(input_path)
    outputs = open_outputs(output_paths, profiles, args, input_path, icl_name)
    summary_counts: Dict[Tuple[str, str, str, int, int, str, str], int] = {}
    profile_counts = {profile: 0 for profile in profiles}
    evidence_records: Dict[str, List[LogRecord]] = {profile: [] for profile in profiles}
    keyword_records: List[Tuple[str, LogRecord]] = []
    hit_terms = keyword_hit_terms(args)

    try:
        for record in iter_records(blob, id_map, args.year_start, args.year_end):
            summary_key = (
                record.cat1,
                record.cat2,
                record.cat3,
                record.module_id,
                record.message_id,
                record.db_source,
                record.db_format,
            )
            summary_counts[summary_key] = summary_counts.get(summary_key, 0) + 1

            for profile in profiles:
                profile_keywords = [] if args.fast_evidence and profile != "custom" else args.keyword
                if args.max_records is not None and profile_counts[profile] >= args.max_records:
                    continue
                if not record_matches_profile(record, profile, custom_includes, profile_keywords):
                    continue
                if args.require_keyword and not record_matches_terms(record, args.require_keyword, include_payload=True):
                    continue
                if args.fast_evidence and profile != "mmi" and hit_terms and not record_matches_terms(
                    record, hit_terms, include_payload=True
                ):
                    continue
                write_record(outputs[profile], record, legacy_mmi_output(profile, args, custom_includes), args)
                profile_counts[profile] += 1
                if len(evidence_records[profile]) < args.evidence_limit:
                    evidence_records[profile].append(record)
                if hit_terms and len(keyword_records) < args.evidence_limit * 2:
                    if record_matches_terms(record, hit_terms, include_payload=True):
                        keyword_records.append((profile, record))
    finally:
        for handle in outputs.values():
            handle.close()

    if should_write_summary(args):
        write_summary(summary_path(input_path, args), summary_counts)
    if should_write_evidence(args):
        write_evidence_md(
            evidence_path(input_path, args),
            input_path,
            icl_name,
            profiles,
            output_paths,
            profile_counts,
            summary_counts,
            evidence_records,
            keyword_records,
            args,
        )
    if use_fast_cache(args):
        write_cache_meta(input_path, args, profiles, output_paths)

    for profile in profiles:
        print(f"Wrote {profile_counts[profile]} records [{profile}]: {output_paths[profile]}")
    if should_write_summary(args):
        print(f"Wrote summary: {summary_path(input_path, args)}")
    if should_write_evidence(args):
        print(f"Wrote evidence: {evidence_path(input_path, args)}")
    return 0


def choose_profiles(args: argparse.Namespace, custom_includes: Sequence[Tuple[Optional[str], Optional[str], Optional[str]]]) -> List[str]:
    if args.evidence_pack and not args.profile:
        return ["mmi", "crash", "network", "memory", "system"]
    if args.fast_evidence and not args.profile:
        return ["mmi"]
    if args.profile:
        return dedupe(args.profile)
    if custom_includes or args.keyword:
        return ["custom"]
    return ["mmi"]


def should_write_summary(args: argparse.Namespace) -> bool:
    return bool(args.summary or args.evidence_pack or args.fast_evidence)


def should_write_evidence(args: argparse.Namespace) -> bool:
    return bool(args.evidence_md or args.evidence_pack or args.fast_evidence)


def keyword_hit_terms(args: argparse.Namespace) -> List[str]:
    terms = list(args.keyword) + list(args.require_keyword)
    if args.fast_evidence and not terms:
        terms = list(DEFAULT_FAST_KEYWORDS)
    return dedupe(terms)


def use_fast_cache(args: argparse.Namespace) -> bool:
    return bool(args.fast_evidence and not args.no_cache)


def cached_outputs_valid(
    input_path: Path,
    args: argparse.Namespace,
    profiles: Sequence[str],
    output_paths: Dict[str, Path],
) -> bool:
    meta_path = cache_meta_path(input_path, args)
    if not meta_path.exists():
        return False

    try:
        with meta_path.open("r", encoding="utf-8") as handle:
            meta = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return False

    if meta.get("signature") != cache_signature(input_path, args, profiles):
        return False

    return all(path.exists() for path in expected_artifact_paths(input_path, args, output_paths))


def write_cache_meta(
    input_path: Path,
    args: argparse.Namespace,
    profiles: Sequence[str],
    output_paths: Dict[str, Path],
) -> None:
    meta_path = cache_meta_path(input_path, args)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    artifacts = [str(path) for path in expected_artifact_paths(input_path, args, output_paths)]
    with meta_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            {
                "signature": cache_signature(input_path, args, profiles),
                "artifacts": artifacts,
            },
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")


def cache_meta_path(input_path: Path, args: argparse.Namespace) -> Path:
    return output_artifact_dir(input_path, args) / f"{safe_input_stem(input_path)}_catstudio_cache.json"


def expected_artifact_paths(input_path: Path, args: argparse.Namespace, output_paths: Dict[str, Path]) -> List[Path]:
    paths = list(output_paths.values())
    if should_write_summary(args):
        paths.append(summary_path(input_path, args))
    if should_write_evidence(args):
        paths.append(evidence_path(input_path, args))
    return paths


def cache_signature(input_path: Path, args: argparse.Namespace, profiles: Sequence[str]) -> Dict[str, object]:
    stat = input_path.stat()
    return {
        "input": str(input_path.resolve()),
        "cache_version": CACHE_VERSION,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "profiles": list(profiles),
        "include": list(args.include),
        "keyword": list(args.keyword),
        "require_keyword": list(args.require_keyword),
        "cat1": args.cat1,
        "cat2": args.cat2,
        "cat3": args.cat3,
        "year_start": args.year_start,
        "year_end": args.year_end,
        "hex_limit": args.hex_limit,
        "full_hex": bool(args.full_hex),
        "extended": bool(args.extended),
        "max_records": args.max_records,
        "evidence_limit": args.evidence_limit,
        "fast_evidence": bool(args.fast_evidence),
    }


def parse_custom_includes(args: argparse.Namespace) -> List[Tuple[Optional[str], Optional[str], Optional[str]]]:
    includes = [parse_include(value) for value in args.include]
    if args.cat1 or args.cat2 or args.cat3:
        includes.append((args.cat1 or "*", args.cat2, args.cat3))
    return includes


def parse_include(value: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    parts = [part.strip() for part in value.split("/")]
    if not 1 <= len(parts) <= 3:
        raise SystemExit(f"Bad --include value: {value}")
    parts += [None] * (3 - len(parts))
    return tuple(None if part == "" else part for part in parts)  # type: ignore[return-value]


def dedupe(values: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def resolve_output_paths(input_path: Path, args: argparse.Namespace, profiles: Sequence[str]) -> Dict[str, Path]:
    if args.output_dir:
        out_dir = Path(args.output_dir)
        return {profile: out_dir / default_output_name(input_path, profile) for profile in profiles}

    if args.output and len(profiles) == 1 and Path(args.output).suffix:
        return {profiles[0]: Path(args.output)}

    out_dir = Path(args.output) if args.output else input_path.parent
    return {profile: out_dir / default_output_name(input_path, profile) for profile in profiles}


def default_output_name(input_path: Path, profile: str) -> str:
    return f"{safe_input_stem(input_path)}_catstudio_{profile}.tsv"


def summary_path(input_path: Path, args: argparse.Namespace) -> Path:
    return output_artifact_dir(input_path, args) / f"{safe_input_stem(input_path)}_catstudio_summary.tsv"


def evidence_path(input_path: Path, args: argparse.Namespace) -> Path:
    return output_artifact_dir(input_path, args) / f"{safe_input_stem(input_path)}_evidence.md"


def output_artifact_dir(input_path: Path, args: argparse.Namespace) -> Path:
    if args.output_dir:
        return Path(args.output_dir)
    elif args.output and (not Path(args.output).suffix or args.profile and len(args.profile) > 1):
        return Path(args.output)
    elif args.output and Path(args.output).suffix:
        return Path(args.output).parent
    return input_path.parent


def safe_input_stem(input_path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", input_path.stem).strip("_")


def read_input(input_path: Path) -> Tuple[bytes, Dict[Tuple[int, int], DbEntry], str]:
    if input_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(input_path, "r") as zf:
            id_map = read_id_map_from_zip(zf)
            icl_name = choose_icl_entry(zf)
            if icl_name is None:
                raise SystemExit(f"No .icl file found in zip: {input_path}")
            return zf.read(icl_name), id_map, icl_name

    if input_path.is_dir():
        id_map = read_id_map_from_dir(input_path)
        icl_path = choose_icl_file(input_path)
        if icl_path is None:
            raise SystemExit(f"No .icl file found in directory: {input_path}")
        return icl_path.read_bytes(), id_map, str(icl_path)

    data = input_path.read_bytes()
    return data, {key: DbEntry(*value) for key, value in DEFAULT_ID_MAP.items()}, str(input_path)


def choose_icl_entry(zf: zipfile.ZipFile) -> Optional[str]:
    entries = [info for info in zf.infolist() if info.filename.lower().endswith(".icl")]
    if not entries:
        return None
    entries.sort(key=lambda info: info.file_size, reverse=True)
    return entries[0].filename


def choose_icl_file(root: Path) -> Optional[Path]:
    entries = [path for path in root.rglob("*.icl") if path.is_file()]
    if not entries:
        return None
    entries.sort(key=lambda path: path.stat().st_size, reverse=True)
    return entries[0]


def read_id_map_from_zip(zf: zipfile.ZipFile) -> Dict[Tuple[int, int], DbEntry]:
    id_map: Dict[Tuple[int, int], DbEntry] = {}
    for source, names in (
        ("Comm_DB", ("Device0/Comm_DB.txt", "Comm_DB.txt")),
        ("App_DB", ("Device0/App_DB.txt", "App_DB.txt")),
    ):
        for name in names:
            try:
                raw = zf.read(name)
            except KeyError:
                continue
            merge_id_map(id_map, read_id_map_from_db(raw, source))
            break
    return id_map or {key: DbEntry(*value) for key, value in DEFAULT_ID_MAP.items()}


def read_id_map_from_dir(root: Path) -> Dict[Tuple[int, int], DbEntry]:
    id_map: Dict[Tuple[int, int], DbEntry] = {}
    for source, name in (("Comm_DB", "Comm_DB.txt"), ("App_DB", "App_DB.txt")):
        paths = sorted(path for path in root.rglob(name) if path.is_file())
        if paths:
            merge_id_map(id_map, read_id_map_from_db(paths[0].read_bytes(), source))
    return id_map or {key: DbEntry(*value) for key, value in DEFAULT_ID_MAP.items()}


def merge_id_map(target: Dict[Tuple[int, int], DbEntry], source: Dict[Tuple[int, int], DbEntry]) -> None:
    for key, value in source.items():
        target.setdefault(key, value)


def read_id_map_from_db(raw: bytes, source: str) -> Dict[Tuple[int, int], DbEntry]:
    text = raw.decode("utf-8", errors="replace")
    result: Dict[Tuple[int, int], DbEntry] = {}
    for row in csv.reader(text.splitlines()):
        if len(row) < 7:
            continue
        try:
            module_id = int(row[0], 0)
            message_id = int(row[1], 0)
        except ValueError:
            continue
        fmt = ",".join(row[7:]).strip() if len(row) > 7 else ""
        result[(module_id, message_id)] = DbEntry(
            cat1=row[4].strip(),
            cat2=row[5].strip(),
            cat3=row[6].strip(),
            fmt=fmt,
            source=source,
        )
    return result


def iter_records(
    blob: bytes,
    id_map: Dict[Tuple[int, int], DbEntry],
    year_start: int,
    year_end: int,
) -> Iterator[LogRecord]:
    seen_offsets = set()
    for year in range(year_start, year_end + 1):
        needle = struct.pack("<H", year)
        pos = 0
        while True:
            pos = blob.find(needle, pos)
            if pos < 0:
                break
            if pos not in seen_offsets:
                seen_offsets.add(pos)
                record = parse_record_at(blob, pos, id_map)
                if record is not None:
                    yield record
            pos += 1


def parse_record_at(
    blob: bytes,
    timestamp_offset: int,
    id_map: Dict[Tuple[int, int], DbEntry],
) -> Optional[LogRecord]:
    if timestamp_offset + 20 > len(blob):
        return None

    fields = struct.unpack_from("<8H", blob, timestamp_offset)
    year, month, day_of_week, day, hour, minute, second, millisecond = fields
    if not (
        2000 <= year <= 2100
        and 1 <= month <= 12
        and 0 <= day_of_week <= 6
        and 1 <= day <= 31
        and 0 <= hour <= 23
        and 0 <= minute <= 59
        and 0 <= second <= 60
        and 0 <= millisecond <= 999
    ):
        return None

    length = struct.unpack_from("<I", blob, timestamp_offset + 16)[0]
    if length < 12 or length > MAX_RECORD_PAYLOAD:
        return None

    data_offset = timestamp_offset + 20
    data_end = data_offset + length
    if data_end > len(blob):
        return None

    packet = blob[data_offset:data_end]
    packet_counter = struct.unpack_from("<H", packet, 2)[0]
    module_id = struct.unpack_from("<H", packet, 4)[0]
    message_id = struct.unpack_from("<H", packet, 6)[0]
    entry = id_map.get((module_id, message_id))
    if entry is None:
        return None

    return LogRecord(
        timestamp_offset=timestamp_offset,
        data_offset=data_offset,
        index=read_catstudio_index(blob, timestamp_offset),
        pc_time=format_pc_time(year, month, day, hour, minute, second, millisecond),
        comm_time=format_comm_ticks(struct.unpack_from("<I", packet, 8)[0]),
        cat1=entry.cat1,
        cat2=entry.cat2,
        cat3=entry.cat3,
        module_id=module_id,
        message_id=message_id,
        packet_counter=packet_counter,
        length=length,
        payload=packet[12:],
        db_format=entry.fmt,
        db_source=entry.source,
    )


def read_catstudio_index(blob: bytes, timestamp_offset: int) -> str:
    marker_offset = timestamp_offset - 25
    marker = b"\xfe\x07\x00\x00"
    if marker_offset >= 0 and blob[marker_offset : marker_offset + 4] == marker:
        value = struct.unpack_from("<I", blob, marker_offset + 4)[0]
        return str(value + 1)

    search_start = max(0, timestamp_offset - 96)
    pos = blob.rfind(marker, search_start, timestamp_offset)
    if pos >= 0 and pos + 8 <= len(blob):
        value = struct.unpack_from("<I", blob, pos + 4)[0]
        if value < 10_000_000:
            return str(value + 2)
    return ""


def record_matches_profile(
    record: LogRecord,
    profile: str,
    custom_includes: Sequence[Tuple[Optional[str], Optional[str], Optional[str]]],
    custom_keywords: Sequence[str],
) -> bool:
    rules = PROFILE_RULES[profile]
    includes = list(rules["includes"]) + list(custom_includes)
    terms = list(rules["terms"]) + list(custom_keywords)
    if any(matches_include(record, include) for include in includes):
        return True
    if terms and record_matches_terms(record, terms, include_payload=False):
        return True
    if terms and is_text_record(record) and record_matches_terms(record, terms, include_payload=True):
        return True
    return False


def matches_include(record: LogRecord, include: Tuple[Optional[str], Optional[str], Optional[str]]) -> bool:
    values = (record.cat1, record.cat2, record.cat3)
    for actual, expected in zip(values, include):
        if expected is None:
            continue
        if expected == "*":
            continue
        if actual.lower() != expected.lower():
            return False
    return True


def record_matches_terms(record: LogRecord, terms: Sequence[str], include_payload: bool) -> bool:
    hay_parts = [record.cat1, record.cat2, record.cat3, record.db_format]
    if include_payload:
        hay_parts.append(decode_or_preview_payload(record.payload, text_preferred=is_text_record(record)))
    haystack = " ".join(hay_parts).lower()
    return any(term.lower() in haystack for term in terms)


def is_text_record(record: LogRecord) -> bool:
    return record.cat1 == "MMI" and record.cat2 == "LOG"


def open_outputs(
    output_paths: Dict[str, Path],
    profiles: Sequence[str],
    args: argparse.Namespace,
    source: Path,
    icl_name: str,
) -> Dict[str, object]:
    outputs = {}
    for profile in profiles:
        path = output_paths[profile]
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("w", encoding="utf-8", newline="\n")
        write_header(handle, profile, source, icl_name, legacy_mmi_output(profile, args, parse_custom_includes(args)))
        outputs[profile] = handle
    return outputs


def legacy_mmi_output(
    profile: str,
    args: argparse.Namespace,
    custom_includes: Sequence[Tuple[Optional[str], Optional[str], Optional[str]]],
) -> bool:
    return (
        profile == "mmi"
        and not args.extended
        and not custom_includes
        and (not args.keyword or args.fast_evidence)
        and not args.require_keyword
    )


def write_header(handle: object, profile: str, source: Path, icl_name: str, legacy: bool) -> None:
    handle.write(f"# Source: {source}\n")
    handle.write(f"# ICL: {icl_name}\n")
    handle.write(f"# Profile: {profile}\n")
    if legacy:
        handle.write("# Filter: Device 0 / DIAG / MMI / LOG\n")
        handle.write("Index\tPC Time\tComm Time\tCat1\tCat2\tCat3\tModuleID\tMessageID\tPacketCounter\tLength\tData\n")
    else:
        handle.write(
            "Index\tPC Time\tComm Time\tCat1\tCat2\tCat3\tModuleID\tMessageID\t"
            "PacketCounter\tLength\tDBSource\tPayloadType\tData\tDBFormat\tPayloadHex\n"
        )


def write_record(handle: object, record: LogRecord, legacy: bool, args: argparse.Namespace) -> None:
    if legacy:
        data = decode_log_text(record.payload)
        handle.write(
            f"{record.index}\t{record.pc_time}\t{record.comm_time}\t"
            f"{record.cat1}\t{record.cat2}\t{record.cat3}\t"
            f"{record.module_id}\t{record.message_id}\t{record.packet_counter}\t"
            f"{record.length}\t{data}\n"
        )
        return

    payload_type = "text" if is_text_record(record) else "binary"
    data = decode_or_preview_payload(record.payload, text_preferred=is_text_record(record))
    hex_limit = len(record.payload) if args.full_hex else args.hex_limit
    hex_text = payload_hex(record.payload, hex_limit)
    handle.write(
        f"{record.index}\t{record.pc_time}\t{record.comm_time}\t"
        f"{record.cat1}\t{record.cat2}\t{record.cat3}\t"
        f"{record.module_id}\t{record.message_id}\t{record.packet_counter}\t"
        f"{record.length}\t{record.db_source}\t{payload_type}\t"
        f"{data}\t{sanitize_field(record.db_format)}\t{hex_text}\n"
    )


def payload_hex(payload: bytes, limit: int = 96) -> str:
    if limit <= 0:
        return ""
    shown = payload[:limit]
    suffix = " ..." if len(payload) > limit else ""
    return shown.hex(" ") + suffix


def decode_log_text(payload: bytes) -> str:
    payload = payload.split(b"\x00", 1)[0].rstrip(b"\r\n")
    for encoding in ("utf-8", "gb18030"):
        try:
            text = payload.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = payload.decode("utf-8", errors="replace")
    return sanitize_field(text)


def decode_or_preview_payload(payload: bytes, text_preferred: bool) -> str:
    if text_preferred:
        return decode_log_text(payload)

    raw = payload.split(b"\x00", 1)[0] if b"\x00" in payload[:256] else payload[:256]
    for encoding in ("utf-8", "gb18030"):
        try:
            text = raw.decode(encoding)
            printable = sum(1 for ch in text if ch.isprintable() or ch in "\r\n\t")
            if text and printable / max(len(text), 1) > 0.85:
                return sanitize_field(text)
        except UnicodeDecodeError:
            pass

    preview = "".join(chr(byte) if 32 <= byte < 127 else "." for byte in payload[:160])
    return sanitize_field(preview)


def sanitize_field(text: str) -> str:
    return (
        text.replace("\t", " ")
        .replace("\r", r"\r")
        .replace("\n", r"\n")
        .strip()
    )


def format_pc_time(
    year: int, month: int, day: int, hour: int, minute: int, second: int, millisecond: int
) -> str:
    return f"{year % 100:02d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}.{millisecond:03d}"


def format_comm_ticks(ticks: int) -> str:
    total_us = round(ticks * 1_000_000 / TICKS_PER_SECOND)
    minutes, rem_us = divmod(total_us, 60_000_000)
    seconds, rem_us = divmod(rem_us, 1_000_000)
    millis, micros = divmod(rem_us, 1000)
    return f"{minutes}:{seconds:02d}.{millis:03d}.{micros:03d}"


def write_summary(path: Path, counts: Dict[Tuple[str, str, str, int, int, str, str], int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("Count\tCat1\tCat2\tCat3\tModuleID\tMessageID\tDBSource\tDBFormat\n")
        for (cat1, cat2, cat3, module_id, message_id, source, fmt), count in sorted(
            counts.items(), key=lambda item: item[1], reverse=True
        ):
            handle.write(
                f"{count}\t{cat1}\t{cat2}\t{cat3}\t{module_id}\t{message_id}\t"
                f"{source}\t{sanitize_field(fmt)}\n"
            )


def write_evidence_md(
    path: Path,
    source: Path,
    icl_name: str,
    profiles: Sequence[str],
    output_paths: Dict[str, Path],
    profile_counts: Dict[str, int],
    summary_counts: Dict[Tuple[str, str, str, int, int, str, str], int],
    evidence_records: Dict[str, List[LogRecord]],
    keyword_records: List[Tuple[str, LogRecord]],
    args: argparse.Namespace,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# CATStudio Evidence Pack\n\n")
        handle.write(f"- Source: `{source}`\n")
        handle.write(f"- ICL: `{icl_name}`\n")
        handle.write(f"- Profiles: `{', '.join(profiles)}`\n")
        if args.keyword:
            handle.write(f"- Keywords: `{', '.join(args.keyword)}`\n")
        elif args.fast_evidence:
            handle.write(f"- Fast keywords: `{', '.join(DEFAULT_FAST_KEYWORDS)}`\n")
        if args.require_keyword:
            handle.write(f"- Required keywords: `{', '.join(args.require_keyword)}`\n")
        handle.write("\n## Outputs\n\n")
        for profile in profiles:
            handle.write(f"- `{profile}`: {profile_counts.get(profile, 0)} records -> `{output_paths[profile]}`\n")
        if should_write_summary(args):
            handle.write(f"- `summary`: `{summary_path(source, args)}`\n")

        handle.write("\n## Top Categories\n\n")
        for (cat1, cat2, cat3, module_id, message_id, db_source, db_format), count in sorted(
            summary_counts.items(), key=lambda item: item[1], reverse=True
        )[:20]:
            handle.write(
                f"- {count} x `{cat1}/{cat2}/{cat3}` module={module_id} msg={message_id} "
                f"source=`{db_source}` fmt=`{sanitize_field(db_format)}`\n"
            )

        if keyword_records:
            handle.write("\n## Keyword Hits\n\n")
            for profile, record in keyword_records:
                handle.write(format_evidence_record(profile, record))

        handle.write("\n## Profile Timeline Samples\n\n")
        for profile in profiles:
            handle.write(f"### {profile}\n\n")
            records = evidence_records.get(profile, [])
            if not records:
                handle.write("- No matching records captured.\n\n")
                continue
            for record in records:
                handle.write(format_evidence_record(profile, record))
            handle.write("\n")

        handle.write("## Suggested Code Searches\n\n")
        suggestions = sorted(suggest_search_terms(profiles, evidence_records, keyword_records))
        if not suggestions:
            suggestions = ["MMI", "LOG", "alarm", "reset", "watchdog", "sim", "location"]
        for term in suggestions[:30]:
            handle.write(f"- `rg -n \"{term}\" <project-root>`\n")


def format_evidence_record(profile: str, record: LogRecord) -> str:
    data = decode_or_preview_payload(record.payload, text_preferred=is_text_record(record))
    data = data[:300] + ("..." if len(data) > 300 else "")
    return (
        f"- `{profile}` {record.pc_time} / {record.comm_time} "
        f"`{record.cat1}/{record.cat2}/{record.cat3}` "
        f"module={record.module_id} msg={record.message_id}: {data}\n"
    )


def suggest_search_terms(
    profiles: Sequence[str],
    evidence_records: Dict[str, List[LogRecord]],
    keyword_records: List[Tuple[str, LogRecord]],
) -> List[str]:
    terms = set()
    for profile in profiles:
        terms.update(PROFILE_RULES.get(profile, {}).get("terms", []))
    for _, record in keyword_records:
        terms.update(part for part in (record.cat1, record.cat2, record.cat3) if part)
        text = decode_or_preview_payload(record.payload, text_preferred=is_text_record(record))
        for match in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", text):
            terms.add(match)
    for records in evidence_records.values():
        for record in records[:3]:
            terms.update(part for part in (record.cat1, record.cat2, record.cat3) if part)
    return [term for term in terms if len(term) <= 64]


if __name__ == "__main__":
    raise SystemExit(main())
