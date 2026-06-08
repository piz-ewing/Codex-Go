from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import os
import re
import time

from codex_go.codex import is_codex_thread_id, normalize_permission_action, parse_status
from codex_go.codex.models import (
    codex_menu_display_name,
    current_model_from_items,
    current_reasoning_mode_from_items,
    merge_model_option_lists,
    model_options_from_display_names,
    model_target_for_key,
    reasoning_target_for_key,
    read_model_catalog_options,
)
from codex_go.codex.session_store import SessionStore, thread_id_from_session_file
from codex_go.codex.threads import classify_thread_project, list_threads
from codex_go.config import Settings

from .attachments import AttachmentError, PreparedAttachment, prepare_attachments


RECENT_SEND_TTL_SECONDS = 5 * 60


def iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class CodexBridgeService:
    settings: Settings
    cdp: Any
    state: Any
    recent_sends: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def send(self, payload: Any) -> dict[str, Any]:
        if payload.target != "codex":
            raise BridgeError("UNSUPPORTED_TARGET", "Codex Go 只支持通过 CDP DOM 控制 Codex。", 400)
        raw_attachments = getattr(payload, "attachments", []) or []
        text = payload.text or ""
        if not text.strip() and not raw_attachments:
            raise BridgeError("EMPTY_MESSAGE", "请输入文字或添加附件。", 400)
        if len(text) > self.settings.limits.max_text_length:
            raise BridgeError("TEXT_TOO_LONG", f"文字太长了，请控制在 {self.settings.limits.max_text_length} 字以内。", 413)
        if payload.threadId and not is_codex_thread_id(payload.threadId):
            raise BridgeError("BAD_THREAD_ID", "线程 ID 不正确。", 400)
        previous_thread_id = payload.previousThreadId if is_codex_thread_id(payload.previousThreadId) else ""

        client_request_id = _normalize_client_request_id(payload.clientRequestId)
        self._cleanup_recent_sends()
        if client_request_id:
            existing = self.recent_sends.get(client_request_id)
            if existing and existing.get("result"):
                return {**existing["result"], "duplicate": True}
            if existing and existing.get("watch"):
                return {
                    "ok": True,
                    "duplicate": True,
                    "message": "这条发送请求已经被接收，正在继续等待 Codex 回复。",
                    "target": "codex",
                    "sentAt": existing.get("sentAt") or "",
                    "watch": existing["watch"],
                }

        try:
            attachments = prepare_attachments(raw_attachments, self.settings)
        except AttachmentError as exc:
            raise BridgeError(exc.code, exc.message, exc.status) from exc

        watch_since = iso_now()
        watch_since_ms = _parse_time_ms(watch_since)
        expect_new_thread = bool(payload.expectNewThread and not payload.threadId)
        expected_cwd = _valid_local_directory(payload.expectedCwd) if expect_new_thread else ""
        watch_file = None if expect_new_thread else self._watch_file(payload.threadId)
        watch = {
            "since": watch_since,
            "threadId": payload.threadId,
            "sessionFile": watch_file.name if watch_file else "",
            "expectNewThread": expect_new_thread,
            "excludeThreadId": previous_thread_id if expect_new_thread else "",
            "cwd": expected_cwd if expect_new_thread else "",
        }
        if client_request_id:
            self.recent_sends[client_request_id] = {"createdAt": time.time(), "sentAt": iso_now(), "watch": watch}

        if expect_new_thread:
            await self._create_new_thread_for_target(_new_thread_payload_from_send(payload))

        cdp_result = await self.cdp.send_text(text, "" if expect_new_thread else payload.threadId, attachments=[attachment.path for attachment in attachments])

        if expect_new_thread:
            new_file = self._wait_for_new_send_file(watch_since_ms, text, expected_cwd, previous_thread_id)
            if new_file:
                watch = {
                    **watch,
                    "threadId": thread_id_from_session_file(new_file),
                    "sessionFile": new_file.name,
                    "expectNewThread": False,
                    "excludeThreadId": "",
                }

        result = {
            "ok": True,
            "message": "已创建新线程并通过 CDP DOM 发送到 Codex。" if expect_new_thread else "已通过 CDP DOM 发送到 Codex。",
            "target": "codex",
            "sentAt": iso_now(),
            "attachments": _attachment_payloads(attachments),
            "cdp": cdp_result,
            "watch": watch,
        }
        if client_request_id:
            self.recent_sends[client_request_id] = {"createdAt": time.time(), "sentAt": result["sentAt"], "watch": watch, "result": result}
        return result

    async def _create_new_thread_for_target(self, target_payload: Any) -> dict[str, str]:
        target = self._resolve_new_thread_target(target_payload)
        project = classify_thread_project(target["cwd"])
        await self.cdp.create_new_thread(project["projectName"] if project["isProjectThread"] else "", target["anchorThreadId"])
        return target

    async def create_new_thread(self, payload: Any) -> dict[str, Any]:
        target = self._resolve_new_thread_target(_new_thread_payload_from_request(payload))
        project = classify_thread_project(target["cwd"])
        return {
            "ok": True,
            "pending": True,
            "cwd": target["cwd"] if project["isProjectThread"] else "",
            "projectName": project["projectName"],
            "projectPath": project["projectPath"],
            "projectKey": project["projectKey"],
            "scope": "project" if project["isProjectThread"] else "conversation",
            "message": f"已准备好在“{project['projectName']}”新建线程，发送第一条消息后才会创建。" if project["isProjectThread"] else "已准备好新建对话线程，发送第一条消息后才会创建。",
        }

    async def thread_action(self, payload: Any) -> dict[str, Any]:
        if not is_codex_thread_id(payload.threadId):
            raise BridgeError("BAD_THREAD_ID", "线程 ID 不正确。", 400)
        action = payload.action
        if action not in {"archive", "pin", "unpin", "rename"}:
            raise BridgeError("BAD_THREAD_ACTION", "不支持的线程操作。", 400)
        if action == "rename" and not payload.name.strip():
            raise BridgeError("EMPTY_THREAD_NAME", "新名称不能为空。", 400)
        if action == "rename" and len(payload.name.strip()) > 120:
            raise BridgeError("THREAD_NAME_TOO_LONG", "新名称太长，请控制在 120 个字符以内。", 400)

        if action == "archive":
            archived_at = iso_now()
            archive_file = SessionStore(self.settings).find_by_thread_id(payload.threadId)
            archive_session_mtime_ms = 0.0
            if archive_file:
                try:
                    archive_session_mtime_ms = archive_file.stat().st_mtime * 1000
                except OSError:
                    archive_session_mtime_ms = 0.0
            result = await self.cdp.run_thread_action(payload.threadId, "archive")
            message = "已归档当前 Codex 线程。"
        elif action in {"pin", "unpin"}:
            pinned = action == "pin"
            result = await self.cdp.run_thread_action(payload.threadId, "pin", pinned=pinned)
            message = "已置顶当前 Codex 线程。" if pinned else "已取消置顶当前 Codex 线程。"
        else:
            result = await self.cdp.run_thread_action(payload.threadId, "rename", name=payload.name.strip())
            message = "已重命名当前 Codex 线程。"

        def update(state: dict[str, Any]) -> dict[str, Any]:
            pinned = set(state.get("pinnedThreadIds") or [])
            archived = set(state.get("archivedThreadIds") or [])
            archive_details = state.get("archivedThreadDetails") if isinstance(state.get("archivedThreadDetails"), dict) else {}
            titles = state.get("titleOverrides") if isinstance(state.get("titleOverrides"), dict) else {}
            if action == "archive":
                archived.add(payload.threadId)
                pinned.discard(payload.threadId)
                archive_details[payload.threadId] = {
                    "archivedAt": archived_at,
                    "sessionFile": archive_file.name if archive_file else "",
                    "sessionMtimeMs": archive_session_mtime_ms,
                }
            elif action == "pin":
                pinned.add(payload.threadId)
            elif action == "unpin":
                pinned.discard(payload.threadId)
            elif action == "rename":
                titles[payload.threadId] = {"name": payload.name.strip(), "renamedAt": iso_now()}
            state["pinnedThreadIds"] = sorted(pinned)
            state["archivedThreadIds"] = sorted(archived)
            state["archivedThreadDetails"] = archive_details
            state["titleOverrides"] = titles
            return state

        self.state.update(update)
        threads = list_threads(self.settings, 120) if action == "archive" else []
        next_thread_id = threads[0]["id"] if threads else payload.threadId
        return {"ok": True, "action": action, "threadId": payload.threadId, "nextThreadId": next_thread_id, "result": result, "message": message, "name": payload.name.strip() if action == "rename" else ""}

    async def pending_sends(self, thread_id: str) -> dict[str, Any]:
        if not is_codex_thread_id(thread_id):
            raise BridgeError("BAD_THREAD_ID", "线程 ID 不正确。", 400)
        result = await self.cdp.list_pending_sends(thread_id)
        return {"ok": True, "threadId": thread_id, "items": result.get("items") if isinstance(result.get("items"), list) else [], "result": result}

    async def pending_send_action(self, payload: Any) -> dict[str, Any]:
        if not is_codex_thread_id(payload.threadId):
            raise BridgeError("BAD_THREAD_ID", "线程 ID 不正确。", 400)
        result = await self.cdp.run_pending_send_action(payload.threadId, payload.action, payload.text)
        return {
            "ok": True,
            "action": result.get("action") or payload.action,
            "threadId": payload.threadId,
            "result": result,
            "message": "已删除 Codex 排队消息。" if result.get("action") == "delete" else "已引导 Codex 先处理这条排队消息。",
        }

    async def permission_action(self, payload: Any) -> dict[str, Any]:
        if not is_codex_thread_id(payload.threadId):
            raise BridgeError("BAD_THREAD_ID", "线程 ID 不正确。", 400)
        action = normalize_permission_action(payload.action)
        if not action:
            raise BridgeError("BAD_PERMISSION_ACTION", "请选择是、总是或跳过。", 400)
        status = parse_status(self.settings, thread_id=payload.threadId)
        request = status.get("permissionRequest")
        if not isinstance(request, dict) or not request.get("pending"):
            gui_status = await self.cdp.read_gui_status(payload.threadId)
            gui_request = gui_status.get("permissionRequest") if isinstance(gui_status, dict) else None
            if isinstance(gui_request, dict) and gui_request.get("pending"):
                request = gui_request
        if not status.get("available") or not isinstance(request, dict) or not request.get("pending"):
            raise BridgeError("NO_PENDING_PERMISSION", "当前线程没有待处理的权限请求。", 409, {"status": status.get("status") or ""})
        if payload.callId and request.get("callId") and payload.callId != request.get("callId"):
            raise BridgeError("PERMISSION_REQUEST_CHANGED", "权限请求已经变化，请刷新后重试。", 409, {"permissionRequest": request})
        result = await self.cdp.resolve_permission(payload.threadId, action, request)
        message = "已在 Codex 桌面端跳过权限请求。" if action == "deny" else "已在 Codex 桌面端总是允许权限请求。" if action == "allow_always" else "已在 Codex 桌面端允许权限请求。"
        return {"ok": True, "action": action, "threadId": payload.threadId, "callId": request.get("callId") or "", "result": result, "message": message}

    async def switch_model(self, payload: Any) -> dict[str, Any]:
        if payload.threadId and not is_codex_thread_id(payload.threadId):
            raise BridgeError("BAD_THREAD_ID", "线程 ID 不正确。", 400)
        file = self._watch_file(payload.threadId)
        current = current_model_from_items(self.settings, SessionStore(self.settings).read_jsonl_tail_objects(file, self.settings.limits.session_tail_bytes)) if file else {}
        try:
            target = model_target_for_key(self.settings, payload.target, current)
        except ValueError as exc:
            raise BridgeError("UNKNOWN_MODEL_TARGET", str(exc), 400) from exc
        menu_display_name = codex_menu_display_name(str(target.get("displayName") or ""), str(target.get("id") or ""))
        await self.cdp.switch_model(payload.threadId, menu_display_name)
        return {
            "ok": True,
            "threadId": payload.threadId,
            "currentModel": current,
            "targetModel": {**target, "displayName": menu_display_name, "available": True, "updatedAt": iso_now()},
            "message": f"已切换到 {menu_display_name}",
        }

    async def switch_reasoning(self, payload: Any) -> dict[str, Any]:
        if payload.threadId and not is_codex_thread_id(payload.threadId):
            raise BridgeError("BAD_THREAD_ID", "线程 ID 不正确。", 400)
        file = self._watch_file(payload.threadId)
        current = current_reasoning_mode_from_items(SessionStore(self.settings).read_jsonl_tail_objects(file, self.settings.limits.session_tail_bytes)) if file else {}
        target = reasoning_target_for_key(payload.target, current)
        await self.cdp.switch_reasoning(payload.threadId, target["displayName"])
        return {
            "ok": True,
            "threadId": payload.threadId,
            "currentReasoningMode": current,
            "targetReasoningMode": {**target, "available": True, "updatedAt": iso_now()},
            "message": f"已切换推理模式为 {target['displayName']}",
        }

    def model_options(self) -> list[dict[str, Any]]:
        return read_model_catalog_options(self.settings)

    async def resolve_model_options(self) -> list[dict[str, Any]]:
        catalog = self.model_options()
        try:
            result = await self.cdp.list_model_options()
        except Exception:
            return catalog
        if not isinstance(result, dict) or not result.get("ok"):
            return catalog
        live = model_options_from_display_names(self.settings, result.get("displayNames") or [])
        if not live:
            return catalog
        return merge_model_option_lists(live, catalog)

    def _cleanup_recent_sends(self) -> None:
        cutoff = time.time() - RECENT_SEND_TTL_SECONDS
        for key in list(self.recent_sends):
            if self.recent_sends[key].get("createdAt", 0) < cutoff:
                del self.recent_sends[key]

    def _watch_file(self, thread_id: str = "") -> Path | None:
        store = SessionStore(self.settings)
        return store.find_by_thread_id(thread_id) if thread_id else store.find_latest()

    def _wait_for_new_send_file(self, since_ms: float, text: str, cwd: str, exclude_thread_id: str) -> Path | None:
        deadline = time.time() + 2.6
        while time.time() <= deadline:
            file = self._find_new_send_file(since_ms, text, cwd, exclude_thread_id)
            if file:
                return file
            time.sleep(0.22)
        return self._find_new_send_file(since_ms, text, cwd, exclude_thread_id)

    def _find_new_send_file(self, since_ms: float, text: str, cwd: str, exclude_thread_id: str) -> Path | None:
        store = SessionStore(self.settings)
        expected = _normalize_comparable_message(text)
        expected_cwd = _valid_local_directory(cwd)
        best: tuple[Path, float, float] | None = None
        for file in store.list_session_files(force=True):
            thread_id = thread_id_from_session_file(file)
            if exclude_thread_id and thread_id == exclude_thread_id:
                continue
            try:
                stat = file.stat()
            except OSError:
                continue
            if stat.st_mtime * 1000 < since_ms - 2500:
                continue
            score = _user_message_match_score(store, file, since_ms, expected)
            if score <= 0 and expected:
                continue
            if expected_cwd:
                meta_cwd = _valid_local_directory(str(store.read_session_meta(file).get("cwd") or ""))
                if meta_cwd != expected_cwd:
                    continue
                score += 35
            score += max(0, min(20, round((stat.st_mtime * 1000 - since_ms) / 1000) + 10))
            if best is None or score > best[1] or (score == best[1] and stat.st_mtime > best[2]):
                best = (file, score, stat.st_mtime)
        return best[0] if best else None

    def _resolve_new_thread_target(self, payload: Any) -> dict[str, str]:
        scope = _normalize_new_thread_scope(payload)
        project_path = _project_cwd_or_empty(getattr(payload, "projectPath", ""))
        thread_id = getattr(payload, "threadId", "")
        if thread_id and not is_codex_thread_id(thread_id):
            raise BridgeError("BAD_THREAD_ID", "线程 ID 不正确。", 400)
        if scope == "conversation":
            return {"scope": "conversation", "cwd": "", "anchorThreadId": thread_id}
        if scope == "project" and project_path:
            return {"scope": "project", "cwd": project_path, "anchorThreadId": thread_id}
        if thread_id:
            file = SessionStore(self.settings).find_by_thread_id(thread_id)
            meta_cwd = str(SessionStore(self.settings).read_session_meta(file).get("cwd") or "") if file else ""
            meta_project = classify_thread_project(_valid_local_directory(meta_cwd))
            if meta_project["isProjectThread"]:
                return {"scope": "project", "cwd": meta_project["projectPath"], "anchorThreadId": thread_id}
            return {"scope": "conversation", "cwd": "", "anchorThreadId": thread_id}
        if project_path:
            return {"scope": "project", "cwd": project_path, "anchorThreadId": ""}
        return {"scope": "conversation", "cwd": "", "anchorThreadId": ""}


class BridgeError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 400, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.extra = extra or {}

    def payload(self) -> dict[str, Any]:
        return {"ok": False, "code": self.code, "message": self.message, **self.extra}


def _normalize_client_request_id(value: str = "") -> str:
    text = str(value or "").strip()
    return text if re.match(r"^[a-zA-Z0-9._:-]{8,120}$", text) else ""


def _parse_time_ms(value: str) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000
    except Exception:
        return time.time() * 1000


def _valid_local_directory(value: str = "") -> str:
    normalized = os.path.normpath(str(value or "")) if value else ""
    if not normalized or not os.path.isabs(normalized):
        return ""
    return normalized if os.path.isdir(normalized) else ""


def _normalize_comparable_message(value: str = "") -> str:
    text = str(value or "")
    marker = "## My request for Codex:"
    index = text.find(marker)
    if index >= 0:
        text = text[index + len(marker) :]
    return re.sub(r"\s+", " ", text).strip()


def _user_message_match_score(store: SessionStore, file: Path, since_ms: float, expected: str) -> float:
    score = 0.0
    for item in store.read_jsonl_tail_objects(file, store.settings.limits.title_scan_bytes):
        payload = item.get("payload") or {}
        if item.get("type") != "event_msg" or payload.get("type") != "user_message":
            continue
        t = _parse_time_ms(item.get("timestamp") or "")
        if since_ms and t and t < since_ms - 2500:
            continue
        actual = _normalize_comparable_message(payload.get("message") or "")
        if not actual and expected:
            continue
        score = max(score, 10)
        if t:
            score += max(0, min(25, round((t - since_ms) / 1000) + 20))
        if expected and actual:
            if actual == expected:
                score += 100
            elif actual in expected or expected in actual:
                score += 70
    return score


def _attachment_payloads(attachments: list[PreparedAttachment]) -> list[dict[str, Any]]:
    return [attachment.response_payload() for attachment in attachments]


class _NewThreadTargetPayload:
    def __init__(
        self,
        *,
        thread_id: str = "",
        project_path: str = "",
        scope: str = "",
        is_project_thread: bool | None = None,
    ):
        self.threadId = thread_id
        self.projectPath = project_path
        self.scope = scope
        self.isProjectThread = is_project_thread


def _new_thread_payload_from_send(payload: Any) -> _NewThreadTargetPayload:
    return _NewThreadTargetPayload(
        thread_id=payload.previousThreadId if is_codex_thread_id(payload.previousThreadId) else "",
        project_path=_project_cwd_or_empty(getattr(payload, "projectPath", "") or getattr(payload, "expectedCwd", "")),
        scope=str(getattr(payload, "newThreadScope", "") or ""),
        is_project_thread=getattr(payload, "isProjectThread", None),
    )


def _new_thread_payload_from_request(payload: Any) -> _NewThreadTargetPayload:
    return _NewThreadTargetPayload(
        thread_id=getattr(payload, "threadId", ""),
        project_path=_project_cwd_or_empty(getattr(payload, "projectPath", "")),
        scope=str(getattr(payload, "scope", "") or ""),
        is_project_thread=getattr(payload, "isProjectThread", None),
    )


def _normalize_new_thread_scope(payload: Any) -> str:
    raw = str(getattr(payload, "scope", "") or "").strip().lower()
    if raw in {"conversation", "project"}:
        return raw
    if getattr(payload, "isProjectThread", None) is False:
        return "conversation"
    if getattr(payload, "isProjectThread", None) is True:
        return "project"
    return ""


def _project_cwd_or_empty(value: str = "") -> str:
    cwd = _valid_local_directory(value)
    if not cwd:
        return ""
    return cwd if classify_thread_project(cwd)["isProjectThread"] else ""
