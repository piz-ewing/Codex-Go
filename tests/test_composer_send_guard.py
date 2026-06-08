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
        cls.app_css = (ROOT / "public" / "css" / "app.css").read_text(encoding="utf-8")
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

    def test_keyboard_open_shrinks_app_without_repinning_thread_container(self) -> None:
        self.assertNotIn("--keyboard-stage-height", self.app_css)
        self.assertNotIn("setKeyboardStageHeight", self.app_js)
        self.assertIn("function keyboardAppHeight(layoutHeight, keyboardOpen, overlayBottom = 0) {", self.app_js)
        self.assertIn("const viewportHeight = Math.round(viewport?.height || 0);", self.app_js)
        self.assertIn("return Math.max(1, Math.min(layoutHeight, ...candidates));", self.app_js)
        self.assertIn(
            "document.documentElement.style.setProperty('--app-height', `${keyboardAppHeight(layoutHeight, keyboardOpen, overlayBottom)}px`);",
            self.app_js,
        )
        stage_match = re.search(
            r"body\.mobile-keyboard-mode\.keyboard-open \.stage \{(?P<body>[\s\S]*?)\n\}",
            self.app_css,
        )
        self.assertIsNotNone(stage_match, "keyboard-open stage rule should stay explicit")
        stage_body = stage_match.group("body")
        self.assertIn("grid-template-rows: minmax(0, 1fr) var(--composer-stack-height);", stage_body)
        self.assertNotIn("height:", stage_body)
        self.assertNotIn("max-height:", stage_body)
        composer_match = re.search(
            r"body\.mobile-keyboard-mode\.keyboard-open \.composer-stack \{(?P<body>[\s\S]*?)\n\}",
            self.app_css,
        )
        self.assertIsNotNone(composer_match, "keyboard-open composer rule should stay explicit")
        composer_body = composer_match.group("body")
        self.assertNotIn("position: fixed", composer_body)
        self.assertNotIn("bottom:", composer_body)

    def test_keyboard_alignment_does_not_scroll_thread(self) -> None:
        self.assertNotIn("thread.scrollTop = thread.scrollHeight", self.app_js)
        match = re.search(
            r"function alignComposerForKeyboard\(\) \{(?P<body>[\s\S]*?)\nfunction scheduleKeyboardAlignment",
            self.app_js,
        )
        self.assertIsNotNone(match, "keyboard alignment should stay explicit")
        body = match.group("body")
        self.assertNotIn("thread.scrollTop", body)
        self.assertNotIn("scrollThreadToBottom", body)
        self.assertNotIn("restoreThreadScrollAnchor", body)
        self.assertNotIn("captureThreadScrollAnchor", body)
        self.assertIn("const keyboardOpen = applyViewportSize();", body)
        self.assertIn("keyboardOverlayOpen = keyboardOpen;", body)

    def test_keyboard_resize_does_not_reuse_bottom_stickiness(self) -> None:
        match = re.search(
            r"function shouldStickThreadToBottomOnResize\(\) \{(?P<body>[\s\S]*?)\n\}",
            self.app_js,
        )
        self.assertIsNotNone(match, "resize bottom-stick guard should stay explicit")
        body = match.group("body")
        self.assertIn("if (Date.now() >= threadStickToBottomUntil) return false;", body)
        self.assertIn("if (document.body.classList.contains('keyboard-open')) return false;", body)
        self.assertIn("document.activeElement === textarea || keyboardFocusStartedAt", body)
        self.assertRegex(
            self.app_js,
            r"function handleWindowResize\(\) \{[\s\S]*?if \(shouldStickThreadToBottomOnResize\(\)\) \{\s*scrollThreadToBottom\(true\);",
        )

    def test_first_textarea_tap_uses_prevent_scroll_focus(self) -> None:
        self.assertNotIn("function shouldUseNativeTextareaFocus", self.app_js)
        match = re.search(
            r"function prepareTextareaFocus\(event\) \{(?P<body>[\s\S]*?)\n\}",
            self.app_js,
        )
        self.assertIsNotNone(match, "textarea focus preparation should stay explicit")
        body = match.group("body")
        prevent_index = body.find("if (event && event.cancelable) event.preventDefault();")
        focus_index = body.find("textarea.focus({ preventScroll: true });")
        edit_index = body.find("if (nativeTextareaEdit)")
        self.assertGreaterEqual(edit_index, 0, "already-focused textarea edits should remain native")
        self.assertGreater(prevent_index, edit_index, "new textarea focus should prevent native page scroll")
        self.assertGreater(focus_index, prevent_index, "new textarea focus should use preventScroll")
        self.assertNotIn("nativeTextareaFocus", body)

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

    def test_queued_send_edit_deletes_and_moves_text_to_composer(self) -> None:
        self.assertIn("function moveQueuedSendToComposer(text) {", self.app_js)
        self.assertIn("textarea.value = value;", self.app_js)
        self.assertIn("saveComposerDraftForKey();", self.app_js)
        self.assertIn("const backendAction = action === 'edit' ? 'delete' : action;", self.app_js)
        self.assertIn("if (action === 'edit') moveQueuedSendToComposer(text);", self.app_js)
        self.assertIn("edit.textContent = editBusy ? '处理中' : '编辑';", self.app_js)
        self.assertIn("runQueuedSendAction('edit', itemText);", self.app_js)
        self.assertIn("actions.append(guide, edit, remove);", self.app_js)
        self.assertNotIn("sendText({ text", self.app_js)


if __name__ == "__main__":
    unittest.main()
