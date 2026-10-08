"""Verify every packaged application module and catalogue against release source."""
from __future__ import annotations

import argparse
import hashlib
import json
import marshal
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/frozen-source-proof.json')
    args = parser.parse_args()
    archive = CArchiveReader(str(args.executable))
    pyz = archive.open_embedded_archive('PYZ.pyz')
    report = {'success': True, 'modules': {}, 'catalogues': {}}
    for path in sorted((ROOT / 'src').glob('*.py')):
        name = 'src' if path.name == '__init__.py' else 'src.' + path.stem
        code = pyz.extract(name)
        expected = compile(path.read_text('utf-8'), code.co_filename, 'exec', dont_inherit=True, optimize=1)
        report['modules'][name] = code == expected
    code = marshal.loads(archive.extract('main'))
    report['modules']['main'] = code == compile((ROOT / 'main.py').read_text('utf-8'), code.co_filename, 'exec', dont_inherit=True, optimize=1)
    for path in sorted((ROOT / 'src/data').glob('*.json')):
        packaged = args.executable.parent / '_internal/src/data' / path.name
        report['catalogues'][path.name] = packaged.read_bytes() == path.read_bytes()
    report['success'] = all(report['modules'].values()) and all(report['catalogues'].values())
    report['exe_sha256'] = hashlib.file_digest(args.executable.open('rb'), 'sha256').hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['success'] else 1)
