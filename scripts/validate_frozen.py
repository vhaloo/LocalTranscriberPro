"""Native packaged CPU recognition and bundled offline-voice smoke checks."""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import subprocess
import threading
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
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(folder)))
    server.daemon_threads = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    cases = [
        ['--smoke-test', str(sample), '--model', 'tiny', '--device', 'cpu', '--offline'],
        ['--voice-test', 'fr', '--voice-text', 'Bonjour, ceci est une vérification locale.', '--offline'],
        ['--voice-test', 'en', '--voice-text', 'Hello, this is a local verification.', '--offline'],
        ['--youtube-test', f'http://127.0.0.1:{server.server_port}/jfk.flac', '--model', 'tiny', '--device', 'cpu', '--offline'],
    ]
    try:
        for index, command in enumerate(cases):
            report = folder / f'report-{index}.json'
            completed = subprocess.run([str(executable), *command, '--diagnostic-output', str(report)], timeout=300)
            if not report.is_file():
                raise RuntimeError(f'Packaged diagnostic {index} exited {completed.returncode} without a report')
            result = json.loads(report.read_text('utf-8'))
            assert completed.returncode == 0 and result['success'], result
            if index in (0, 3):
                assert result['status']['model_id'] == 'tiny' and result['status']['device'] == 'cpu'
                assert result['progress_completed']
        assert not list((folder / 'youtube-qa').glob('ltp-video-*')), 'Online import left temporary audio behind'
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
    print('Native CPU ASR, bundled French/English voices and isolated HTTP audio import passed.')
