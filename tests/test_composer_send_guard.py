#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class ComposerSendGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
        cls.app_js = (ROOT / "public" / "js" / "app.js").read_text(encoding="utf-8")

    def assert_matches(self, pattern: str, message: str) -> None:
        self.assertRegex(self.app_js, pattern, message)

    def test_send_button_is_not_native_submit(self) -> None:
        self.assertIn('<button class="send-btn" id="send" type="button"', self.html)
        self.assertRegex(self.html, r'<script src="js/app\.js\?v=[0-9a-z]+"></script>')

    def test_native_submit_is_only_suppressed(self) -> None:
        self.assert_matches(
            r"composer\.addEventListener\('submit',\s*event\s*=>\s*\{\s*event\.preventDefault\(\);\s*\}\);",
            "composer submit handler should only suppress native submit",
        )
        self.assert_matches(
            r"if \(!hasTextOverride && options\.userInitiated !== true\) return;",
            "sendText must reject composer text sends that were not explicitly user initiated",
        )

    def test_ime_enter_does_not_send(self) -> None:
        self.assert_matches(r"let composerImeActive = false;", "composer must track active IME composition state")
        self.assert_matches(
            r"textarea\.addEventListener\('compositionstart',\s*\(\)\s*=>\s*\{\s*composerImeActive = true;",
            "composer must mark IME composition as active",
        )
        self.assert_matches(
            r"textarea\.addEventListener\('compositionend',\s*\(\)\s*=>\s*\{\s*composerImeActive = false;\s*composerImeEndedAt = Date\.now\(\);",
            "composer must remember recent IME composition end",
        )
        self.assert_matches(
            r"function isComposerImeEnter\(event\) \{[\s\S]*event\.keyCode === 229[\s\S]*event\.which === 229[\s\S]*Date\.now\(\) - composerImeEndedAt < 250[\s\S]*\}",
            "composer must treat IME Enter and recent composition-end Enter as non-send input",
        )
        self.assert_matches(
            r"if \(event\.key === 'Enter' && !event\.shiftKey\) \{\s*if \(isComposerImeEnter\(event\)\)",
            "Enter handler must check IME state before sending",
        )

    def test_focused_textarea_rearm_does_not_interrupt_keyboard_start(self) -> None:
        self.assertIn("function shouldRearmFocusedTextarea(now) {", self.app_js)
        self.assert_matches(
            r"if \(composerImeActive \|\| Date\.now\(\) - composerImeEndedAt < 600\) return false;",
            "focused textarea rearm must not interrupt active or just-finished IME composition",
        )
        self.assert_matches(
            r"if \(keyboardFocusStartedAt && now - keyboardFocusStartedAt < 1600\) return false;",
            "focused textarea rearm must not run while the mobile keyboard is still opening",
        )
        self.assert_matches(
            r"if \(lastTextareaFocusPrepareAt && now - lastTextareaFocusPrepareAt < 350\) return false;",
            "focused textarea rearm must ignore duplicate touch/pointer events from the same tap",
        )

    def test_keyboard_open_requires_real_viewport_evidence(self) -> None:
        match = re.search(
            r"function isMobileKeyboardLikelyOpen\(focused, keyboardBottom\) \{(?P<body>[\s\S]*?)\n\}",
            self.app_js,
        )
        self.assertIsNotNone(match, "mobile keyboard detection should stay explicit")
        body = match.group("body")
        self.assertIn("if (keyboardBottom > 20) return true;", body)
        self.assertIn("return layoutHeight - viewportHeight > 20 || layoutViewportBaselineHeight - viewportHeight > 20;", body)
        self.assertNotIn("keyboardFocusStartedAt", body, "focus grace must not mark the keyboard open before viewport evidence")

    def test_direct_textarea_tap_uses_native_focus(self) -> None:
        self.assertIn("function shouldUseNativeTextareaFocus(event, alreadyFocused) {", self.app_js)
        self.assert_matches(
            r"return Boolean\(event && event\.target === textarea && !alreadyFocused\);",
            "direct mobile textarea taps should be left to native browser focus",
        )
        match = re.search(
            r"function prepareTextareaFocus\(event\) \{(?P<body>[\s\S]*?)\n\}",
            self.app_js,
        )
        self.assertIsNotNone(match, "textarea focus preparation should stay explicit")
        body = match.group("body")
        native_index = body.find("if (nativeTextareaFocus)")
        prevent_index = body.find("if (event && event.cancelable) event.preventDefault();")
        focus_index = body.find("textarea.focus({ preventScroll: true });")
        self.assertGreaterEqual(native_index, 0, "prepareTextareaFocus should branch for native textarea focus")
        self.assertGreater(prevent_index, native_index, "native textarea focus branch should run before preventDefault")
        self.assertGreater(focus_index, native_index, "native textarea focus branch should run before programmatic focus")

    def test_textarea_touchmove_is_left_to_native_handling(self) -> None:
        match = re.search(
            r"function lockPageScrollToThread\(\) \{(?P<body>[\s\S]*?)\nfunction clampNumber",
            self.app_js,
        )
        self.assertIsNotNone(match, "page scroll lock should stay explicit")
        body = match.group("body")
        self.assertIn("if (editableTarget) {", body)
        self.assertIn("pageTouch.x = touch.clientX;", body)
        self.assertIn("pageTouch.y = touch.clientY;", body)
        editable_block = body[body.find("if (editableTarget) {") : body.find("if (horizontalTarget")]
        self.assertNotIn("preventPageMove(event)", editable_block, "textarea touchmove must not cancel native focus/keyboard handling")
        self.assertNotIn("keepLayoutViewportPinned()", editable_block, "textarea touchmove must not fight native keyboard scroll")

    def test_send_text_calls_are_user_initiated_or_explicit_text(self) -> None:
        unsafe_calls = []
        for match in re.finditer(r"sendText\(([^)]*)\)", self.app_js):
            prefix = self.app_js[max(0, match.start() - 24) : match.start()]
            call = match.group(0)
            if re.search(r"function\s+$", prefix):
                continue
            if "text:" in call or "userInitiated: true" in call:
                continue
            unsafe_calls.append(call)
        self.assertEqual(unsafe_calls, [], f"found unsafe composer sendText calls: {', '.join(unsafe_calls)}")

    def test_unauthorized_response_clears_stale_token(self) -> None:
        self.assertIn("function handleUnauthorizedResponse()", self.app_js)
        self.assertIn("localStorage.removeItem('codexGo.token')", self.app_js)
        self.assertRegex(self.app_js, r"if \(response\.status === 401\) handleUnauthorizedResponse\(\);")

    def test_new_thread_button_only_creates_frontend_draft(self) -> None:
        match = re.search(
            r"function createNewThreadInCurrentProject\(\) \{(?P<body>[\s\S]*?)\n\}",
            self.app_js,
        )
        self.assertIsNotNone(match, "new-thread handler should be a synchronous frontend draft transition")
        body = match.group("body")
        self.assertIn("pendingNewThread = {", body)
        self.assertNotIn("fetchApi('/codex/new-thread'", body)
        self.assertNotIn("await ensureRouteForSend", body)

    def test_first_draft_send_carries_new_thread_target(self) -> None:
        self.assertRegex(self.app_js, r"const isPendingNewThreadFirstSend = isPendingNewThreadView\(\);")
        self.assertRegex(self.app_js, r"if \(!isPendingNewThreadFirstSend\) \{\s*await syncCodexThread")
        self.assertIn("expectNewThread: isPendingNewThreadFirstSend", self.app_js)
        self.assertIn("previousThreadId: pendingNewThread?.previousThreadId || ''", self.app_js)
        self.assertIn("newThreadScope: pendingNewThread?.scope || ''", self.app_js)
        self.assertIn("projectPath: pendingNewThread?.projectPath || ''", self.app_js)

    def test_permission_actions_use_backend_available_actions(self) -> None:
        self.assertRegex(
            self.app_js,
            r"const availableActions = Array\.isArray\(request\.actions\) && request\.actions\.length\s*\?\s*request\.actions\s*:\s*\[\{ id: 'allow' \}, \{ id: 'allow_always' \}, \{ id: 'deny' \}\];",
        )
        self.assertIn("data.permissionRequest?.callId || ''", self.app_js)


if __name__ == "__main__":
    unittest.main()
