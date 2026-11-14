#!/usr/bin/env python3
"""Prepare branch-bound build profiles from a repository-local durable store."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
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


class BuildInputsChanged(StoreError):
    """Root build files changed; confirmed settings need a focused owner review."""


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


def version_family(version: str) -> str:
    """Ignore publication dates and F/T or S/ST counters, retaining product text."""
    family = re.split(r'_\d{8}_\d{4}(?:_|$)', version, maxsplit=1)[0]
    return re.sub(r'_(?:ST|[FTS])\d+$', '', family)


def with_configuration_inputs(repo: Path, binding: dict, profile: dict) -> dict:
    """Add opt-in JSON values; existing profiles keep their original binding."""
    binding = {key: value for key, value in binding.items() if key != 'configurationInputs'}
    if 'configurationInputs' not in profile:
        return binding
    selectors = profile['configurationInputs']
    if not isinstance(selectors, list):
        raise StoreError('configurationInputs must be a list of {path, pointer} selectors')
    values = []
    documents = {}
    for selector in selectors:
        if not isinstance(selector, dict) or set(selector) != {'path', 'pointer'}:
            raise StoreError('Each configurationInputs selector requires exactly path and pointer')
        relative, pointer = selector['path'], selector['pointer']
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise StoreError('configurationInputs.path must be repository-relative')
        source = (repo / relative).resolve()
        if not source.is_relative_to(repo.resolve()):
            raise StoreError('configurationInputs.path must stay inside the repository')
        if not isinstance(pointer, str) or not pointer.startswith('/') or re.search(r'~(?![01])', pointer):
            raise StoreError('configurationInputs.pointer must be a non-root JSON Pointer')
        if source not in documents:
            try:
                documents[source] = json.loads(source.read_text(encoding='utf-8-sig'))
            except (OSError, ValueError) as exc:
                raise StoreError(f'Cannot read configuration input {relative}: {exc}') from exc
        value = documents[source]
        try:
            for token in pointer[1:].split('/'):
                key = token.replace('~1', '/').replace('~0', '~')
                if isinstance(value, list) and re.fullmatch(r'0|[1-9][0-9]*', key):
                    value = value[int(key)]
                elif isinstance(value, dict):
                    value = value[key]
                else:
                    raise KeyError(key)
        except (KeyError, IndexError) as exc:
            raise StoreError(f'Configuration input not found: {relative}#{pointer}') from exc
        values.append({'path': relative, 'pointer': pointer, 'value': value})
    return dict(binding, configurationInputs=values) if selectors else binding


def live_binding(repo: Path, profile: dict | None = None) -> dict:
    yl = read_yl(repo)
    if any(value == '不可用' for value in yl.values()):
        raise StoreError('Missing product/hardware/version definitions in yl.h; cannot bind a build profile')
    branch = git(repo, 'branch', '--show-current')
    if not branch:
        branch = 'detached:' + git(repo, 'rev-parse', 'HEAD')
    family = version_family(yl['yl_device_ver'])
    build_inputs = {}
    for relative in ('Makefile', 'CMakeLists.txt'):
        source = repo / relative
        if source.is_file():
            build_inputs[relative] = digest(source.read_bytes())
    binding = {
        'branch': branch, 'ylDeviceName': yl['yl_device_name'],
        'ylHwVer': yl['yl_hw_ver'], 'versionFamily': family,
        'buildInputs': build_inputs,
    }
    return with_configuration_inputs(repo, binding, profile or {})


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


def assert_binding(expected: dict, actual: dict, *, root_review: bool = False) -> None:
    # Older records kept S/ST suffixes (or terminal dates) in versionFamily.
    # Read them compatibly without rewriting historical records or relaxing the
    # branch, product, hardware, and build-input bindings.
    differences = [key for key in sorted(expected.keys() | actual.keys()) if (
        version_family(str(expected.get(key, ''))) != version_family(str(actual.get(key, '')))
        if key == 'versionFamily' else encoded({'value': expected.get(key)}) != encoded({'value': actual.get(key)})
    )]
    if root_review and differences == ['buildInputs']:
        raise BuildInputsChanged(
            'Root Makefile/CMakeLists.txt changed; review the definitions used by this target. '
            'If the registered settings remain valid, run refresh-inputs --evidence <review>; '
            'no parameter reconfirmation is needed.')
    if differences:
        raise StoreError('Stored build profile does not match current identity: ' + ', '.join(differences))


def _profile_without_binding(profile: dict) -> dict:
    return {key: value for key, value in profile.items() if key != 'contextBinding'}


def load_record(path: Path, binding: dict, repo: Path) -> dict:
    record = read_object(path)
    profile = record.get('profile')
    if not isinstance(profile, dict) or digest(encoded(profile)) != record.get('profileSha256'):
        raise StoreError(f'Profile record checksum mismatch: {path}')
    assert_binding(record.get('binding', {}), with_configuration_inputs(repo, binding, profile), root_review=True)
    validate_profile(profile, repo)
    return record


def register(repo: Path, adapter: Path, evidence: str, *, write: bool = True) -> dict:
    if not evidence.strip():
        raise StoreError('Registration requires the source of the confirmed build parameters (--evidence)')
    profile = _profile_without_binding(read_object(adapter))
    validate_profile(profile, repo)
    binding = live_binding(repo, profile)
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
            assert_binding(binding, live_binding(repo, profile))
            if path.exists():
                previous = read_object(path)
                if encoded(previous.get('binding', {})) == encoded(binding) and previous.get('profileSha256') == profile_hash:
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


def refresh_inputs(repo: Path, evidence: str, *, write: bool = True) -> dict:
    """Record an owner's review without changing any registered build parameters."""
    if not evidence.strip():
        raise StoreError('Build input refresh requires the focused review (--evidence)')
    path = record_path(repo, live_binding(repo))
    target = repo / PROFILE_PATH
    changed = []
    with record_lock(path) if write else nullcontext():
        previous = read_object(path)
        profile = previous.get('profile')
        if not isinstance(profile, dict) or digest(encoded(profile)) != previous.get('profileSha256'):
            raise StoreError(f'Profile record checksum mismatch: {path}')
        binding = live_binding(repo, profile)
        old_binding = previous.get('binding', {})
        # Review may refresh only the root hashes, never product or selected values.
        assert_binding(old_binding, dict(binding, buildInputs=old_binding.get('buildInputs')))
        validate_profile(profile, repo)
        current = read_object(target) if target.exists() else None
        if current is not None:
            current_binding = current.get('contextBinding')
            if not isinstance(current_binding, dict) or not current_binding.get('branch'):
                raise StoreError('Local profile is unregistered; preserving it before input refresh')
            current_record = read_object(record_path(repo, current_binding))
            assert_binding(current_record.get('binding', {}), current_binding)
            if digest(encoded(_profile_without_binding(current))) != current_record.get('profileSha256'):
                raise StoreError('Local profile has unregistered edits; preserving it before input refresh')
        if encoded(old_binding) == encoded(binding):
            return {'status': 'UNCHANGED', 'recordPath': str(path), 'changed': []}
        record = dict(previous, binding=binding, buildInputReview={
            'evidence': evidence, 'commit': git(repo, 'rev-parse', 'HEAD'),
            'at': datetime.now(timezone.utc).isoformat(),
        })
        if write:
            assert_binding(binding, live_binding(repo, profile))
            current_now = read_object(target) if target.exists() else None
            if encoded(current_now) != encoded(current):
                raise StoreError('Local profile changed during input review; preserving the newer file')
            history = path.parent.parent / 'history' / (digest(encoded(previous)) + '.json')
            atomic_write(history, encoded(previous))
            if atomic_write(path, encoded(record)):
                changed.append(str(path))
            if atomic_write(target, encoded(dict(profile, contextBinding=binding))):
                changed.append(str(target))
    return {'status': 'INPUTS_REFRESHED' if write else 'WOULD_REFRESH_INPUTS',
            'repo': str(repo), 'recordPath': str(path), 'adapterPath': str(target), 'changed': changed}


def prepare(repo: Path, adapter: Path | None = None, *, write: bool = True) -> dict:
    binding = live_binding(repo)
    target = adapter or repo / PROFILE_PATH
    path = record_path(repo, binding)
    current = read_object(target) if target.exists() else None
    saved = load_record(path, binding, repo) if path.exists() else None
    if saved:
        binding = with_configuration_inputs(repo, binding, saved['profile'])
    selected = None
    origin = 'current'
    if current and encoded(current.get('contextBinding', {})) == encoded(binding):
        validate_profile(current, repo)
        # A local edit must be deliberately re-registered; never silently choose between two truths.
        if saved:
            if digest(encoded(_profile_without_binding(current))) != saved['profileSha256']:
                raise StoreError('Current profile differs from its registered record; review and register the intended update')
        else:
            raise StoreError('Bound profile has no durable source record; register it to restore the store')
        selected = current
    elif current and not current.get('contextBinding'):
        raise StoreError('Build profile has no confirmed branch binding; register it once with evidence')
    elif saved:
        if current and current.get('contextBinding'):
            previous_path = record_path(repo, current['contextBinding'])
            previous = read_object(previous_path) if previous_path.exists() else {}
            if digest(encoded(_profile_without_binding(current))) != previous.get('profileSha256'):
                raise StoreError('Previous branch profile has unregistered edits; preserve and register them before switching configuration')
        selected = dict(saved['profile'], contextBinding=binding)
        origin = 'record'
    else:
        raise StoreError(f'No confirmed build profile for branch {binding["branch"]}; register exact build parameters once')
    changed = []
    if write:
        with record_lock(path):
            assert_binding(binding, live_binding(repo, selected))
            latest = load_record(path, binding, repo)
            if latest['profileSha256'] != digest(encoded(_profile_without_binding(selected))):
                raise StoreError('Branch record changed during preparation; retry with the new record')
            current_now = read_object(target) if target.exists() else None
            if encoded(current_now) != encoded(current):
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
        assert_binding(expanded['contextBinding'], live_binding(repo, expanded), root_review=True)
    elif 'configurationInputs' in expanded and expanded['configurationInputs'] != []:
        raise StoreError('configurationInputs requires a registered contextBinding')
    path = store_root(repo) / 'expanded' / (digest(encoded(expanded)) + '.json')
    if write:
        atomic_write(path, encoded(expanded))
    return {'status': 'EXPANDED', 'expandedPath': str(path), 'adapterPath': str(adapter)}


def release_path(repo: Path, branch: str, version: str) -> Path:
    return store_root(repo) / 'releases' / (digest((branch + '\n' + version).encode('utf-8')) + '.json')


def release_snapshot(repo: Path, adapter: Path, version: str, *, write: bool = True) -> dict:
    profile = read_object(adapter)
    validate_profile(profile, repo)
    binding = live_binding(repo, profile)
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
            if path.exists() and encoded(read_object(path)) != encoded(value):
                raise StoreError(f'Release configuration snapshot already exists with different content: {path}')
            atomic_write(path, encoded(value))
    return {'status': 'SNAPSHOT_SAVED' if write else 'WOULD_SAVE', 'path': str(path)}


def restore_version(repo: Path, version: str, *, write: bool = True) -> dict:
    binding = live_binding(repo)
    if not version or version != read_yl(repo)['yl_device_ver']:
        raise StoreError('Select the source checkout with the requested yl_device_ver before restoring its configuration')
    path = release_path(repo, binding['branch'], version)
    snapshot = read_object(path)
    profile = snapshot.get('profile')
    if not isinstance(profile, dict) or digest(encoded(profile)) != snapshot.get('profileSha256'):
        raise StoreError(f'Release configuration checksum mismatch: {path}')
    binding = with_configuration_inputs(repo, binding, profile)
    assert_binding(snapshot.get('binding', {}), binding)
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
    parser.add_argument('action', choices=('prepare', 'register', 'refresh-inputs', 'check', 'expand', 'release-snapshot', 'restore-version', 'list'))
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
        elif args.action == 'refresh-inputs':
            if args.adapter:
                raise StoreError('refresh-inputs uses the registered parameters; --adapter is not supported')
            result = refresh_inputs(repo, args.evidence, write=not args.read_only)
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
        result = {'status': 'BUILD_INPUT_REVIEW_REQUIRED' if isinstance(exc, BuildInputsChanged) else 'NEEDS_CONFIGURATION',
                  'repo': str(repo), 'error': str(exc)}
        code = 2
    else:
        code = 0
    if args.json_out:
        atomic_write(args.json_out, encoded(result))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
