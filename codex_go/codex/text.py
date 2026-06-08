from __future__ import annotations

import json
import os
import re
from typing import Any


def truncate_text(value: str, max_len: int = 1200) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def extract_plain_text_deep(value: Any, seen: set[int] | None = None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    seen = seen or set()
    obj_id = id(value)
    if obj_id in seen:
        return []
    seen.add(obj_id)
    out: list[str] = []
    if isinstance(value, list):
        for item in value:
            out.extend(extract_plain_text_deep(item, seen))
        return out
    if isinstance(value, dict):
        for key in ("message", "detail", "details", "error", "reason", "description", "status", "code", "title", "text", "content", "summary", "output", "value"):
            if key in value:
                out.extend(extract_plain_text_deep(value[key], seen))
        return out
    return []


def extract_message_text(content: Any) -> str:
    return "\n".join(part.strip() for part in extract_plain_text_deep(content) if part and str(part).strip())


def normalize_history_text(value: Any) -> str:
    return re.sub(r"\n{3,}", "\n\n", str(value or "").replace("\r\n", "\n")).strip()


def clean_user_history_text(value: Any) -> str:
    if isinstance(value, str):
        text = normalize_history_text(value)
        marker = "## My request for Codex:"
        index = text.find(marker)
        return normalize_history_text(text[index + len(marker) :]) if index >= 0 else text
    if isinstance(value, list):
        return normalize_history_text(extract_message_text(value))
    if isinstance(value, dict):
        return normalize_history_text(extract_message_text(value))
    return ""


def summarize_thread_title(value: Any) -> str:
    text = clean_user_history_text(value)
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\bsk-[a-zA-Z0-9_-]{12,}\b", "[key]", text)
    text = re.sub(r"\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b", "[token]", text)
    text = re.sub(r"https?://\S+", "[link]", text)
    text = re.sub(r"[#>*_[\]()~]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return truncate_text(text, 34)


def parse_tool_arguments(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("arguments") or payload.get("input") or ""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(str(raw))
        return parsed if isinstance(parsed, dict) else {"raw": raw}
    except Exception:
        return {"raw": str(raw)}


def extract_failure_text(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict) or not is_failure_like_payload(payload):
        return ""
    text = "\n".join(
        normalize_history_text(part)
        for part in extract_plain_text_deep(payload)
        if normalize_history_text(part) and not re.match(r"^(true|false|null|undefined)$", normalize_history_text(part), re.I)
    )
    return truncate_text(text, 1600)


def is_failure_like_payload(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    joined = " ".join(str(payload.get(key) or "").lower() for key in ("type", "status", "code"))
    return bool(
        re.search(r"error|fail|failed|failure|timeout|rate_limit|unavailable|overload|abort|cancel|interrupt", joined)
        or payload.get("error") is not None
        or payload.get("detail") is not None
        or payload.get("details") is not None
        or payload.get("reason") is not None
    )


def is_terminal_failure_payload(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    kind = str(payload.get("type") or "").lower()
    return bool(
        kind == "turn_aborted"
        or re.search(r"(?:^|_)(?:failed|failure|error|timeout|cancelled|canceled|aborted|interrupted)$", kind)
        or (is_failure_like_payload(payload) and re.search(r"abort|cancel|interrupt|fail|error|timeout|unavailable|overload", kind))
    )


def extract_reasoning_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("summary", "content"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        parts.append(item["text"])
                    elif isinstance(item.get("summary"), str):
                        parts.append(item["summary"])
    if isinstance(payload.get("text"), str):
        parts.append(payload["text"])
    return "\n".join(part.strip() for part in parts if part and part.strip())


def shell_quote_pattern() -> str:
    return r'(?:(?:"[^"]+")|(?:\'[^\']+\')|(?:\\\S|\S)+)'


def strip_shell_quotes(value: Any) -> str:
    text = str(value or "").strip()
    while (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1]
    return re.sub(r"\\([\s\"'])", r"\1", text)


def short_path(value: Any) -> str:
    text = strip_shell_quotes(value).replace("~/", "~/")
    if not text:
        return ""
    home = os.path.expanduser("~")
    normalized = f"~{text[len(home):]}" if text.startswith(home) else text
    return normalized.removeprefix("./")


def unique_list(values: list[Any], limit: int = 3) -> list[str]:
    out: list[str] = []
    for value in values:
        text = short_path(value)
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def truncate_command(cmd: Any, max_len: int = 120) -> str:
    one_line = re.sub(r"\s+", " ", str(cmd or "").split("\n")[0]).strip()
    home = os.path.expanduser("~")
    text = one_line.replace(home, "~")
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def format_tool_call(payload: dict[str, Any], complete: bool = False) -> str:
    raw_name = str(payload.get("name") or "tool")
    name = raw_name.split(".")[-1]
    args = parse_tool_arguments(payload)
    if name == "exec_command":
        cmd = str(args.get("cmd") or args.get("raw") or "").strip()
        if re.search(r"\b(?:rg|grep)\b", cmd):
            return "Search project files"
        if re.search(r"\bfind\b", cmd):
            return "Find files"
        if re.search(r"\bls\b", cmd):
            return "List files"
        if re.search(r"\bgit\s+diff\b", cmd):
            return "Review diff"
        if re.search(r"\bgit\s+status\b", cmd):
            return "Check git status"
        if re.search(r"\bgit\b", cmd):
            return f"Run git: {truncate_command(cmd, 90)}"
        if re.search(r"\b(?:python|python3|uv run|bash -n)\b", cmd):
            return f"Run check: {truncate_command(cmd, 90)}"
        if re.search(r"\bcurl\b", cmd):
            return f"Check endpoint: {truncate_command(cmd, 100)}"
        return f"Run: {truncate_command(cmd) or 'local command'}"
    if name == "apply_patch":
        return "已编辑文件" if complete else "正在编辑文件"
    if name == "write_stdin":
        return "Read command output"
    if "browser" in name or "chrome" in name:
        return "Check browser page"
    return raw_name
