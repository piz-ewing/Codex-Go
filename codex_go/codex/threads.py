from __future__ import annotations

from pathlib import Path
import os
import time
from typing import Any

from codex_go.config import Settings
from codex_go.state.store import StateStore

from .session_store import SessionStore, thread_id_from_session_file
from .status_parser import quick_runtime_from_items
from .text import summarize_thread_title


def _display_path_name(cwd: str) -> str:
    if not cwd:
        return "对话"
    normalized = os.path.normpath(cwd)
    if normalized == str(Path.home()):
        return "~"
    return os.path.basename(normalized) or normalized


def classify_thread_project(cwd: str) -> dict[str, Any]:
    normalized = os.path.normpath(cwd) if cwd else ""
    scratch_root = Path.home() / "Documents" / "Codex"
    generated_projectless = False
    if normalized:
        try:
            rel = Path(normalized).relative_to(scratch_root)
            generated_projectless = bool(rel.parts and len(rel.parts[0]) >= 10 and rel.parts[0][4:5] == "-")
        except ValueError:
            generated_projectless = False
    if not normalized or generated_projectless:
        return {
            "isProjectThread": False,
            "projectKey": "conversation",
            "projectName": "对话",
            "projectPath": "",
        }
    return {
        "isProjectThread": True,
        "projectKey": normalized,
        "projectName": _display_path_name(normalized),
        "projectPath": normalized,
    }


def _first_user_message(store: SessionStore, file: Path, settings: Settings) -> str:
    items = store.read_jsonl_tail_objects(file, settings.limits.title_scan_bytes)
    for item in items:
        payload = item.get("payload") or {}
        if item.get("type") == "event_msg" and payload.get("type") == "user_message":
            title = summarize_thread_title(payload.get("message") or "")
            if title:
                return title
    return ""


def list_threads(settings: Settings, limit: int = 80) -> list[dict[str, Any]]:
    normalized_limit = max(1, min(160, int(limit or 80)))
    store = SessionStore(settings)
    state_store = StateStore(settings)
    state = state_store.read()
    pinned = set(state.get("pinnedThreadIds") or [])
    archived = set(state.get("archivedThreadIds") or [])
    archived_details = state.get("archivedThreadDetails") if isinstance(state.get("archivedThreadDetails"), dict) else {}
    title_overrides = state.get("titleOverrides") or {}
    by_id = store.read_thread_index()
    restored_archived: set[str] = set()

    for file in store.list_session_files():
        thread_id = thread_id_from_session_file(file)
        if not thread_id:
            continue
        try:
            stat = file.stat()
        except OSError:
            continue
        if thread_id in archived and _thread_restored_after_archive(thread_id, stat.st_mtime * 1000, archived_details):
            restored_archived.add(thread_id)
            archived.discard(thread_id)
        meta = store.read_session_meta(file)
        runtime = quick_runtime_from_items(store.read_jsonl_tail_objects(file, settings.limits.activity_tail_bytes), stat.st_mtime)
        existing = by_id.get(thread_id, {"id": thread_id, "name": "", "updatedAt": ""})
        if not existing.get("name") or str(existing.get("name")).strip() in {"新对话", "Untitled", "未命名线程"}:
            existing["name"] = _first_user_message(store, file, settings) or "未命名线程"
            existing["nameSource"] = "first_user_message"
        override = title_overrides.get(thread_id) if isinstance(title_overrides, dict) else None
        if isinstance(override, dict) and str(override.get("name") or "").strip():
            existing["name"] = str(override["name"]).strip()
            existing["nameSource"] = "codex_go_override"
        existing.update(classify_thread_project(str(meta.get("cwd") or "")))
        index_ms = _parse_time_ms(existing.get("updatedAt"))
        sort_ms = _parse_time_ms(runtime.get("listSortUpdatedAt"))
        updated_ms = max(index_ms, sort_ms)
        if updated_ms <= 0:
            updated_ms = stat.st_mtime * 1000
        existing.update(
            {
                "id": thread_id,
                "sessionFile": file.name,
                "mtimeMs": stat.st_mtime * 1000,
                "effectiveUpdatedMs": updated_ms,
                "effectiveUpdatedAt": _iso_from_ms(updated_ms),
                "cwd": meta.get("cwd") or "",
                "source": meta.get("source") or "",
                "threadSource": meta.get("thread_source") or "",
                "runtimeStatus": runtime["status"],
                "runtimeActive": runtime["active"],
                "runtimeStartedAt": runtime["startedAt"],
                "runtimeCompletedAt": runtime["completedAt"],
                "runtimeUpdatedAt": runtime["updatedAt"],
                "runtimeTurnId": runtime["turnId"],
                "pinned": thread_id in pinned,
            }
        )
        by_id[thread_id] = existing

    if restored_archived:
        def update(restored_state: dict[str, Any]) -> dict[str, Any]:
            remaining = [thread_id for thread_id in restored_state.get("archivedThreadIds") or [] if thread_id not in restored_archived]
            details = restored_state.get("archivedThreadDetails") if isinstance(restored_state.get("archivedThreadDetails"), dict) else {}
            for thread_id in restored_archived:
                details.pop(thread_id, None)
            restored_state["archivedThreadIds"] = remaining
            restored_state["archivedThreadDetails"] = details
            return restored_state

        state_store.update(update)

    rows = [
        item
        for item in by_id.values()
        if item.get("sessionFile") and item.get("id") not in archived
    ]
    rows.sort(key=lambda item: (bool(item.get("pinned")), item.get("effectiveUpdatedMs") or 0), reverse=True)
    return rows[:normalized_limit]


def _parse_time_ms(value: Any) -> float:
    if not value:
        return 0
    try:
        from datetime import datetime

        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000
    except Exception:
        return 0


def _thread_restored_after_archive(thread_id: str, session_mtime_ms: float, archived_details: dict[str, Any]) -> bool:
    details = archived_details.get(thread_id) if isinstance(archived_details, dict) else None
    if not isinstance(details, dict):
        return True
    archived_at_ms = _parse_time_ms(details.get("archivedAt"))
    session_mtime_at_archive = float(details.get("sessionMtimeMs") or 0)
    baseline_ms = session_mtime_at_archive or archived_at_ms
    return baseline_ms <= 0 or session_mtime_ms > baseline_ms + 1000


def _iso_from_ms(ms: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
