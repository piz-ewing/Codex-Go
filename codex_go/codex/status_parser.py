from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re

from codex_go.config import Settings

from .models import current_model_from_items, current_reasoning_mode_from_items
from .session_store import SessionStore, thread_id_from_session_file
from .text import (
    extract_plain_text_deep,
    extract_failure_text,
    extract_message_text,
    extract_reasoning_text,
    format_tool_call,
    is_terminal_failure_payload,
    normalize_history_text,
    parse_tool_arguments,
    truncate_text,
)


PERMISSION_PROMPT_RE = (
    r"权限|授权|批准|允许|确认|是否|是否运行|运行此命令|执行此命令|是否执行|"
    r"是否打开|是否启动|是否使用|是否应用|应用这些更改|应用更改|应用补丁|应用修改|"
    r"运行浏览器|打开浏览器|启动浏览器|使用浏览器|"
    r"使用.*工具|打开.*应用|访问.*网站|访问.*链接|读取.*文件|写入.*文件|"
    r"do you want|may i|allow|approve|permission|approval|run this command|"
    r"execute this command|open browser|launch browser|use browser|open app|"
    r"use tool|access website|access link|read file|write file|"
    r"apply (these )?(changes|edits|patch)|apply changes|apply patch"
)


def normalize_permission_action(value: str) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    if re.match(r"^(?:1|一)(?:[._。)、\s]|$)", text):
        return "allow"
    if re.match(r"^(?:2|二)(?:[._。)、\s]|$)", text):
        return "allow_always"
    if re.match(r"^(?:3|三)(?:[._。)、\s]|$)", text):
        return "deny"
    aliases = {
        "allow": "allow",
        "yes": "allow",
        "continue": "allow",
        "approve": "allow",
        "allow_always": "allow_always",
        "always_allow": "allow_always",
        "approve_always": "allow_always",
        "always": "allow_always",
        "remember": "allow_always",
        "yes_always": "allow_always",
        "run": "allow",
        "deny": "deny",
        "reject": "deny",
        "no": "deny",
        "cancel": "deny",
        "skip": "deny",
    }
    return aliases.get(text, "")


def is_permission_request_tool_call(payload: dict[str, Any]) -> bool:
    if payload.get("type") != "function_call":
        return False
    args = parse_tool_arguments(payload)
    if _has_permission_flag(args) or _has_permission_flag(payload):
        return True
    prompt = _permission_prompt_text(args) or _permission_prompt_text(payload)
    if _looks_like_permission_prompt(prompt):
        return True
    return False


def permission_request_from_tool_call(payload: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    args = parse_tool_arguments(payload)
    subject = _permission_subject(args, payload)
    prefix_rule = args.get("prefix_rule") if isinstance(args.get("prefix_rule"), list) else []
    justification = _permission_prompt_text(args) or _permission_prompt_text(payload) or "Codex 请求授权执行受限操作。"
    call_id = payload.get("call_id") or ""
    return {
        "callId": call_id,
        "toolName": payload.get("name") or "",
        "command": truncate_text(subject, 160),
        "subject": truncate_text(subject, 160),
        "prefixRule": [str(item) for item in prefix_rule if item],
        "justification": truncate_text(str(justification), 280),
        "text": truncate_text(f"{justification}（{subject}）" if subject else str(justification), 240),
        "pending": True,
        "time": item.get("timestamp") or "",
        "actions": [
            {"id": "allow", "label": "允许"},
            {"id": "allow_always", "label": "总是允许"},
            {"id": "deny", "label": "跳过"},
        ],
    }


def _permission_prompt_text(args: dict[str, Any]) -> str:
    for key in (
        "justification",
        "reason",
        "message",
        "prompt",
        "question",
        "description",
        "title",
        "approval",
        "approval_prompt",
        "permission_prompt",
        "user_facing_approval_question",
        "approval_question",
    ):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    joined = " ".join(
        str(part).strip()
        for part in extract_plain_text_deep(args)
        if isinstance(part, str) and str(part).strip()
    )
    if _looks_like_permission_prompt(joined):
        return joined
    return ""


def _looks_like_permission_prompt(value: str) -> bool:
    return bool(re.search(PERMISSION_PROMPT_RE, str(value or ""), re.I))


def _has_permission_flag(args: dict[str, Any]) -> bool:
    for key in (
        "sandbox_permissions",
        "sandboxPermissions",
        "permission",
        "approval",
        "approval_required",
        "requires_approval",
        "requiresApproval",
        "requires_permission",
        "requiresPermission",
        "status",
    ):
        if _is_permission_flag_value(args.get(key)):
            return True
    return False


def _is_permission_flag_value(value: Any) -> bool:
    if value is True:
        return True
    text = str(value or "").strip().lower()
    if not text:
        return False
    if text in {"false", "none", "never", "not_required", "no", "0"}:
        return False
    return bool(re.search(r"require|approval|approve|permission|escalat|confirm|prompt|ask", text))


def _permission_subject(args: dict[str, Any], payload: dict[str, Any]) -> str:
    for key in (
        "cmd",
        "command",
        "shell_command",
        "argv",
        "url",
        "uri",
        "href",
        "target",
        "resource",
        "path",
        "file",
        "directory",
        "app",
        "application",
        "browser",
        "tool",
        "operation",
        "action",
    ):
        value = args.get(key)
        text = _stringify_permission_subject(value)
        if text:
            return text
    return str(payload.get("name") or "").strip()


def _stringify_permission_subject(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        for key in ("cmd", "command", "url", "path", "name", "title", "value"):
            text = _stringify_permission_subject(value.get(key))
            if text:
                return text
        return ""
    return str(value).strip()


def step_from_event(item: dict[str, Any]) -> dict[str, Any] | None:
    payload = item.get("payload") or {}
    timestamp = item.get("timestamp") or ""
    if item.get("type") == "event_msg":
        if payload.get("type") == "task_started":
            return {"kind": "start", "label": "开始", "text": "Codex 开始处理请求。", "time": timestamp}
        if payload.get("type") == "task_complete":
            return {"kind": "complete", "label": "完成", "text": "Codex 已完成。", "time": timestamp}
        if payload.get("type") == "agent_message" and payload.get("phase") == "commentary":
            text = normalize_history_text(payload.get("message") or "")
            if text:
                return {"kind": "commentary", "label": "进度", "text": truncate_text(text, 1200), "time": timestamp}
        if is_terminal_failure_payload(payload):
            return {"kind": "error", "label": "失败", "text": truncate_text(extract_failure_text(payload) or "Codex 运行失败。"), "time": timestamp}
    if item.get("type") == "response_item":
        if is_permission_request_tool_call(payload):
            req = permission_request_from_tool_call(payload, item)
            return {"kind": "permission", "label": "等待权限", "text": req["text"], "time": timestamp, "callId": req["callId"], "pending": True}
        if payload.get("type") == "function_call":
            return {"kind": "tool", "label": "工具", "text": truncate_text(format_tool_call(payload), 500), "time": timestamp, "callId": payload.get("call_id") or ""}
        if payload.get("type") == "message":
            text = extract_message_text(payload.get("content"))
            if text and payload.get("role") == "assistant":
                if payload.get("phase") == "commentary":
                    return {"kind": "commentary", "label": "进度", "text": truncate_text(text, 1200), "time": timestamp}
                return {
                    "kind": "final" if payload.get("phase") == "final_answer" else "assistant",
                    "label": "回复",
                    "text": truncate_text(text, 1200),
                    "time": timestamp,
                }
        if payload.get("type") in {"reasoning", "reasoning_summary"}:
            text = extract_reasoning_text(payload) or extract_message_text(payload)
            if text:
                return {"kind": "thinking", "label": "思考", "text": truncate_text(text, 1200), "time": timestamp}
    return None


def quick_runtime_from_items(items: list[dict[str, Any]], mtime: float = 0) -> dict[str, Any]:
    status = "idle"
    active = False
    started_at = ""
    completed_at = ""
    updated_at = _iso_from_timestamp(mtime) if mtime else ""
    list_sort_updated_at = ""
    turn_id = ""
    pending_permission_call_ids: set[str] = set()
    for item in items:
        payload = item.get("payload") or {}
        if item.get("timestamp"):
            updated_at = item["timestamp"]
        if item.get("type") == "turn_context" and payload.get("turn_id"):
            turn_id = payload["turn_id"]
        if item.get("type") == "event_msg":
            event_type = payload.get("type")
            if event_type == "user_message" or event_type == "task_complete" or is_terminal_failure_payload(payload):
                list_sort_updated_at = item.get("timestamp") or list_sort_updated_at
        if item.get("type") == "event_msg" and payload.get("type") == "task_started":
            status = "running"
            active = True
            started_at = item.get("timestamp") or started_at
            completed_at = ""
            turn_id = payload.get("turn_id") or turn_id
        if item.get("type") == "response_item" and is_permission_request_tool_call(payload):
            if payload.get("call_id"):
                pending_permission_call_ids.add(payload["call_id"])
            status = "permission_required"
            active = True
        if item.get("type") == "response_item" and payload.get("type") == "function_call_output" and payload.get("call_id") in pending_permission_call_ids:
            pending_permission_call_ids.discard(payload["call_id"])
            status = "permission_required" if pending_permission_call_ids else "running"
            active = True
        if item.get("type") == "event_msg" and payload.get("type") == "task_complete":
            status = "complete"
            active = False
            completed_at = item.get("timestamp") or completed_at
        if item.get("type") == "event_msg" and is_terminal_failure_payload(payload):
            status = "error"
            active = False
            completed_at = item.get("timestamp") or completed_at
    return {
        "status": status,
        "active": active,
        "startedAt": started_at,
        "completedAt": completed_at,
        "updatedAt": updated_at,
        "listSortUpdatedAt": list_sort_updated_at,
        "turnId": turn_id,
    }


def parse_status(settings: Settings, **options: Any) -> dict[str, Any]:
    store = SessionStore(settings)
    since_ms = _parse_time_ms(options.get("since") or "")
    wants_exact = bool(options.get("thread_id") or options.get("session_file"))
    file: Path | None
    if options.get("thread_id"):
        file = store.find_by_thread_id(str(options["thread_id"]))
    elif options.get("session_file"):
        file = store.find_by_name(str(options["session_file"]))
    else:
        file = store.find_latest(
            after_ms=since_ms if options.get("expect_new_thread") else 0,
            exclude_thread_id=str(options.get("exclude_thread_id") or ""),
            cwd=str(options.get("cwd") or ""),
        )
    if not file:
        return {
            "ok": True,
            "available": False,
            "active": bool(options.get("expect_new_thread") and since_ms),
            "status": "missing" if wants_exact else "waiting" if options.get("expect_new_thread") and since_ms else "idle",
            "threadId": options.get("thread_id") or "",
            "sessionFile": options.get("session_file") or "",
            "message": "没有找到所选线程的 Codex 会话文件。" if wants_exact else "还没有找到 Codex 会话文件。",
            "steps": [],
            "preview": "已发送，等待 Codex 创建新线程记录…" if options.get("expect_new_thread") and since_ms else "还没有找到这个线程的回复记录。",
            "final": "",
            "durationMs": 0,
        }
    items = store.read_jsonl_tail_objects(file, settings.limits.session_tail_bytes)
    start_index = _find_start_index(items, since_ms)
    turn_items = items[start_index:]
    if since_ms:
        turn_items = [item for item in turn_items if not _parse_time_ms(item.get("timestamp") or "") or _parse_time_ms(item.get("timestamp") or "") >= since_ms]

    active = bool(since_ms)
    completed = False
    final = ""
    preview = ""
    started_at = ""
    completed_at = ""
    turn_id = ""
    failure_text = ""
    steps: list[dict[str, Any]] = []
    commentary_texts_seen: set[str] = set()
    thinking_texts_seen: set[str] = set()
    permission_requests: dict[str, dict[str, Any]] = {}
    tool_calls: dict[str, dict[str, Any]] = {}

    for item in turn_items:
        payload = item.get("payload") or {}
        failure_text = failure_text or extract_failure_text(payload)
        if item.get("type") == "event_msg" and payload.get("type") == "task_started":
            active = True
            started_at = started_at or item.get("timestamp") or ""
            turn_id = payload.get("turn_id") or turn_id
        if item.get("type") == "turn_context":
            turn_id = payload.get("turn_id") or turn_id
        if item.get("type") == "event_msg" and payload.get("type") == "task_complete":
            active = False
            completed = True
            completed_at = item.get("timestamp") or completed_at
            final = normalize_history_text(payload.get("last_agent_message") or "") or final
        if item.get("type") == "event_msg" and is_terminal_failure_payload(payload):
            active = False
            completed = True
            completed_at = item.get("timestamp") or completed_at
        if item.get("type") == "response_item" and payload.get("type") == "function_call_output":
            call_id = payload.get("call_id")
            if call_id and call_id in permission_requests:
                permission_requests[call_id]["pending"] = False
                for step in steps:
                    if step.get("callId") == call_id and step.get("kind") == "permission":
                        step["pending"] = False
                        step["label"] = "已授权"
            if call_id and call_id in tool_calls:
                for step in steps:
                    if step.get("callId") == call_id and step.get("kind") == "tool":
                        step["text"] = format_tool_call(tool_calls[call_id], complete=True)
        step = step_from_event(item)
        if not step:
            continue
        if step.get("kind") in {"assistant", "final", "thinking", "commentary"} and step.get("text"):
            preview = step["text"]
        if step.get("kind") == "final" and step.get("text"):
            final = step["text"]
        if step.get("kind") == "permission" and step.get("callId"):
            req = permission_request_from_tool_call(payload, item)
            permission_requests[step["callId"]] = req
        if step.get("kind") == "tool" and step.get("callId"):
            tool_calls[step["callId"]] = payload
        if step.get("kind") in {"start", "commentary", "thinking", "tool", "permission", "complete", "error"}:
            if step.get("kind") == "commentary":
                commentary_text = normalize_history_text(step.get("text") or "")
                if commentary_text in commentary_texts_seen:
                    continue
                commentary_texts_seen.add(commentary_text)
            if step.get("kind") == "thinking":
                thinking_text = normalize_history_text(step.get("text") or "")
                if thinking_text in thinking_texts_seen:
                    continue
                thinking_texts_seen.add(thinking_text)
            steps.append(step)

    pending_permission = next((req for req in permission_requests.values() if req.get("pending")), None)
    failed = completed and not final and bool(failure_text)
    final_failure_text = normalize_history_text(failure_text) if failed else ""
    status = "error" if failed else "complete" if completed else "permission_required" if pending_permission else "running" if active else "idle"
    waiting = bool(since_ms and not steps)
    status_steps = steps[-30:]
    start_ms = _parse_time_ms(started_at) or since_ms or 0
    end_ms = _parse_time_ms(completed_at) or (_now_ms() if start_ms else 0)
    duration_ms = max(0, end_ms - start_ms) if start_ms else 0
    updated_at = status_steps[-1].get("time") if status_steps else _iso_from_timestamp(file.stat().st_mtime)
    model = current_model_from_items(settings, items)
    reasoning_mode = current_reasoning_mode_from_items(items)
    return {
        "ok": True,
        "available": True,
        "active": True if waiting else active or bool(pending_permission),
        "status": "waiting" if waiting else status,
        "turnId": turn_id,
        "sessionFile": file.name,
        "threadId": thread_id_from_session_file(file),
        "updatedAt": updated_at,
        "startedAt": started_at,
        "completedAt": completed_at,
        "durationMs": duration_ms,
        "context": _context_usage_from_items(items),
        "model": model,
        "reasoningMode": reasoning_mode,
        "processText": "\n".join(f"{step.get('label') or '事件'}：{step.get('text') or ''}" for step in status_steps),
        "preview": final or preview or final_failure_text or (f"Codex 正在等待你授权：{pending_permission.get('justification')}" if pending_permission else "Codex 正在回复…" if active else "暂无可显示回复。"),
        "final": final or "",
        "error": final_failure_text,
        "permissionRequest": pending_permission,
        "steps": status_steps,
    }


def _find_start_index(items: list[dict[str, Any]], since_ms: float) -> int:
    if since_ms:
        for index, item in enumerate(items):
            t = _parse_time_ms(item.get("timestamp") or "")
            if t and t >= since_ms and item.get("type") == "event_msg" and (item.get("payload") or {}).get("type") == "task_started":
                return index
    for index in range(len(items) - 1, -1, -1):
        if items[index].get("type") == "event_msg" and (items[index].get("payload") or {}).get("type") == "task_started":
            return index
    return max(0, len(items) - 80)


def _parse_time_ms(value: Any) -> float:
    if not value:
        return 0
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000
    except Exception:
        return 0


def _now_ms() -> float:
    return datetime.now(tz=timezone.utc).timestamp() * 1000


def _iso_from_timestamp(timestamp: float) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _context_usage_from_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    window_tokens = 0
    latest_usage: dict[str, Any] | None = None
    updated_at = ""
    for item in items:
        payload = item.get("payload") or {}
        if item.get("type") == "event_msg" and payload.get("type") == "task_started":
            try:
                value = int(payload.get("model_context_window") or 0)
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                window_tokens = value
        if item.get("type") != "event_msg" or payload.get("type") != "token_count":
            continue
        info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
        try:
            value = int(info.get("model_context_window") or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            window_tokens = value
        usage = info.get("last_token_usage") or info.get("current_token_usage")
        if isinstance(usage, dict):
            latest_usage = usage
            updated_at = item.get("timestamp") or updated_at
    if not latest_usage or not window_tokens:
        return {
            "available": False,
            "usedTokens": 0,
            "windowTokens": window_tokens or 0,
            "remainingTokens": window_tokens or 0,
            "percent": None,
            "updatedAt": updated_at,
        }
    input_tokens = int(latest_usage.get("input_tokens") or 0)
    output_tokens = int(latest_usage.get("output_tokens") or 0)
    total_tokens = int(latest_usage.get("total_tokens") or 0)
    used_tokens = total_tokens or input_tokens + output_tokens or input_tokens
    if used_tokens > window_tokens * 1.15 and 0 < input_tokens <= window_tokens * 1.15:
        used_tokens = input_tokens + output_tokens
    used_tokens = max(0, round(used_tokens))
    percent = max(0, min(100, (used_tokens / window_tokens) * 100))
    return {
        "available": True,
        "usedTokens": used_tokens,
        "windowTokens": window_tokens,
        "remainingTokens": max(0, round(window_tokens - used_tokens)),
        "percent": percent,
        "updatedAt": updated_at,
    }
