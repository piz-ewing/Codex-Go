#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codex_go.cdp.dom import attach_files_after_set_expression, attachment_drop_target_expression, attachment_snapshot_expression


class CdpAttachmentEventTest(unittest.TestCase):
    def test_attachment_events_do_not_broadcast_one_file_to_many_targets(self) -> None:
        expression = attach_files_after_set_expression(1)

        self.assertIn("dispatch(input, new Event('input'", expression)
        self.assertIn("dispatch(input, new Event('change'", expression)
        self.assertIn("if (injected && dropTarget)", expression)
        self.assertNotIn("for (const target of targets.filter", expression)
        self.assertNotIn("new ClipboardEvent('paste'", expression)

    def test_native_drag_helpers_do_not_build_synthetic_file_payloads(self) -> None:
        drop_expression = attachment_drop_target_expression()
        snapshot_expression = attachment_snapshot_expression(
            [
                {
                    "path": "/tmp/shot.png",
                    "name": "shot.png",
                    "type": "image/png",
                }
            ]
        )
        expression = drop_expression + snapshot_expression

        self.assertIn("getBoundingClientRect()", drop_expression)
        self.assertIn("matchedNames", snapshot_expression)
        self.assertIn("likelyCount", snapshot_expression)
        self.assertNotIn("decodeBase64", expression)
        self.assertNotIn("new File(", expression)
        self.assertNotIn("new Event('paste'", expression)
        self.assertNotIn("Object.defineProperty(event, 'clipboardData'", expression)
        self.assertNotIn("input.type = 'file'", expression)
        self.assertNotIn("new ClipboardEvent('paste'", expression)


if __name__ == "__main__":
    unittest.main()
