#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class ThreadMenuRenderingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app_js = (ROOT / "public" / "js" / "app.js").read_text(encoding="utf-8")

    def test_selected_project_does_not_reorder_project_groups(self) -> None:
        match = re.search(
            r"const projectGroups = \[\.\.\.projectMap\.values\(\)\]\.sort\(\((?P<args>[^)]*)\) => (?P<body>[^;]+)\);",
            self.app_js,
        )
        self.assertIsNotNone(match, "thread menu should sort project groups explicitly")
        self.assertNotIn(
            "currentProjectKey",
            match.group("body"),
            "selecting a thread must not move its project group to the top of the sidebar",
        )
        self.assertIn("b.latest - a.latest", match.group("body"))
        self.assertIn("label.textContent = '项目';", self.app_js)


if __name__ == "__main__":
    unittest.main()
