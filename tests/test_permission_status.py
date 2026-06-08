#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codex_go.codex import normalize_permission_action, parse_status
from codex_go.config import load_settings


THREAD_ID = "11111111-2222-3333-4444-555555555555"
SESSION_FILE = f"rollout-2026-06-07T18-02-02-{THREAD_ID}.jsonl"


def write_jsonl(file: Path, rows: list[dict]) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class PermissionStatusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = ROOT
        self.temp_root = Path(tempfile.mkdtemp(prefix="codex-go-permission-test-"))
        self.session_path = self.temp_root / ".codex" / "sessions" / "2026" / "06" / "07" / SESSION_FILE
        self.env_backup = os.environ.copy()
        os.environ["CODEX_GO_SESSIONS_DIR"] = str(self.temp_root / ".codex" / "sessions")
        os.environ["CODEX_GO_SESSION_INDEX"] = str(self.temp_root / ".codex" / "session_index.jsonl")
        os.environ["CODEX_GO_DESKTOP_LOGS_DIR"] = str(self.temp_root / "Library" / "Logs" / "com.openai.codex")
        os.environ["CODEX_GO_STATE_DIR"] = str(self.temp_root / ".codex-go")
        os.environ["CODEX_GO_PUBLIC_DIR"] = str(self.repo_root / "public")
        self.settings = load_settings()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.env_backup)
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def permission_rows(self, extra_rows: list[dict] | None = None) -> list[dict]:
        return [
            {
                "timestamp": "2026-06-07T10:00:00.000Z",
                "type": "session_meta",
                "payload": {
                    "id": THREAD_ID,
                    "cwd": str(self.repo_root),
                    "model": "gpt-5.5",
                },
            },
            {
                "timestamp": "2026-06-07T10:00:01.000Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "turn-permission"},
            },
            {
                "timestamp": "2026-06-07T10:00:02.000Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "exec_command",
                    "call_id": "call_permission",
                    "arguments": json.dumps(
                        {
                            "cmd": "uv sync",
                            "workdir": str(self.repo_root),
                            "sandbox_permissions": "require_escalated",
                            "justification": "Do you want to allow installing dependencies?",
                            "prefix_rule": ["uv", "sync"],
                        }
                    ),
                },
            },
            *(extra_rows or []),
        ]

    def chinese_run_command_permission_rows(self) -> list[dict]:
        return [
            {
                "timestamp": "2026-06-07T10:00:00.000Z",
                "type": "session_meta",
                "payload": {
                    "id": THREAD_ID,
                    "cwd": str(self.repo_root),
                    "model": "gpt-5.5",
                },
            },
            {
                "timestamp": "2026-06-07T10:00:01.000Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "turn-permission"},
            },
            {
                "timestamp": "2026-06-07T10:00:02.000Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "exec_command",
                    "call_id": "call_run_command",
                    "arguments": json.dumps(
                        {
                            "command": "git status --short",
                            "workdir": str(self.repo_root),
                            "message": "是否运行此命令？",
                        },
                        ensure_ascii=False,
                    ),
                },
            },
        ]

    def generic_permission_rows(self, args: dict, call_id: str = "call_generic_permission", tool_name: str = "browser.open") -> list[dict]:
        return [
            {
                "timestamp": "2026-06-07T10:00:00.000Z",
                "type": "session_meta",
                "payload": {
                    "id": THREAD_ID,
                    "cwd": str(self.repo_root),
                    "model": "gpt-5.5",
                },
            },
            {
                "timestamp": "2026-06-07T10:00:01.000Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "turn-permission"},
            },
            {
                "timestamp": "2026-06-07T10:00:02.000Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": tool_name,
                    "call_id": call_id,
                    "arguments": json.dumps(args, ensure_ascii=False),
                },
            },
        ]

    def test_permission_request_and_resolution(self) -> None:
        write_jsonl(self.session_path, self.permission_rows())
        response = parse_status(self.settings, thread_id=THREAD_ID)
        self.assertTrue(response["ok"])
        self.assertEqual(response["status"], "permission_required")
        self.assertTrue(response["active"])
        self.assertIsNotNone(response["permissionRequest"])
        self.assertTrue(response["permissionRequest"]["pending"])
        self.assertEqual([action["id"] for action in response["permissionRequest"]["actions"]], ["allow", "allow_always", "deny"])
        self.assertRegex(response["preview"], "权限|授权|允许|确认")
        self.assertTrue(any(step["kind"] == "permission" and step["pending"] for step in response["steps"]))

        write_jsonl(
            self.session_path,
            self.permission_rows(
                [
                    {
                        "timestamp": "2026-06-07T10:00:03.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": "call_permission",
                            "output": "Chunk ID: ok\nWall time: 0.0000 seconds\nProcess exited with code 0\nOutput:\n",
                        },
                    }
                ]
            ),
        )
        after_approval = parse_status(self.settings, thread_id=THREAD_ID)
        self.assertEqual(after_approval["status"], "running")
        self.assertIsNone(after_approval["permissionRequest"])
        self.assertTrue(any(step["kind"] == "permission" and not step["pending"] for step in after_approval["steps"]))

    def test_permission_action_aliases(self) -> None:
        self.assertEqual(normalize_permission_action("1"), "allow")
        self.assertEqual(normalize_permission_action("2"), "allow_always")
        self.assertEqual(normalize_permission_action("3"), "deny")
        self.assertEqual(normalize_permission_action("一"), "allow")
        self.assertEqual(normalize_permission_action("二"), "allow_always")
        self.assertEqual(normalize_permission_action("三"), "deny")
        self.assertEqual(normalize_permission_action("continue"), "allow")
        self.assertEqual(normalize_permission_action("allow-always"), "allow_always")
        self.assertEqual(normalize_permission_action("always_allow"), "allow_always")
        self.assertEqual(normalize_permission_action("cancel"), "deny")

    def test_chinese_run_command_prompt_is_permission_request(self) -> None:
        write_jsonl(self.session_path, self.chinese_run_command_permission_rows())
        response = parse_status(self.settings, thread_id=THREAD_ID)
        self.assertEqual(response["status"], "permission_required")
        self.assertIsNotNone(response["permissionRequest"])
        self.assertEqual(response["permissionRequest"]["command"], "git status --short")
        self.assertIn("是否运行此命令", response["permissionRequest"]["justification"])
        self.assertTrue(any(step["kind"] == "permission" and step["pending"] for step in response["steps"]))

    def test_browser_permission_prompt_is_permission_request(self) -> None:
        write_jsonl(
            self.session_path,
            self.generic_permission_rows(
                {
                    "url": "https://example.com",
                    "question": "是否打开浏览器访问这个网站？",
                },
                tool_name="browser.open_url",
            ),
        )
        response = parse_status(self.settings, thread_id=THREAD_ID)
        self.assertEqual(response["status"], "permission_required")
        self.assertEqual(response["permissionRequest"]["subject"], "https://example.com")
        self.assertIn("是否打开浏览器", response["permissionRequest"]["justification"])

    def test_apply_changes_prompt_is_permission_request(self) -> None:
        write_jsonl(
            self.session_path,
            self.generic_permission_rows(
                {
                    "message": "是否应用这些更改？",
                    "path": str(self.repo_root / "codex_go" / "cdp" / "dom.py"),
                },
                tool_name="apply_patch",
            ),
        )
        response = parse_status(self.settings, thread_id=THREAD_ID)
        self.assertEqual(response["status"], "permission_required")
        self.assertIsNotNone(response["permissionRequest"])
        self.assertIn("是否应用这些更改", response["permissionRequest"]["justification"])

    def test_permission_flag_without_command_is_permission_request(self) -> None:
        write_jsonl(
            self.session_path,
            self.generic_permission_rows(
                {
                    "tool": "browser",
                    "requires_approval": True,
                    "message": "是否使用浏览器？",
                },
                tool_name="browser.control",
            ),
        )
        response = parse_status(self.settings, thread_id=THREAD_ID)
        self.assertEqual(response["status"], "permission_required")
        self.assertEqual(response["permissionRequest"]["subject"], "browser")
        self.assertIn("是否使用浏览器", response["permissionRequest"]["justification"])


if __name__ == "__main__":
    unittest.main()
