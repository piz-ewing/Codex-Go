#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codex_go.config import load_settings
from codex_go.services.codex_bridge import CodexBridgeService
from codex_go.state.store import StateStore


class FakeCdp:
    def __init__(self, sessions_dir: Path) -> None:
        self.sessions_dir = sessions_dir
        self.calls: list[tuple[str, tuple]] = []

    async def create_new_thread(self, project_name: str = "", anchor_thread_id: str = "") -> dict:
        self.calls.append(("create_new_thread", (project_name, anchor_thread_id)))
        return {"ok": True}

    async def send_text(self, text: str, thread_id: str = "", title: str = "", attachments: list[Path] | None = None) -> dict:
        self.calls.append(("send_text", (text, thread_id, title, [Path(path) for path in attachments or []])))
        if not thread_id:
            session_file = self.sessions_dir / "2026" / "06" / "08" / "rollout-2026-06-08T10-00-00-22222222-3333-4444-5555-666666666666.jsonl"
            session_file.parent.mkdir(parents=True, exist_ok=True)
            rows = [
                {
                    "timestamp": "2026-06-08T10:00:00.000Z",
                    "type": "session_meta",
                    "payload": {"id": "22222222-3333-4444-5555-666666666666", "cwd": ""},
                },
                {
                    "timestamp": "2026-06-08T10:00:01.000Z",
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": text},
                },
            ]
            session_file.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
        return {"ok": True}


class NewThreadDeferredCreationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.env_backup = os.environ.copy()
        self.temp_root = Path(tempfile.mkdtemp(prefix="codex-go-new-thread-test-"))
        os.environ["CODEX_GO_CODEX_HOME"] = str(self.temp_root / ".codex")
        os.environ["CODEX_GO_SESSIONS_DIR"] = str(self.temp_root / ".codex" / "sessions")
        os.environ["CODEX_GO_SESSION_INDEX"] = str(self.temp_root / ".codex" / "session_index.jsonl")
        os.environ["CODEX_GO_STATE_DIR"] = str(self.temp_root / ".codex-go")
        os.environ["CODEX_GO_PUBLIC_DIR"] = str(ROOT / "public")
        self.settings = load_settings()
        self.cdp = FakeCdp(self.settings.paths.sessions_dir)
        self.bridge = CodexBridgeService(settings=self.settings, cdp=self.cdp, state=StateStore(self.settings))

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.env_backup)
        shutil.rmtree(self.temp_root, ignore_errors=True)

    async def test_new_thread_endpoint_only_returns_draft_metadata(self) -> None:
        result = await self.bridge.create_new_thread(
            SimpleNamespace(threadId="", projectPath="", scope="conversation", isProjectThread=False)
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["pending"])
        self.assertEqual(result["scope"], "conversation")
        self.assertEqual(self.cdp.calls, [])

    async def test_first_send_creates_thread_then_sends_text(self) -> None:
        payload = SimpleNamespace(
            target="codex",
            attachments=[],
            text="第一条消息",
            threadId="",
            previousThreadId="11111111-2222-3333-4444-555555555555",
            expectedCwd="",
            newThreadScope="conversation",
            projectPath="",
            isProjectThread=False,
            expectNewThread=True,
            directPasteWithoutClick=False,
            clientRequestId="send-test-0001",
        )

        result = await self.bridge.send(payload)

        self.assertTrue(result["ok"])
        self.assertEqual(result["watch"]["expectNewThread"], False)
        self.assertEqual(result["watch"]["threadId"], "22222222-3333-4444-5555-666666666666")
        self.assertEqual(
            self.cdp.calls,
            [
                ("create_new_thread", ("", "11111111-2222-3333-4444-555555555555")),
                ("send_text", ("第一条消息", "", "", [])),
            ],
        )


if __name__ == "__main__":
    unittest.main()
