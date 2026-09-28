#!/usr/bin/env python3
"""Prepare branch-bound build profiles from a repository-local durable store."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from asr360x_context import gather, read_yl

PROFILE_PATH = Path('.codex-project/asr3602-build-profile.json')


class StoreError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def read_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise StoreError(f'Cannot read profile record {path}: {exc}') from exc
    if not isinstance(value, dict):
        raise StoreError(f'Expected JSON object: {path}')
    return value


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, encoding='utf-8', errors='replace', timeout=30)
    if proc.returncode:
        raise StoreError(proc.stderr.strip())
    return proc.stdout.strip()


def store_root(repo: Path) -> Path:
    common = Path(git(repo, 'rev-parse', '--git-common-dir'))
    if not common.is_absolute():
        common = repo / common
    return common.resolve() / 'codex/build-profiles'


def live_binding(repo: Path) -> dict:
    yl = read_yl(repo)
    if any(value == '不可用' for value in yl.values()):
        raise StoreError('Missing product/hardware/version definitions in yl.h; cannot bind a build profile')
    branch = git(repo, 'branch', '--show-current')
    if not branch:
        branch = 'detached:' + git(repo, 'rev-parse', 'HEAD')
    version = yl['yl_device_ver']
    # Publication dates and release counters do not change the build family.
    family = re.split(r'_\d{8}_\d{4}_', version, maxsplit=1)[0]
    if family == version:
        family = re.split(r'_[FT]\d+$', version, maxsplit=1)[0]
    build_inputs = {}
    for relative in ('Makefile', 'CMakeLists.txt'):
        source = repo / relative
        if source.is_file():
            build_inputs[relative] = digest(source.read_bytes())
    return {
        'branch': branch, 'ylDeviceName': yl['yl_device_name'],
        'ylHwVer': yl['yl_hw_ver'], 'versionFamily': family,
        'buildInputs': build_inputs,
    }


def record_path(repo: Path, binding: dict) -> Path:
    key = digest(binding['branch'].encode('utf-8'))[:24]
    return store_root(repo) / 'records' / (key + '.json')


def atomic_write(path: Path, data: bytes) -> bool:
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + '.', suffix='.partial', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return True


@contextmanager
def record_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise StoreError(f'Profile record is being updated: {lock}; retry after the writer finishes') from exc
    try:
        os.write(fd, str(os.getpid()).encode('ascii'))
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def validate_profile(profile: dict, repo: Path) -> dict:
    from asr3602_build_profile import expand_adapter, validate_adapter
    expanded = expand_adapter(profile)
    validate_adapter(expanded, repo)
    return expanded


def assert_binding(expected: dict, actual: dict) -> None:
    differences = [key for key in actual if expected.get(key) != actual[key]]
    if differences:
        raise StoreError('Stored build profile does not match current identity: ' + ', '.join(differences))


def _profile_without_binding(profile: dict) -> dict:
    return {key: value for key, value in profile.items() if key != 'contextBinding'}


def load_record(path: Path, binding: dict, repo: Path) -> dict:
    record = read_object(path)
    assert_binding(record.get('binding', {}), binding)
    profile = record.get('profile')
    if not isinstance(profile, dict) or digest(encoded(profile)) != record.get('profileSha256'):
        raise StoreError(f'Profile record checksum mismatch: {path}')
    validate_profile(profile, repo)
    return record


def register(repo: Path, adapter: Path, evidence: str, *, write: bool = True) -> dict:
    if not evidence.strip():
        raise StoreError('Registration requires the source of the confirmed build parameters (--evidence)')
    binding = live_binding(repo)
    profile = _profile_without_binding(read_object(adapter))
    validate_profile(profile, repo)
    path = record_path(repo, binding)
    profile_hash = digest(encoded(profile))
    record = {
        'schemaVersion': 1, 'binding': binding, 'profile': profile,
        'profileSha256': profile_hash, 'evidence': evidence,
        'registeredAt': datetime.now(timezone.utc).isoformat(),
        'registeredCommit': git(repo, 'rev-parse', 'HEAD'),
    }
    target = repo / PROFILE_PATH
    changed = []
    if write:
        with record_lock(path):
            assert_binding(binding, live_binding(repo))
            if path.exists():
                previous = read_object(path)
                if previous.get('binding') == binding and previous.get('profileSha256') == profile_hash:
                    record = previous
                else:
                    history = path.parent.parent / 'history' / (digest(encoded(previous)) + '.json')
                    atomic_write(history, encoded(previous))
            if atomic_write(path, encoded(record)):
                changed.append(str(path))
            current = dict(profile, contextBinding=binding)
            if atomic_write(target, encoded(current)):
                changed.append(str(target))
    return {'status': 'REGISTERED' if write else 'WOULD_REGISTER', 'repo': str(repo), 'branch': binding['branch'], 'recordPath': str(path), 'adapterPath': str(target), 'changed': changed}


def prepare(repo: Path, adapter: Path | None = None, *, write: bool = True) -> dict:
    binding = live_binding(repo)
    target = adapter or repo / PROFILE_PATH
    path = record_path(repo, binding)
    current = read_object(target) if target.exists() else None
    selected = None
    origin = 'current'
    if current and current.get('contextBinding') == binding:
        validate_profile(current, repo)
        # A local edit must be deliberately re-registered; never silently choose between two truths.
        if path.exists():
            saved = load_record(path, binding, repo)
            if digest(encoded(_profile_without_binding(current))) != saved['profileSha256']:
                raise StoreError('Current profile differs from its registered record; review and register the intended update')
        else:
            raise StoreError('Bound profile has no durable source record; register it to restore the store')
        selected = current
    elif current and not current.get('contextBinding'):
        raise StoreError('Build profile has no confirmed branch binding; register it once with evidence')
    elif path.exists():
        if current and current.get('contextBinding'):
            previous_path = record_path(repo, current['contextBinding'])
            previous = read_object(previous_path) if previous_path.exists() else {}
            if digest(encoded(_profile_without_binding(current))) != previous.get('profileSha256'):
                raise StoreError('Previous branch profile has unregistered edits; preserve and register them before switching configuration')
        saved = load_record(path, binding, repo)
        selected = dict(saved['profile'], contextBinding=binding)
        origin = 'record'
    else:
        raise StoreError(f'No confirmed build profile for branch {binding["branch"]}; register exact build parameters once')
    changed = []
    if write:
        with record_lock(path):
            assert_binding(binding, live_binding(repo))
            latest = load_record(path, binding, repo)
            if latest['profileSha256'] != digest(encoded(_profile_without_binding(selected))):
                raise StoreError('Branch record changed during preparation; retry with the new record')
            current_now = read_object(target) if target.exists() else None
            if current_now != current:
                raise StoreError('Local profile changed during preparation; preserving the newer file')
            if atomic_write(target, encoded(selected)):
                changed.append(str(target))
    expanded = validate_profile(selected, repo)
    expanded_path = store_root(repo) / 'expanded' / (digest(encoded(expanded)) + '.json')
    if write:
        atomic_write(expanded_path, encoded(expanded))
    return {
        'status': 'READY', 'repo': str(repo), 'branch': binding['branch'],
        'recordPath': str(path), 'adapterPath': str(target), 'expandedPath': str(expanded_path),
        'source': origin, 'changed': changed, 'buildTarget': expanded['buildTarget'],
        'targetOs': expanded['targetOs'], 'psMode': expanded['psMode'], 'chipId': expanded['chipId'],
        'buildCommand': expanded['build']['command'],
    }


def expand_explicit(repo: Path, adapter: Path, *, write: bool = True) -> dict:
    """Normalize an explicitly selected adapter without selecting another branch record."""
    expanded = validate_profile(read_object(adapter), repo)
    if expanded.get('contextBinding'):
        assert_binding(expanded['contextBinding'], live_binding(repo))
    path = store_root(repo) / 'expanded' / (digest(encoded(expanded)) + '.json')
    if write:
        atomic_write(path, encoded(expanded))
    return {'status': 'EXPANDED', 'expandedPath': str(path), 'adapterPath': str(adapter)}


def release_path(repo: Path, branch: str, version: str) -> Path:
    return store_root(repo) / 'releases' / (digest((branch + '\n' + version).encode('utf-8')) + '.json')


def release_snapshot(repo: Path, adapter: Path, version: str, *, write: bool = True) -> dict:
    profile = read_object(adapter)
    validate_profile(profile, repo)
    binding = live_binding(repo)
    assert_binding(profile.get('contextBinding', {}), binding)
    actual = read_yl(repo)['yl_device_ver']
    if version != actual:
        raise StoreError(f'Release version differs from yl.h: {version} != {actual}')
    value = {'schemaVersion': 1, 'version': version, 'binding': binding,
             'commit': git(repo, 'rev-parse', 'HEAD'), 'profile': profile,
             'profileSha256': digest(encoded(profile)), 'kind': 'release-configuration'}
    header = (repo / 'gui/lv_watch/lv_apps/yl/yl.h').read_text(encoding='utf-8-sig', errors='replace')
    software = re.search(r'#define\s+yl_soft_ver\s+"([^"]+)"', header)
    value['softwareVersion'] = software.group(1) if software else ''
    path = release_path(repo, binding['branch'], version)
    if write:
        with record_lock(path):
            if path.exists() and read_object(path) != value:
                raise StoreError(f'Release configuration snapshot already exists with different content: {path}')
            atomic_write(path, encoded(value))
    return {'status': 'SNAPSHOT_SAVED' if write else 'WOULD_SAVE', 'path': str(path)}


def restore_version(repo: Path, version: str, *, write: bool = True) -> dict:
    binding = live_binding(repo)
    if not version or version != read_yl(repo)['yl_device_ver']:
        raise StoreError('Select the source checkout with the requested yl_device_ver before restoring its configuration')
    path = release_path(repo, binding['branch'], version)
    snapshot = read_object(path)
    assert_binding(snapshot.get('binding', {}), binding)
    profile = snapshot.get('profile')
    if not isinstance(profile, dict) or digest(encoded(profile)) != snapshot.get('profileSha256'):
        raise StoreError(f'Release configuration checksum mismatch: {path}')
    assert_binding(profile.get('contextBinding', {}), binding)
    validate_profile(profile, repo)
    target = repo / PROFILE_PATH
    if target.exists():
        current = read_object(target)
        previous_binding = current.get('contextBinding')
        if not previous_binding:
            raise StoreError('Local profile is unregistered; preserve and register it before restoring a version')
        previous = read_object(record_path(repo, previous_binding))
        if digest(encoded(_profile_without_binding(current))) != previous.get('profileSha256'):
            raise StoreError('Local profile has unregistered edits; preserving it before version restore')
    if not write:
        return {'status': 'WOULD_RESTORE', 'path': str(path), 'version': version}
    # Feed the validated immutable snapshot through the same registration path.
    expanded_path = store_root(repo) / 'expanded' / (digest(encoded(profile)) + '.json')
    atomic_write(expanded_path, encoded(profile))
    register(repo, expanded_path, 'Restored release configuration: ' + str(path))
    result = prepare(repo)
    result.update({'restoredVersion': version, 'releaseSnapshot': str(path)})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'register', 'check', 'expand', 'release-snapshot', 'restore-version', 'list'))
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--adapter', type=Path)
    parser.add_argument('--evidence', default='')
    parser.add_argument('--version')
    parser.add_argument('--json-out', type=Path)
    parser.add_argument('--read-only', action='store_true')
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    adapter = args.adapter.resolve() if args.adapter else repo / PROFILE_PATH
    try:
        if args.action == 'register':
            result = register(repo, adapter, args.evidence, write=not args.read_only)
        elif args.action == 'list':
            records = []
            for path in sorted((store_root(repo) / 'records').glob('*.json')):
                value = read_object(path)
                settings = value.get('profile', {})
                records.append({'branch': value.get('binding', {}).get('branch'), 'product': settings.get('product'),
                                'targetOs': settings.get('targetOs'), 'chipId': settings.get('chipId'), 'path': str(path)})
            releases = []
            for path in sorted((store_root(repo) / 'releases').glob('*.json')):
                value = read_object(path)
                releases.append({'branch': value.get('binding', {}).get('branch'), 'version': value.get('version'), 'path': str(path)})
            result = {'records': records, 'releases': releases}
        elif args.action == 'expand':
            result = expand_explicit(repo, adapter, write=not args.read_only)
        elif args.action == 'release-snapshot':
            result = release_snapshot(repo, adapter, args.version or read_yl(repo)['yl_device_ver'], write=not args.read_only)
        elif args.action == 'restore-version':
            result = restore_version(repo, args.version or '', write=not args.read_only)
        else:
            result = prepare(repo, adapter, write=args.action != 'check' and not args.read_only)
    except (ValueError, OSError, RuntimeError) as exc:
        result = {'status': 'NEEDS_CONFIGURATION', 'repo': str(repo), 'error': str(exc)}
        code = 2
    else:
        code = 0
    if args.json_out:
        atomic_write(args.json_out, encoded(result))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
