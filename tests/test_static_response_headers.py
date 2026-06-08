#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP_SOURCE = ROOT / "codex_go" / "api" / "app.py"


class StaticResponseHeaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = APP_SOURCE.read_text(encoding="utf-8")

    def test_static_files_use_mime_type_with_octet_stream_fallback(self) -> None:
        self.assertRegex(
            self.source,
            r"mimetypes\.guess_type\(str\(resolved\)\)\[0\]\s+or\s+\"application/octet-stream\"",
        )

    def test_static_files_set_cache_control_for_dynamic_assets(self) -> None:
        self.assertRegex(
            self.source,
            r"resolved\.suffix in \{\"\.html\", \"\.js\", \"\.css\", \"\.webmanifest\"\}:[\s\S]*?\"Cache-Control\"\]\s*=\s*\"no-store\"",
        )

    def test_static_files_set_cache_control_for_other_assets(self) -> None:
        self.assertIn('response.headers["Cache-Control"] = "public, max-age=3600"', self.source)

    def test_static_files_set_content_length(self) -> None:
        self.assertRegex(self.source, r"stat = resolved\.stat\(\)")
        self.assertRegex(self.source, r"response\.headers\[\"Content-Length\"\]\s*=\s*str\(stat\.st_size\)")


if __name__ == "__main__":
    unittest.main()
