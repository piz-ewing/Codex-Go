#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class ThemeSettingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
        cls.app_js = (ROOT / "public" / "js" / "app.js").read_text(encoding="utf-8")
        cls.base_css = (ROOT / "public" / "css" / "app.css").read_text(encoding="utf-8")
        cls.theme_css = {
            path.stem: path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "public" / "css" / "themes").glob("*.css"))
        }

    def load_api_config_body(self) -> str:
        match = re.search(
            r"async function loadApiConfig\(\) \{(?P<body>[\s\S]*?)\nasync function refreshApiConfigIfNeeded",
            self.app_js,
        )
        self.assertIsNotNone(match, "loadApiConfig should stay explicit")
        return match.group("body")

    def test_theme_dropdown_exposes_all_theme_options(self) -> None:
        for value in ("native", "workbench", "minimal", "dark", "luxe-dark", "dracula"):
            self.assertIn(f'<option value="{value}">', self.html)
        self.assertIn("const THEME_OPTIONS = ['native', 'workbench', 'minimal', 'dark', 'luxe-dark', 'dracula'];", self.app_js)

    def test_theme_styles_are_loaded_from_independent_css_files(self) -> None:
        expected = ("native", "workbench", "minimal", "dark", "luxe-dark", "dracula")
        for theme in expected:
            self.assertIn(f'href="css/themes/{theme}.css?', self.html)
            self.assertIn(theme, self.theme_css, f"missing theme css file for {theme}")
        self.assertNotIn("body.theme-workbench", self.base_css)
        self.assertNotIn("body.theme-minimal", self.base_css)
        self.assertNotIn("body.theme-dark", self.base_css)
        self.assertNotIn("body.theme-luxe-dark", self.base_css)
        self.assertNotIn("body.theme-dracula", self.base_css)

    def test_local_theme_preference_wins_over_api_config_defaults(self) -> None:
        body = self.load_api_config_body()
        appearance_start = body.find("if (data.appearanceSettings)")
        model_start = body.find("if (Array.isArray(data.modelOptions)")
        self.assertGreaterEqual(appearance_start, 0, "config loading should handle appearance settings")
        self.assertGreater(model_start, appearance_start, "appearance handling should finish before model options")
        block = body[appearance_start:model_start]

        local_guard = block.find("if (hasLocalAppearanceSettings)")
        keep_local = block.find("appearanceSettings = normalizeAppearanceSettings(appearanceSettings);")
        use_remote = block.find("appearanceSettings = normalizeAppearanceSettings(data.appearanceSettings);")
        self.assertGreaterEqual(local_guard, 0, "local theme settings must guard remote defaults")
        self.assertGreater(keep_local, local_guard, "local settings should be normalized under the local guard")
        self.assertGreater(use_remote, keep_local, "remote config should only be used in the fallback branch")
        self.assertNotIn("isAndroidKeyboardBrowser && hasLocalAppearanceSettings", block)
        self.assertNotIn("persistAppearanceSettingsLocal();", block)

    def test_dark_theme_context_ring_has_distinct_pie_style(self) -> None:
        dark_css = self.theme_css["dark"]
        self.assertIn("body.theme-dark .context-status.level-medium", dark_css)
        self.assertIn("--context-dark-accent: #79c7e8;", dark_css)
        self.assertRegex(
            dark_css,
            r"body\.theme-dark \.context-ring \{[\s\S]*?width: 28px;[\s\S]*?conic-gradient\(from -132deg",
        )

    def test_dracula_theme_uses_eye_care_palette(self) -> None:
        dracula_css = self.theme_css["dracula"]
        self.assertIn("--bg: #282a36;", dracula_css)
        self.assertIn("--text: #f8f8f2;", dracula_css)
        self.assertIn("--ok: #50fa7b;", dracula_css)
        self.assertIn("body.theme-dracula .markdown-body a", dracula_css)
        self.assertIn("color: #8be9fd;", dracula_css)
        self.assertIn("background: #bd93f9;", dracula_css)

    def test_dark_themes_style_attachment_chips(self) -> None:
        for theme in ("dark", "luxe-dark", "dracula"):
            css = self.theme_css[theme]
            self.assertIn(f"body.theme-{theme} .attachment-chip", css)
            self.assertNotIn("background: #eeeeea;", css)

    def test_luxe_dark_theme_restores_flowing_dark_style(self) -> None:
        luxe_css = self.theme_css["luxe-dark"]
        self.assertIn("body.theme-luxe-dark.color-flow-on .composer::before", luxe_css)
        self.assertIn("animation: colorFlow 4.8s ease-in-out infinite;", luxe_css)
        self.assertIn("--color-flow-tint-a: color(display-p3 .67 .90 .82);", luxe_css)

    def test_dark_theme_icon_paths_survive_theme_css_split(self) -> None:
        for theme in ("dark", "luxe-dark", "dracula"):
            css = self.theme_css[theme]
            self.assertIn('url("../../icons/dark/icon-32.png', css)
            self.assertNotIn('url("../icons/dark/icon-32.png', css)
        self.assertIn("return isDarkTheme(theme) ? 'icons/dark' : 'icons';", self.app_js)

    def test_luxe_dark_attachment_icon_keeps_svg_visible(self) -> None:
        luxe_css = self.theme_css["luxe-dark"]
        match = re.search(
            r"body\.theme-luxe-dark\.color-flow-on \.icon-btn \{(?P<body>[\s\S]*?)\n\}",
            luxe_css,
        )
        self.assertIsNotNone(match, "luxe dark should style icon buttons explicitly")
        block = match.group("body")
        self.assertIn("color: #d9ffe9;", block)
        self.assertIn("-webkit-text-fill-color: currentColor;", block)
        self.assertIsNone(re.search(r"(?m)^\s*color:\s*transparent;", block))
        self.assertIn("body.theme-luxe-dark.color-flow-on .icon-btn svg", luxe_css)
        self.assertIn("stroke: currentColor;", luxe_css)

    def test_luxe_dark_primary_actions_are_not_black_blocks(self) -> None:
        luxe_css = self.theme_css["luxe-dark"]
        primary_match = re.search(
            r"body\.theme-luxe-dark \.permission-action-btn\.is-primary,[\s\S]*?body\.theme-luxe-dark \.reasoning-menu-item\.is-current \{(?P<body>[\s\S]*?)\n\}",
            luxe_css,
        )
        self.assertIsNotNone(primary_match, "luxe dark should style primary action surfaces")
        primary_block = primary_match.group("body")
        self.assertIn("background: var(--luxe-action-bg);", primary_block)
        self.assertIn("color: var(--luxe-action-fg);", primary_block)
        self.assertIn("box-shadow: var(--luxe-action-shadow);", primary_block)
        for selector in (
            ".queued-send-action.is-primary",
            ".thread-action-button.is-blue",
            ".context-quick-card",
            ".model-menu-item.is-current",
            ".reasoning-menu-item.is-current",
        ):
            self.assertIn(f"body.theme-luxe-dark {selector}", luxe_css)
        self.assertIn("body.theme-luxe-dark .message.guided-send-note .bubble", luxe_css)
        self.assertIn("color: #d9ffe9;", luxe_css)
        self.assertIn("body.theme-luxe-dark .settings-switch.is-on", luxe_css)
        self.assertIn("background: var(--luxe-action-bg);", luxe_css)

    def test_luxe_dark_settings_and_notices_use_obsidian_glass(self) -> None:
        luxe_css = self.theme_css["luxe-dark"]
        self.assertIn("--luxe-glass-bg: linear-gradient(180deg, rgba(18,20,23,.98), rgba(8,10,12,.96));", luxe_css)
        self.assertIn("body.theme-luxe-dark .settings-card", luxe_css)
        self.assertIn("background: var(--luxe-glass-bg);", luxe_css)
        self.assertIn("body.theme-luxe-dark .notice-pill", luxe_css)
        self.assertIn("body.theme-luxe-dark .notice-pill.error", luxe_css)
        self.assertIn("body.theme-luxe-dark .message.guided-send-note .bubble", luxe_css)
        self.assertIn("background: linear-gradient(180deg, rgba(18,20,23,.92), rgba(10,12,14,.88));", luxe_css)


if __name__ == "__main__":
    unittest.main()
