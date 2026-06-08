#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codex_go.codex.status_parser import quick_runtime_from_items


class ThreadListSortTest(unittest.TestCase):
    def test_list_sort_uses_user_and_complete_events_not_streaming(self) -> None:
        items = [
            {"type": "event_msg", "timestamp": "2026-06-08T10:00:00Z", "payload": {"type": "user_message", "message": "hello"}},
            {"type": "event_msg", "timestamp": "2026-06-08T10:00:01Z", "payload": {"type": "task_started", "turn_id": "turn-1"}},
            {"type": "response_item", "timestamp": "2026-06-08T10:00:05Z", "payload": {"type": "message", "role": "assistant", "phase": "final_answer", "content": "hi"}},
            {"type": "event_msg", "timestamp": "2026-06-08T10:00:10Z", "payload": {"type": "task_complete", "last_agent_message": "done"}},
        ]
        runtime = quick_runtime_from_items(items, mtime=1_700_000_000.0)
        self.assertEqual(runtime["listSortUpdatedAt"], "2026-06-08T10:00:10Z")
        self.assertEqual(runtime["status"], "complete")


if __name__ == "__main__":
    unittest.main()
