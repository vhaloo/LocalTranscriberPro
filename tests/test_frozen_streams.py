import sys

from tqdm import tqdm

from src.utils import configure_frozen_streams


def test_frozen_checkpoint_progress_works_with_absent_or_invalid_console(monkeypatch):
    class BrokenConsole:
        def flush(self):
            raise OSError(22, "Invalid argument")

    for original in (None, BrokenConsole()):
        with monkeypatch.context() as patch:
            patch.setattr(sys, "frozen", True, raising=False)
            patch.setattr(sys, "stdout", original)
            patch.setattr(sys, "stderr", original)
            configure_frozen_streams()
            streams = (sys.stdout, sys.stderr)
            try:
                # Reproduce the actual checkpoint-loader path: tqdm flushes
                # stdout as well as its own stderr while creating the bar.
                assert list(tqdm(range(2), desc="Loading checkpoint shards", disable=False)) == [0, 1]
                print("Test multilingue : français, العربية, 日本語")
                sys.stdout.flush()
                sys.stderr.flush()
            finally:
                for stream in streams:
                    stream.close()
