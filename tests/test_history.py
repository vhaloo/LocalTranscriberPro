import json

from src.history import HistoryStore, SessionRecord

SEGMENTS = [{"start": 0.0, "end": 2.5, "text": "A durable local session."}]


def test_history_keeps_session_index_and_folder_log(tmp_path):
    text_path = tmp_path / "Transcription.txt"
    json_path = tmp_path / "Transcription.json"
    text_path.write_text("A durable local session.\n", encoding="utf-8")
    json_path.write_text(json.dumps(SEGMENTS), encoding="utf-8")
    store = HistoryStore(tmp_path / "history.sqlite3")
    record = SessionRecord.create(
        title="Transcription",
        task="dictation",
        text_path=text_path,
        json_path=json_path,
        model="large-v3",
        device="cuda",
        segments=SEGMENTS,
    )

    store.add(record)

    saved = store.list_sessions()
    assert saved == [record]
    assert store.load_segments(saved[0]) == SEGMENTS
    log = (tmp_path / "LocalTranscriberPro-history.jsonl").read_text(encoding="utf-8")
    assert "large-v3" in log


def test_history_imports_exports_from_older_versions(tmp_path):
    (tmp_path / "Old.txt").write_text("Old session\n", encoding="utf-8")
    (tmp_path / "Old.json").write_text(json.dumps(SEGMENTS), encoding="utf-8")
    store = HistoryStore(tmp_path / "history.sqlite3")

    assert store.index_existing(tmp_path) == 1
    assert store.index_existing(tmp_path) == 0
    assert store.list_sessions()[0].task == "legacy"
