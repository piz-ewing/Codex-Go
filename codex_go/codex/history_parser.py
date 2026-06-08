from __future__ import annotations

from pathlib import Path
from typing import Any

from codex_go.config import Settings

from .session_store import SessionStore, is_codex_thread_id
from .text import clean_user_history_text, extract_failure_text, extract_message_text, is_terminal_failure_payload, normalize_history_text


def extract_user_attachments(payload: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("local_images", "images"):
        values = payload.get(key)
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, str):
                paths.append(item)
            elif isinstance(item, dict):
                if isinstance(item.get("path"), str):
                    paths.append(item["path"])
                elif isinstance(item.get("filePath"), str):
                    paths.append(item["filePath"])
    return paths


def _attachment_kind(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".heif", ".avif", ".bmp"}:
        return "image"
    if ext in {".mp4", ".mov", ".m4v", ".webm"}:
        return "video"
    if ext in {".mp3", ".wav", ".m4a"}:
        return "audio"
    if ext == ".pdf":
        return "pdf"
    if ext in {".zip", ".rar", ".7z", ".tar", ".gz"}:
        return "archive"
    if ext in {".txt", ".md", ".json", ".csv", ".log", ".py", ".js", ".ts", ".tsx", ".jsx", ".css", ".html", ".xml", ".yaml", ".yml", ".toml", ".sh", ".rs", ".go"}:
        return "text"
    return "file"


def _attachment_summary(paths: list[str]) -> str:
    counts: dict[str, int] = {}
    for path in paths:
        label = _attachment_kind_label(_attachment_kind(path))
        counts[label] = counts.get(label, 0) + 1
    return "、".join(f"{count} {'张' if label == '图片' else '个'}{label}" for label, count in counts.items())


def _attachment_kind_label(kind: str) -> str:
    return {
        "image": "图片",
        "video": "视频",
        "audio": "音频",
        "pdf": "PDF",
        "archive": "压缩包",
        "text": "文本",
        "file": "文件",
    }.get(kind, "文件")


def parse_history(settings: Settings, thread_id: str, limit: int | str = 120) -> dict[str, Any]:
    if not is_codex_thread_id(thread_id):
        return {"ok": False, "code": "BAD_THREAD_ID", "message": "线程 ID 不正确。"}
    store = SessionStore(settings)
    file = store.find_by_thread_id(thread_id)
    if not file:
        return {
            "ok": True,
            "available": False,
            "threadId": thread_id,
            "sessionFile": "",
            "messages": [],
            "message": "没有找到所选线程的 Codex 会话文件。",
        }
    max_messages = max(1, min(int(limit or settings.limits.max_history_messages), settings.limits.max_history_messages))
    lines = store.read_tail_lines(file, min(file.stat().st_size, settings.limits.history_tail_bytes))
    messages: list[dict[str, Any]] = []
    current_turn: dict[str, Any] | None = None
    for line in lines:
        try:
            import json

            item = json.loads(line)
        except Exception:
            continue
        payload = item.get("payload") or {}
        if item.get("type") == "event_msg" and payload.get("type") == "task_started":
            current_turn = {"hasAssistant": False, "assistantIndex": -1, "startedAt": item.get("timestamp") or "", "failureText": "", "turnId": payload.get("turn_id") or ""}
            continue
        if current_turn and item.get("type") == "event_msg":
            current_turn["failureText"] = current_turn.get("failureText") or extract_failure_text(payload)
        if current_turn and item.get("type") == "turn_context":
            current_turn["turnId"] = payload.get("turn_id") or current_turn.get("turnId") or ""
        if item.get("type") == "event_msg" and payload.get("type") == "user_message":
            text = clean_user_history_text(payload.get("message"))
            attachments = extract_user_attachments(payload)
            if text or attachments:
                messages.append(
                    {
                        "role": "user",
                        "label": f"你 · {_attachment_summary(attachments)}" if attachments else "你",
                        "text": text or (" " if attachments else ""),
                        "attachments": [{"filePath": path, "name": Path(path).name, "kind": _attachment_kind(path)} for path in attachments],
                        "timestamp": item.get("timestamp") or "",
                    }
                )
            continue
        if item.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "assistant":
            if payload.get("phase") != "final_answer":
                continue
            text = normalize_history_text(extract_message_text(payload.get("content")))
            if text:
                index = len(messages)
                messages.append({"role": "assistant", "label": "Codex", "text": text, "timestamp": item.get("timestamp") or ""})
                if current_turn is not None:
                    current_turn["hasAssistant"] = True
                    current_turn["assistantIndex"] = index
            continue
        if item.get("type") == "event_msg" and payload.get("type") == "task_complete":
            last_message = normalize_history_text(payload.get("last_agent_message") or "")
            completed_at = item.get("timestamp") or ""
            if current_turn and not current_turn.get("hasAssistant"):
                messages.append(
                    {
                        "role": "assistant",
                        "label": _complete_label(current_turn.get("startedAt") or "", completed_at),
                        "text": last_message or current_turn.get("failureText") or "Codex 已结束本轮回复，但没有写入最终消息。",
                        "timestamp": completed_at or current_turn.get("startedAt") or "",
                    }
                )
            elif current_turn and current_turn.get("hasAssistant") and current_turn.get("assistantIndex", -1) >= 0:
                messages[current_turn["assistantIndex"]]["label"] = _complete_label(current_turn.get("startedAt") or "", completed_at)
            current_turn = None
            continue
        if item.get("type") == "event_msg" and is_terminal_failure_payload(payload):
            failure_text = normalize_history_text(extract_failure_text(payload) or (current_turn or {}).get("failureText") or "")
            completed_at = item.get("timestamp") or ""
            if current_turn and not current_turn.get("hasAssistant"):
                messages.append(
                    {
                        "role": "assistant",
                        "label": _failure_label(current_turn.get("startedAt") or "", completed_at),
                        "text": failure_text or "Codex GUI 这次没有返回可显示回复，请在电脑端查看原始失败提示。",
                        "timestamp": completed_at or current_turn.get("startedAt") or "",
                    }
                )
            elif current_turn and current_turn.get("hasAssistant") and current_turn.get("assistantIndex", -1) >= 0:
                messages[current_turn["assistantIndex"]]["label"] = _failure_label(current_turn.get("startedAt") or "", completed_at)
            current_turn = None

    return {
        "ok": True,
        "available": True,
        "threadId": thread_id,
        "sessionFile": file.name,
        "truncated": file.stat().st_size > settings.limits.history_tail_bytes,
        "messages": messages[-max_messages:],
    }


def _duration_text(started_at: str = "", completed_at: str = "") -> str:
    from datetime import datetime

    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00")).timestamp()
        end = datetime.fromisoformat(completed_at.replace("Z", "+00:00")).timestamp()
    except Exception:
        return ""
    if end < start:
        return ""
    total = max(0, int(end - start))
    minutes = total // 60
    seconds = total % 60
    return f"{minutes}m {seconds}s" if minutes else f"{seconds}s"


def _complete_label(started_at: str = "", completed_at: str = "") -> str:
    duration = _duration_text(started_at, completed_at)
    return f"Codex · 已处理 {duration}" if duration else "Codex"


def _failure_label(started_at: str = "", completed_at: str = "") -> str:
    duration = _duration_text(started_at, completed_at)
    return f"Codex · 失败 {duration}" if duration else "Codex"
