from __future__ import annotations

from collections.abc import Callable
from typing import Any
import json
import os
import tempfile

from codex_go.config import Settings


def empty_state() -> dict[str, Any]:
    return {
        "pinnedThreadIds": [],
        "archivedThreadIds": [],
        "archivedThreadDetails": {},
        "titleOverrides": {},
        "appearanceSettings": {"colorFlowEnabled": True},
        "guiFailureReports": {},
    }


class StateStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.settings.paths.state_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return empty_state()
        except OSError:
            return empty_state()
        except json.JSONDecodeError:
            return empty_state()
        state = empty_state()
        state.update(data)
        for key in ("pinnedThreadIds", "archivedThreadIds"):
            if not isinstance(state.get(key), list):
                state[key] = []
        if not isinstance(state.get("archivedThreadDetails"), dict):
            state["archivedThreadDetails"] = {}
        if not isinstance(state.get("titleOverrides"), dict):
            state["titleOverrides"] = {}
        if not isinstance(state.get("appearanceSettings"), dict):
            state["appearanceSettings"] = {"colorFlowEnabled": True}
        elif "colorFlowEnabled" not in state["appearanceSettings"]:
            state["appearanceSettings"]["colorFlowEnabled"] = True
        if not isinstance(state.get("guiFailureReports"), dict):
            state["guiFailureReports"] = {}
        return state

    def write(self, state: dict[str, Any]) -> None:
        self.settings.paths.state_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix="state-", suffix=".json", dir=self.settings.paths.state_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(tmp_name, self.settings.paths.state_file)
        finally:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass

    def update(self, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
        state = fn(self.read())
        self.write(state)
        return state
