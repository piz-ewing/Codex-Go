#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codex_go.codex import list_threads
from codex_go.config import load_settings
from codex_go.state.store import StateStore


THREAD_ID = "11111111-2222-3333-4444-555555555555"
SESSION_FILE = f"rollout-2026-06-08T10-00-00-{THREAD_ID}.jsonl"


def write_jsonl(file: Path, rows: list[dict]) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class ThreadArchiveRestoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.env_backup = os.environ.copy()
        self.temp_root = Path(tempfile.mkdtemp(prefix="codex-go-thread-archive-test-"))
        self.session_path = self.temp_root / ".codex" / "sessions" / "2026" / "06" / "08" / SESSION_FILE
        os.environ["CODEX_GO_CODEX_HOME"] = str(self.temp_root / ".codex")
        os.environ["CODEX_GO_SESSIONS_DIR"] = str(self.temp_root / ".codex" / "sessions")
        os.environ["CODEX_GO_SESSION_INDEX"] = str(self.temp_root / ".codex" / "session_index.jsonl")
        os.environ["CODEX_GO_STATE_DIR"] = str(self.temp_root / ".codex-go")
        os.environ["CODEX_GO_PUBLIC_DIR"] = str(ROOT / "public")
        self.settings = load_settings()
        write_jsonl(
            self.session_path,
            [
                {
                    "timestamp": "2026-06-08T10:00:00.000Z",
                    "type": "session_meta",
                    "payload": {"id": THREAD_ID, "cwd": str(ROOT)},
                },
                {
                    "timestamp": "2026-06-08T10:00:01.000Z",
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": "检查归档恢复"},
                },
            ],
        )

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.env_backup)
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def write_state(self, state: dict) -> None:
        StateStore(self.settings).write(state)

    def test_legacy_archived_thread_is_restored_when_session_file_exists(self) -> None:
        self.write_state({"archivedThreadIds": [THREAD_ID]})

        threads = list_threads(self.settings)

        self.assertIn(THREAD_ID, [thread["id"] for thread in threads])
        self.assertNotIn(THREAD_ID, StateStore(self.settings).read()["archivedThreadIds"])

    def test_recent_archive_detail_keeps_thread_hidden_until_session_changes(self) -> None:
        mtime_ms = self.session_path.stat().st_mtime * 1000
        self.write_state(
            {
                "archivedThreadIds": [THREAD_ID],
                "archivedThreadDetails": {
                    THREAD_ID: {
                        "archivedAt": "2026-06-08T10:00:02.000Z",
                        "sessionFile": SESSION_FILE,
                        "sessionMtimeMs": mtime_ms,
                    }
                },
            }
        )

        threads = list_threads(self.settings)

        self.assertNotIn(THREAD_ID, [thread["id"] for thread in threads])
        self.assertIn(THREAD_ID, StateStore(self.settings).read()["archivedThreadIds"])

    def test_archived_thread_is_restored_after_session_file_changes(self) -> None:
        mtime_ms = self.session_path.stat().st_mtime * 1000
        self.write_state(
            {
                "archivedThreadIds": [THREAD_ID],
                "archivedThreadDetails": {
                    THREAD_ID: {
                        "archivedAt": "2026-06-08T10:00:02.000Z",
                        "sessionFile": SESSION_FILE,
                        "sessionMtimeMs": mtime_ms,
                    }
                },
            }
        )
        changed_mtime = time.time() + 5
        os.utime(self.session_path, (changed_mtime, changed_mtime))

        threads = list_threads(self.settings)

        self.assertIn(THREAD_ID, [thread["id"] for thread in threads])
        state = StateStore(self.settings).read()
        self.assertNotIn(THREAD_ID, state["archivedThreadIds"])
        self.assertNotIn(THREAD_ID, state["archivedThreadDetails"])


if __name__ == "__main__":
    unittest.main()
