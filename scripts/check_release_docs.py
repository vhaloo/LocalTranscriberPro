"""Fail a release when its public instructions/screenshots describe an older build."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    errors = []
    version = re.search(r'__version__ = "([^"]+)"', (root / 'src/__init__.py').read_text('utf-8'))[1]
    for filename, expression in [
        ('pyproject.toml', r'version = "([^"]+)"'),
        ('packaging/windows/installer.iss', r'#define AppVersion "([^"]+)"'),
        ('packaging/LocalTranscriberPro.spec', r'version="([^"]+)"'),
    ]:
        match = re.search(expression, (root / filename).read_text('utf-8'))
        if not match or match[1] != version:
            errors.append(filename + ': inconsistent release version')
    readme = (root / 'README.md').read_text('utf-8')
    if not readme.startswith('# Local Transcriber Pro ' + version + '\n'):
        errors.append('README.md: stale title')
    if f'releases/download/v{version}/LocalTranscriberPro-{version}-Windows-x64-Setup.exe' not in readme:
        errors.append('README.md: stale Windows download')
    if not (root / 'CHANGELOG.md').read_text('utf-8').startswith(f'# Changelog\n\n## {version}'):
        errors.append('CHANGELOG.md: missing current release entry')
    for filename in ('docs/TRANSLATION.md', 'docs/VALIDATION_3.1.md'):
        if version not in (root / filename).read_text('utf-8'):
            errors.append(filename + ': stale release documentation')
    try:
        screenshots = json.loads((root / 'docs/images/current-release.json').read_text('utf-8'))
        if screenshots['version'] != version:
            errors.append('Screenshots belong to another release')
        if not screenshots['images']:
            errors.append('No current screenshots')
        for entry in screenshots['images']:
            path = (root / 'docs/images' / entry['file']).resolve()
            if path.parent != (root / 'docs/images').resolve():
                errors.append('Invalid screenshot path')
                continue
            data = path.read_bytes()
            if not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')):
                errors.append('Invalid screenshot image: ' + entry['file'])
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                errors.append('Screenshot checksum changed: ' + entry['file'])
            if entry['file'] not in readme:
                errors.append('Screenshot absent from README: ' + entry['file'])
    except (OSError, ValueError, KeyError, TypeError):
        errors.append('Current screenshot manifest missing or invalid')
    return version, errors


if __name__ == '__main__':
    version, errors = check()
    for error in errors:
        print(error)
    if errors:
        raise SystemExit(1)
    print(f'Release {version}: public documentation and screenshots are current.')
