#!/usr/bin/env python3
import argparse
import re
import shutil
import sys
from pathlib import Path


DEVICE_VER_RE = re.compile(r'(#define\s+yl_device_ver\s+")([^"]+)(")')
TIMESTAMP_RE = re.compile(r'_(\d{8}_\d{4})_')


def read_text_preserve_encoding(path: Path):
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"Unable to decode {path}")


def extract_device_ver(text: str) -> str:
    match = DEVICE_VER_RE.search(text)
    if not match:
        raise SystemExit("Could not find #define yl_device_ver")
    return match.group(2)


def update_device_ver_timestamp(text: str, release_time: str):
    match = DEVICE_VER_RE.search(text)
    if not match:
        raise SystemExit("Could not find #define yl_device_ver")

    old_ver = match.group(2)
    if not TIMESTAMP_RE.search(old_ver):
        raise SystemExit(f"Could not find YYYYMMDD_HHMM in yl_device_ver: {old_ver}")

    new_ver = TIMESTAMP_RE.sub(f"_{release_time}_", old_ver, count=1)
    new_text = text[: match.start(2)] + new_ver + text[match.end(2) :]
    return old_ver, new_ver, new_text


def validate_release_time(value: str):
    if not re.fullmatch(r"\d{8}_\d{4}", value):
        raise SystemExit("--release-time must be YYYYMMDD_HHMM")


def detect_product_dir(repo: Path) -> Path:
    out_product = repo / "out" / "product"
    preferred = out_product / "craneg_modem_watch"
    if preferred.is_dir():
        return preferred
    if not out_product.is_dir():
        raise SystemExit(f"Missing output directory: {out_product}")
    dirs = [p for p in out_product.iterdir() if p.is_dir()]
    if len(dirs) == 1:
        return dirs[0]
    names = "\n".join(f"  {p}" for p in dirs)
    raise SystemExit(f"Could not choose product directory. Pass --product-dir.\n{names}")


def choose_single(candidates, label, explicit=None):
    if explicit:
        path = Path(explicit).resolve()
        if not path.is_file():
            raise SystemExit(f"{label} does not exist: {path}")
        return path
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise SystemExit(f"No {label} candidate found")
    listing = "\n".join(
        f"  {p.name} ({p.stat().st_size} bytes, {p.stat().st_mtime:.0f})"
        for p in sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)
    )
    raise SystemExit(f"Multiple {label} candidates found. Pass an explicit path.\n{listing}")


def firmware_zip_candidates(product_dir: Path):
    result = []
    for path in product_dir.glob("*.zip"):
        lower = path.name.lower()
        if "source" in lower:
            continue
        if "release_upload" in path.parts:
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.stat().st_mtime, reverse=True)


def mdb_candidates(product_dir: Path):
    return sorted(product_dir.glob("*.mdb.txt"), key=lambda item: item.stat().st_mtime, reverse=True)


def copy_file(src: Path, dst: Path, dry_run: bool, overwrite: bool):
    if dry_run:
        suffix = " (destination exists)" if dst.exists() else ""
        print(f"DRY-RUN copy: {src} -> {dst}{suffix}")
        return
    if dst.exists() and not overwrite:
        raise SystemExit(f"Destination exists, pass --overwrite if intended: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Copied: {src} -> {dst}")


def main():
    parser = argparse.ArgumentParser(description="Prepare renamed Akq firmware release upload files.")
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument("--release-time", required=True, help="Release time: YYYYMMDD_HHMM")
    parser.add_argument("--yl-h", default="gui/lv_watch/lv_apps/yl/yl.h", help="Path to yl.h relative to repo")
    parser.add_argument("--product-dir", help="Build product directory")
    parser.add_argument("--firmware-zip", help="Explicit firmware zip to upload")
    parser.add_argument("--mdb", help="Explicit mdb txt file to upload")
    parser.add_argument("--readme", help="User-provided readme.txt to include. Omit to exclude readme from upload files.")
    parser.add_argument("--output-dir", help="Destination directory for renamed upload files")
    parser.add_argument("--no-update-yl", action="store_true", help="Do not update yl.h")
    parser.add_argument("--update-yl-only", action="store_true", help="Update yl.h timestamp and exit before choosing build artifacts")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing destination files")
    args = parser.parse_args()

    validate_release_time(args.release_time)
    repo = Path(args.repo).resolve()
    yl_h = (repo / args.yl_h).resolve()
    if not yl_h.is_file():
        raise SystemExit(f"Missing yl.h: {yl_h}")

    text, encoding = read_text_preserve_encoding(yl_h)
    old_ver, new_ver, new_text = update_device_ver_timestamp(text, args.release_time)

    print(f"repo: {repo}")
    print(f"yl_h: {yl_h}")
    print(f"old yl_device_ver: {old_ver}")
    print(f"new yl_device_ver: {new_ver}")

    if not args.no_update_yl and old_ver != new_ver:
        if args.dry_run:
            print(f"DRY-RUN update yl.h timestamp using encoding {encoding}")
        else:
            yl_h.write_text(new_text, encoding=encoding)
            print(f"Updated yl.h timestamp using encoding {encoding}")

    if args.update_yl_only:
        print("update_yl_only: done")
        return

    product_dir = Path(args.product_dir).resolve() if args.product_dir else detect_product_dir(repo)
    if not product_dir.is_dir():
        raise SystemExit(f"Missing product directory: {product_dir}")

    firmware_zip = choose_single(firmware_zip_candidates(product_dir), "firmware zip", args.firmware_zip)
    mdb = choose_single(mdb_candidates(product_dir), "mdb txt", args.mdb)

    readme = Path(args.readme).resolve() if args.readme else None
    if readme and not readme.is_file():
        raise SystemExit(f"User-provided readme does not exist: {readme}")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else product_dir / "release_upload" / args.release_time
    target_zip = output_dir / f"{new_ver}.zip"
    target_mdb = output_dir / f"{new_ver}.mdb.txt"
    target_readme = output_dir / "readme.txt" if readme else None

    print(f"product_dir: {product_dir}")
    print(f"firmware_zip: {firmware_zip}")
    print(f"mdb: {mdb}")
    print(f"readme: {readme if readme else '(excluded; user did not provide readme)'}")
    print(f"output_dir: {output_dir}")

    copy_file(firmware_zip, target_zip, args.dry_run, args.overwrite)
    copy_file(mdb, target_mdb, args.dry_run, args.overwrite)
    if readme:
        copy_file(readme, target_readme, args.dry_run, args.overwrite)

    print("Upload these files:")
    print(target_zip)
    print(target_mdb)
    if target_readme:
        print(target_readme)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
