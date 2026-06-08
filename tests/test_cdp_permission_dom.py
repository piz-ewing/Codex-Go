#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codex_go.cdp.dom import permission_action_expression, read_gui_status_expression


class CdpPermissionDomTest(unittest.TestCase):
    def test_gui_status_detects_apply_changes_confirmation(self) -> None:
        expression = read_gui_status_expression("11111111-2222-3333-4444-555555555555")

        self.assertIn("findGuiPermissionRequest", expression)
        self.assertIn("是否应用这些更改", expression)
        self.assertIn("应用这些更改", expression)
        self.assertIn("apply (these )?(changes|edits|patch)", expression)
        self.assertIn("source: 'gui'", expression)

    def test_permission_action_allows_option_flow_without_enabled_submit(self) -> None:
        expression = permission_action_expression("allow", "", "是否应用这些更改？")

        self.assertIn("enabledSubmitNear", expression)
        self.assertIn("!isDisabled(submit.button)", expression)
        self.assertIn("resolvedWithoutSubmit: true", expression)
        self.assertNotIn("已选择权限选项，但提交按钮尚不可用", expression)
        self.assertIn("应用.*(更改|修改|补丁)", expression)
        self.assertIn("apply.*(changes|edits|patch)", expression)
        self.assertIn("[role=\"radio\"]", expression)
        self.assertIn("containers.length ? containers.map", expression)

    def test_direct_permission_buttons_do_not_use_submit_flow(self) -> None:
        expression = permission_action_expression("allow", "git status", "Do you want to allow this command?")

        self.assertIn("const selectableOptionSelector = '[role=\"radio\"],[role=\"menuitemradio\"],label';", expression)
        self.assertIn("root.querySelectorAll(selectableOptionSelector)", expression)
        self.assertIn("submitNear(button, true, container.el)", expression)
        self.assertIn("if (!container) continue;", expression)
        self.assertNotIn("button,[role=\"button\"],[role=\"radio\"],[role=\"menuitemradio\"],label", expression)
        self.assertNotIn("return [...document.querySelectorAll('button,[role=\"button\"]')]", expression)


if __name__ == "__main__":
    unittest.main()
