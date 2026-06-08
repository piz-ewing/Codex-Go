#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codex_go.cdp.client import CdpClient, CdpTarget
from codex_go.config import CdpSettings


class FakeWebSocket:
    def __init__(self) -> None:
        self.last_request: dict = {}
        self.calls: list[tuple[str, dict]] = []

    async def send(self, raw: str) -> None:
        self.last_request = json.loads(raw)
        self.calls.append((self.last_request["method"], self.last_request.get("params") or {}))

    async def recv(self) -> str:
        request_id = self.last_request["id"]
        method = self.last_request["method"]
        params = self.last_request.get("params") or {}
        if method == "Runtime.evaluate" and params.get("returnByValue"):
            value = {"ok": True, "fileCount": 1} if params.get("expression") == "after()" else {"ok": True}
            return json.dumps({"id": request_id, "result": {"result": {"value": value}}})
        if method == "Runtime.evaluate":
            return json.dumps({"id": request_id, "result": {"result": {"objectId": "attachment-input-object"}}})
        if method == "DOM.requestNode":
            return json.dumps({"id": request_id, "result": {}})
        return json.dumps({"id": request_id, "result": {}})


class FakeConnection:
    def __init__(self, socket: FakeWebSocket) -> None:
        self.socket = socket

    async def __aenter__(self) -> FakeWebSocket:
        return self.socket

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None


class FakeCdpClient(CdpClient):
    async def get_page_target(self) -> CdpTarget:
        return CdpTarget("target", "page", "app://-/index.html", "Codex", "ws://codex.test")


class CdpFileInputTest(unittest.IsolatedAsyncioTestCase):
    async def test_set_file_input_files_uses_object_id_when_request_node_returns_no_node_id(self) -> None:
        socket = FakeWebSocket()
        websockets = SimpleNamespace(connect=lambda *_args, **_kwargs: FakeConnection(socket))
        client = FakeCdpClient(CdpSettings(host="127.0.0.1", port=39252, timeout_seconds=1.0))

        with patch.dict(sys.modules, {"websockets": websockets}):
            result = await client.set_file_input_files("prepare()", ["/tmp/shot.png"], "after()")

        self.assertTrue(result["ok"])
        self.assertTrue(result["fileInputTarget"]["usedObjectIdFallback"])
        self.assertIn(("DOM.setFileInputFiles", {"objectId": "attachment-input-object", "files": ["/tmp/shot.png"]}), socket.calls)


if __name__ == "__main__":
    unittest.main()
