"""Native packaged CPU recognition and bundled offline-voice smoke checks."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import requests
from faster_whisper import WhisperModel
from platformdirs import user_cache_dir

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    executable = args.executable.resolve()
    folder = Path('artifacts/packaged-smoke').resolve()
    folder.mkdir(parents=True, exist_ok=True)
    response = requests.get('https://raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac', timeout=60)
    response.raise_for_status()
    sample = folder / 'jfk.flac'
    sample.write_bytes(response.content)
    # Prepare locally before the genuine executable is required to stay offline.
    model = WhisperModel('tiny', device='cpu', download_root=str(Path(user_cache_dir('LocalTranscriberPro', 'Vhaloo')) / 'models'))
    del model
    cases = [
        ['--smoke-test', str(sample), '--model', 'tiny', '--device', 'cpu', '--offline'],
        ['--voice-test', 'fr', '--voice-text', 'Bonjour, ceci est une vérification locale.', '--offline'],
        ['--voice-test', 'en', '--voice-text', 'Hello, this is a local verification.', '--offline'],
    ]
    for index, command in enumerate(cases):
        report = folder / f'report-{index}.json'
        completed = subprocess.run([str(executable), *command, '--diagnostic-output', str(report)], timeout=300)
        if not report.is_file():
            raise RuntimeError(f'Packaged diagnostic {index} exited {completed.returncode} without a report')
        result = json.loads(report.read_text('utf-8'))
        assert completed.returncode == 0 and result['success'], result
        if index == 0:
            assert result['status']['model_id'] == 'tiny' and result['status']['device'] == 'cpu'
            assert result['progress_completed']
    print('Native packaged CPU ASR and bundled French/English voices passed offline checks.')
