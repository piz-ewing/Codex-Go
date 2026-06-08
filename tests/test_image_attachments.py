#!/usr/bin/env python3
from __future__ import annotations

import base64
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
from codex_go.services.attachments import AttachmentError, prepare_attachments, prepare_image_attachments
from codex_go.services.codex_bridge import CodexBridgeService
from codex_go.state.store import StateStore


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class FakeCdp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    async def send_text(self, text: str, thread_id: str = "", title: str = "", attachments: list[Path] | None = None) -> dict:
        self.calls.append(("send_text", (text, thread_id, title, [Path(path) for path in attachments or []])))
        return {"ok": True}


class ImageAttachmentTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.env_backup = os.environ.copy()
        self.temp_root = Path(tempfile.mkdtemp(prefix="codex-go-image-test-"))
        os.environ["CODEX_GO_CODEX_HOME"] = str(self.temp_root / ".codex")
        os.environ["CODEX_GO_SESSIONS_DIR"] = str(self.temp_root / ".codex" / "sessions")
        os.environ["CODEX_GO_SESSION_INDEX"] = str(self.temp_root / ".codex" / "session_index.jsonl")
        os.environ["CODEX_GO_STATE_DIR"] = str(self.temp_root / ".codex-go")
        os.environ["CODEX_GO_UPLOAD_DIR"] = str(self.temp_root / "uploads")
        os.environ["CODEX_GO_PUBLIC_DIR"] = str(ROOT / "public")
        self.settings = load_settings()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.env_backup)
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_prepare_image_attachment_writes_valid_image_to_upload_dir(self) -> None:
        data_url = "data:image/png;base64," + base64.b64encode(PNG_1X1).decode("ascii")

        attachments = prepare_image_attachments([{"name": "../demo.png", "type": "image/png", "dataUrl": data_url}], self.settings)

        self.assertEqual(len(attachments), 1)
        attachment = attachments[0]
        self.assertEqual(attachment.type, "image/png")
        self.assertTrue(attachment.path.is_file())
        self.assertTrue(str(attachment.path).startswith(str(self.settings.paths.upload_dir)))
        self.assertEqual(attachment.path.read_bytes(), PNG_1X1)
        self.assertNotIn("..", attachment.name)

    def test_prepare_attachment_writes_text_file_to_upload_dir(self) -> None:
        data_url = "data:text/plain;base64," + base64.b64encode(b"hello").decode("ascii")

        attachments = prepare_attachments([{"name": "../note.txt", "type": "text/plain", "dataUrl": data_url}], self.settings)

        self.assertEqual(len(attachments), 1)
        attachment = attachments[0]
        self.assertEqual(attachment.type, "text/plain")
        self.assertTrue(attachment.path.is_file())
        self.assertTrue(str(attachment.path).startswith(str(self.settings.paths.upload_dir)))
        self.assertEqual(attachment.path.read_bytes(), b"hello")
        self.assertNotIn("..", attachment.name)

    def test_prepare_attachment_rejects_svg_image_payload(self) -> None:
        data_url = "data:image/svg+xml;base64," + base64.b64encode(b"<svg></svg>").decode("ascii")

        with self.assertRaises(AttachmentError) as context:
            prepare_attachments([{"name": "bad.svg", "type": "image/svg+xml", "dataUrl": data_url}], self.settings)

        self.assertEqual(context.exception.code, "BAD_ATTACHMENT_TYPE")

    def test_prepare_attachment_rejects_blocked_executable_name(self) -> None:
        data_url = "data:application/octet-stream;base64," + base64.b64encode(b"hello").decode("ascii")

        with self.assertRaises(AttachmentError) as context:
            prepare_attachments([{"name": "run.exe", "type": "application/octet-stream", "dataUrl": data_url}], self.settings)

        self.assertEqual(context.exception.code, "BAD_ATTACHMENT_TYPE")

    async def test_bridge_sends_attachment_file_paths_to_cdp(self) -> None:
        data_url = "data:image/png;base64," + base64.b64encode(PNG_1X1).decode("ascii")
        cdp = FakeCdp()
        bridge = CodexBridgeService(settings=self.settings, cdp=cdp, state=StateStore(self.settings))
        payload = SimpleNamespace(
            target="codex",
            attachments=[{"name": "shot.png", "type": "image/png", "dataUrl": data_url}],
            text="看这张图",
            threadId="",
            previousThreadId="",
            expectedCwd="",
            newThreadScope="conversation",
            projectPath="",
            isProjectThread=False,
            expectNewThread=False,
            directPasteWithoutClick=False,
            clientRequestId="send-attachment-0001",
        )

        result = await bridge.send(payload)

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["attachments"]), 1)
        self.assertEqual(cdp.calls[0][0], "send_text")
        text, thread_id, title, paths = cdp.calls[0][1]
        self.assertEqual((text, thread_id, title), ("看这张图", "", ""))
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].is_file())
        self.assertEqual(paths[0].read_bytes(), PNG_1X1)

    async def test_bridge_sends_non_image_attachment_file_paths_to_cdp(self) -> None:
        data_url = "data:text/plain;base64," + base64.b64encode(b"hello").decode("ascii")
        cdp = FakeCdp()
        bridge = CodexBridgeService(settings=self.settings, cdp=cdp, state=StateStore(self.settings))
        payload = SimpleNamespace(
            target="codex",
            attachments=[{"name": "note.txt", "type": "text/plain", "dataUrl": data_url}],
            text="看这个文件",
            threadId="",
            previousThreadId="",
            expectedCwd="",
            newThreadScope="conversation",
            projectPath="",
            isProjectThread=False,
            expectNewThread=False,
            directPasteWithoutClick=False,
            clientRequestId="send-file-0001",
        )

        result = await bridge.send(payload)

        self.assertTrue(result["ok"])
        self.assertEqual(result["attachments"][0]["type"], "text/plain")
        self.assertEqual(cdp.calls[0][0], "send_text")
        _text, _thread_id, _title, paths = cdp.calls[0][1]
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].is_file())
        self.assertEqual(paths[0].read_bytes(), b"hello")


if __name__ == "__main__":
    unittest.main()
