#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codex_go.codex.models import (
    codex_menu_display_name,
    default_model_catalog_options,
    footer_label_from_menu_text,
    merge_model_option_lists,
    model_options_from_display_names,
    read_model_catalog_options,
)
from codex_go.config import load_settings


class ModelCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="codex-go-model-catalog-"))
        self.env_backup = os.environ.copy()
        self.codex_home = self.temp_root / ".codex"
        self.codex_home.mkdir(parents=True, exist_ok=True)
        os.environ["CODEX_GO_CODEX_HOME"] = str(self.codex_home)
        os.environ["CODEX_GO_SESSIONS_DIR"] = str(self.codex_home / "sessions")
        os.environ["CODEX_GO_SESSION_INDEX"] = str(self.codex_home / "session_index.jsonl")
        os.environ["CODEX_GO_STATE_DIR"] = str(self.temp_root / ".codex-go")
        os.environ["CODEX_GO_PUBLIC_DIR"] = str(ROOT / "public")

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.env_backup)

    def test_default_catalog_includes_official_models(self):
        options = default_model_catalog_options("gpt-5.5")
        labels = [item["label"] for item in options]
        self.assertIn("5.5", labels)
        self.assertIn("5.4", labels)
        self.assertIn("5.3", labels)
        self.assertGreaterEqual(len(options), 5)

    def test_read_catalog_without_model_catalog_json_uses_defaults(self):
        (self.codex_home / "config.toml").write_text('model = "gpt-5.5"\n', encoding="utf-8")
        settings = load_settings()
        options = read_model_catalog_options(settings)
        self.assertGreaterEqual(len(options), 5)
        self.assertEqual(options[0]["id"], "gpt-5.5")

    def test_model_options_from_display_names(self):
        settings = load_settings()
        options = model_options_from_display_names(settings, ["GPT-5.4", "GPT-5.3 Codex"])
        labels = [item["label"] for item in options]
        self.assertIn("5.4", labels)
        self.assertIn("5.3", labels)

    def test_merge_model_option_lists_prefers_primary_order(self):
        primary = [{"key": "gpt-5.4", "id": "gpt-5.4", "label": "5.4", "displayName": "GPT-5.4"}]
        secondary = [
            {"key": "gpt-5.5", "id": "gpt-5.5", "label": "5.5", "displayName": "GPT-5.5"},
            {"key": "gpt-5.4", "id": "gpt-5.4", "label": "5.4", "displayName": "GPT-5.4"},
        ]
        merged = merge_model_option_lists(primary, secondary)
        self.assertEqual([item["id"] for item in merged], ["gpt-5.4", "gpt-5.5"])

    def test_footer_label_from_menu_text_matches_codex_footer(self):
        self.assertEqual(footer_label_from_menu_text("GPT-5.4"), "5.4")
        self.assertEqual(footer_label_from_menu_text("GPT-5.4-Mini"), "5.4-Mini")
        self.assertEqual(footer_label_from_menu_text("GPT-5.3-Codex"), "5.3-Codex")

    def test_codex_menu_display_name_normalizes_legacy_labels(self):
        self.assertEqual(codex_menu_display_name("GPT-5.4 Mini", "gpt-5.4-mini"), "GPT-5.4-Mini")
        self.assertEqual(codex_menu_display_name("", "gpt-5.3-codex"), "GPT-5.3-Codex")


if __name__ == "__main__":
    unittest.main()
