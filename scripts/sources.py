"""Prepare pinned upstream source files. Does not execute downloaded code."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_ARCHIVE = 100 * 1024 * 1024
MAX_EXTRACTED = 256 * 1024 * 1024


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not path.parts or path.is_absolute() or '..' in path.parts or '\\' in value or ':' in value:
        raise ValueError(f'Unsafe archive/manifest path: {value}')
    return path


def read_sources(root: Path = ROOT) -> list[dict]:
    sources = json.loads((root / 'sources.lock.json').read_text(encoding='utf8'))['sources']
    sequence = json.loads((root / 'loop.config.json').read_text(encoding='utf8'))['sequence']
    if [s['id'] for s in sources] != sequence or len(set(sequence)) != len(sequence):
        raise ValueError('Manifest order must match the unique configured sequence')
    for source in sources:
        if not re.fullmatch(r'[a-z0-9-]+', source['id']):
            raise ValueError('Invalid source ID')
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', source['repository']):
            raise ValueError('Invalid GitHub repository')
        if not re.fullmatch(r'[a-f0-9]{40}', source['commit']):
            raise ValueError('Expected a full commit SHA')
        if not re.fullmatch(r'[a-f0-9]{64}', source['sha256']):
            raise ValueError('Expected an archive SHA-256')
        for value in [source['entry'], source['license_file'], source['archive'], *source['include']]:
            safe_path(value)
        if len(PurePosixPath(source['archive']).parts) != 1:
            raise ValueError('Archive name must be a basename')
    return sources


def extract_source(archive: Path, source: dict, parent: Path) -> Path:
    if digest(archive) != source['sha256']:
        raise ValueError(f"Checksum mismatch: {source['id']}")
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / source['id']
    if target.exists():
        raise FileExistsError(f'Will not replace an existing source: {target}')
    with tempfile.TemporaryDirectory(prefix='.prepare-', dir=parent) as temp:
        output = Path(temp) / 'source'
        output.mkdir()
        if not output.resolve().is_relative_to(parent.resolve()):
            raise ValueError('Temporary directory escapes source root')
        recorded = {}
        total = 0
        with zipfile.ZipFile(archive) as bundle:
            roots = set()
            for item in bundle.infolist():
                full = safe_path(item.filename)
                roots.add(full.parts[0])
                if len(roots) > 1:
                    raise ValueError('Expected a single GitHub archive root')
                if len(full.parts) < 2 or item.is_dir():
                    continue
                relative = PurePosixPath(*full.parts[1:]).as_posix()
                if not any(relative == p.rstrip('/') or relative.startswith(p.rstrip('/') + '/')
                           for p in source['include']):
                    continue
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError(f'Selected archive entry is a symlink: {relative}')
                total += item.file_size
                if total > MAX_EXTRACTED:
                    raise ValueError('Selected source exceeds extraction limit')
                file = output.joinpath(*PurePosixPath(relative).parts)
                if not file.resolve().is_relative_to(output.resolve()):
                    raise ValueError('Archive member escapes output directory')
                if relative in recorded:
                    raise ValueError('Duplicate archive member')
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(bundle.read(item))
                recorded[relative] = digest(file)
        for required in (source['entry'], source['license_file']):
            if required not in recorded:
                raise ValueError(f'Missing required source or license: {required}')
        record = {'commit': source['commit'], 'archive_sha256': source['sha256'], 'files': recorded}
        (output / '.source-files.json').write_text(json.dumps(record, indent=2), encoding='utf8')
        output.rename(target)
    return target


def verify_source(target: Path, source: dict) -> None:
    record = json.loads((target / '.source-files.json').read_text(encoding='utf8'))
    if record['commit'] != source['commit'] or record['archive_sha256'] != source['sha256']:
        raise ValueError(f"Source version differs from lock: {source['id']}")
    if source['entry'] not in record['files'] or source['license_file'] not in record['files']:
        raise ValueError('Source record lacks required entry/license')
    for name, expected in record['files'].items():
        file = target.joinpath(*safe_path(name).parts)
        if not file.resolve().is_relative_to(target.resolve()) or digest(file) != expected:
            raise ValueError(f'Modified source file: {file}')


def download(source: dict, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / source['archive']
    url = f"https://codeload.github.com/{source['repository']}/zip/{source['commit']}"
    with tempfile.NamedTemporaryFile(dir=folder, delete=False, suffix='.part') as stream:
        temporary = Path(stream.name)
        try:
            total = 0
            request = urllib.request.Request(url, headers={'User-Agent': 'design-skills-loop'})
            with urllib.request.urlopen(request, timeout=60) as response:
                while block := response.read(1024 * 1024):
                    total += len(block)
                    if total > MAX_ARCHIVE:
                        raise ValueError('Download exceeds archive size limit')
                    stream.write(block)
            stream.close()
            if digest(temporary) != source['sha256']:
                raise ValueError(f"Downloaded checksum differs from lock: {source['id']}")
            temporary.replace(final)
        finally:
            stream.close()
            temporary.unlink(missing_ok=True)
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['fetch', 'verify'])
    parser.add_argument('--cache-dir', type=Path, help='Existing ZIP cache; read-only')
    parser.add_argument('--offline', action='store_true', help='Never download missing archives')
    args = parser.parse_args()
    try:
        sources = read_sources()
        parent = ROOT / '.upstream'
        if not parent.resolve().is_relative_to(ROOT):
            raise ValueError('Source directory must stay inside the skill root')
        resolved = {}
        for source in sources:
            target = parent / source['id']
            if not target.resolve().is_relative_to(parent.resolve()):
                raise ValueError('Source target escapes source directory')
            if not target.exists() and args.command == 'fetch':
                cached = args.cache_dir / source['archive'] if args.cache_dir else None
                archive = cached if cached and cached.is_file() else parent / '.downloads' / source['archive']
                if not archive.is_file():
                    if args.offline:
                        raise FileNotFoundError(f'Missing cached archive: {source["archive"]}')
                    archive = download(source, parent / '.downloads')
                extract_source(archive, source, parent)
            verify_source(target, source)
            resolved[source['id']] = {'entry': str((target / source['entry']).resolve()),
                                      'root': str(target.resolve()), 'commit': source['commit']}
            print(f"OK {source['id']} {source['commit'][:12]}")
        (ROOT / 'sources.local.json').write_text(json.dumps(resolved, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        print(f'Ready: {len(sources)} sources. Loop execution is defined in SKILL.md.')
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f'ERROR: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
