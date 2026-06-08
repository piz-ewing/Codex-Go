#!/usr/bin/env python3
from __future__ import annotations

import base64
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codex_go.cdp.actions import CodexCdpActions


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class FakeClient:
    def __init__(self) -> None:
        self.evaluated: list[str] = []
        self.calls: list[tuple[str, dict]] = []
        self.snapshot_reads = 0
        self.accept_attachment = True

    async def evaluate(self, expression: str) -> dict:
        self.evaluated.append(expression)
        if "matchedNames" in expression and "likelyCount" in expression:
            self.snapshot_reads += 1
            if self.snapshot_reads == 1:
                return {"ok": True, "matchedNames": [], "likelyCount": 0, "imageCount": 0, "previewCount": 0}
            if not self.accept_attachment:
                return {"ok": True, "matchedNames": [], "likelyCount": 0, "imageCount": 0, "previewCount": 0}
            return {"ok": True, "matchedNames": ["shot.png"], "likelyCount": 1, "imageCount": 1, "previewCount": 1}
        if "Input.dispatchDragEvent" not in expression and "getBoundingClientRect()" in expression and "x:" in expression and "y:" in expression:
            return {"ok": True, "x": 240, "y": 560}
        if "focus" in expression and ".ProseMirror" in expression:
            return {"ok": True}
        if "sendButton.click()" in expression:
            return {"ok": True}
        return {"ok": True}

    async def call(self, method: str, params: dict | None = None) -> dict:
        self.calls.append((method, params or {}))
        return {}


class CdpSendAttachmentTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_text_drags_image_attachment_into_composer(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-go-cdp-send-test-") as temp_dir:
            image_path = Path(temp_dir) / "shot.png"
            image_path.write_bytes(PNG_1X1)
            client = FakeClient()
            actions = CodexCdpActions(client)  # type: ignore[arg-type]

            result = await actions.send_text("看图", attachments=[image_path])

        self.assertTrue(result["ok"])
        self.assertEqual(result["attachments"]["method"], "native-drag")
        self.assertEqual(result["sent"]["method"], "enter")
        self.assertIn(("Input.insertText", {"text": "看图"}), client.calls)
        drag_calls = [params for method, params in client.calls if method == "Input.dispatchDragEvent"]
        self.assertEqual([call["type"] for call in drag_calls], ["dragEnter", "dragOver", "drop"])
        self.assertEqual(drag_calls[0]["files"] if "files" in drag_calls[0] else drag_calls[0]["data"]["files"], [str(image_path.resolve())])
        key_calls = [params["type"] for method, params in client.calls if method == "Input.dispatchKeyEvent"]
        self.assertEqual(key_calls, ["keyDown", "keyUp"])
        self.assertFalse(any("decodeBase64" in expression or "method: 'paste'" in expression for expression in client.evaluated))

    async def test_send_text_stops_when_native_drag_is_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-go-cdp-send-test-") as temp_dir:
            image_path = Path(temp_dir) / "shot.png"
            image_path.write_bytes(PNG_1X1)
            client = FakeClient()
            client.accept_attachment = False
            actions = CodexCdpActions(client)  # type: ignore[arg-type]

            with self.assertRaisesRegex(Exception, "没有接收原生拖拽附件"):
                await actions.send_text("看图", attachments=[image_path])

        self.assertNotIn(("Input.insertText", {"text": "看图"}), client.calls)
        self.assertFalse(any(method == "Input.dispatchKeyEvent" for method, _params in client.calls))
        self.assertFalse(any("method: 'paste'" in expression or "decodeBase64" in expression for expression in client.evaluated))


if __name__ == "__main__":
    unittest.main()
