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
    for suffix in ('Windows-x64-Setup.exe', 'Windows-x64-CPU-Setup.exe', 'macOS-arm64-experimental.dmg',
                   'Linux-x86_64-experimental.AppImage', 'Linux-x86_64-experimental.tar.gz'):
        if f'releases/download/v{version}/LocalTranscriberPro-{version}-{suffix}' not in readme:
            errors.append('README.md: missing current download for ' + suffix)
    for download_version in re.findall(r'releases/download/v([^/\s)]+)/', readme):
        if download_version != version:
            errors.append('README.md: stale platform download')
    if not (root / 'CHANGELOG.md').read_text('utf-8').startswith(f'# Changelog\n\n## {version}'):
        errors.append('CHANGELOG.md: missing current release entry')
    minor = '.'.join(version.split('.')[:2])
    for filename in ('docs/TRANSLATION.md', f'docs/VALIDATION_{minor}.md', f'docs/EXPERIMENTAL_DESKTOP_{minor}.md'):
        if version not in (root / filename).read_text('utf-8'):
            errors.append(filename + ': stale release documentation')
    try:
        screenshots = json.loads((root / 'docs/images/current-release.json').read_text('utf-8'))
        if screenshots['version'] != version:
            errors.append('Screenshots belong to another release')
        if screenshots.get('ui_language') != 'en':
            errors.append('The current screenshot gallery must use the English interface')
        if not screenshots['images']:
            errors.append('No current screenshots')
        listed = [entry['file'] for entry in screenshots['images']]
        embedded = re.findall(r'!\[[^\]\n]*\]\(docs/images/([^\s)]+)\)', readme)
        if sorted(embedded) != sorted(set(listed)) or len(listed) != len(set(listed)):
            errors.append('README.md: screenshot gallery must match the manifest exactly')
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
