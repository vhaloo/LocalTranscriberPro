import shutil

import pytest

from scripts.check_release_docs import ROOT, check


def fixture_repo(tmp_path):
    for name in ('src/__init__.py', 'pyproject.toml', 'packaging/windows/installer.iss',
                 'packaging/LocalTranscriberPro.spec', 'README.md', 'CHANGELOG.md',
                 'docs/TRANSLATION.md', 'docs/VALIDATION_3.1.md'):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    shutil.copytree(ROOT / 'docs/images', tmp_path / 'docs/images')
    return tmp_path


def test_current_release_docs():
    assert check()[1] == []


@pytest.mark.parametrize('name', ['README.md', 'CHANGELOG.md', 'pyproject.toml',
                                  'docs/images/current-release.json'])
def test_stale_release_is_blocked(tmp_path, name):
    root = fixture_repo(tmp_path)
    path = root / name
    path.write_text(path.read_text('utf-8').replace('3.1.0', '0.0.1'), encoding='utf-8')
    assert check(root)[1]


def test_changed_screenshot_is_blocked(tmp_path):
    import json
    root = fixture_repo(tmp_path)
    manifest = json.loads((root / 'docs/images/current-release.json').read_text('utf-8'))
    path = root / 'docs/images' / manifest['images'][0]['file']
    path.write_bytes(path.read_bytes() + b'changed')
    assert any('checksum' in error for error in check(root)[1])
