from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re

from codex_go.config import Settings


REASONING_MODE_TARGETS: dict[str, dict[str, str]] = {
    "low": {"key": "low", "value": "low", "label": "低", "displayName": "低"},
    "medium": {"key": "medium", "value": "medium", "label": "中", "displayName": "中"},
    "high": {"key": "high", "value": "high", "label": "高", "displayName": "高"},
    "xhigh": {"key": "xhigh", "value": "xhigh", "label": "超高", "displayName": "超高"},
}

OFFICIAL_MODELS: dict[str, tuple[str, str]] = {
    "gpt-5.5": ("5.5", "GPT-5.5"),
    "gpt-5.4": ("5.4", "GPT-5.4"),
    "gpt-5.4-mini": ("mini", "GPT-5.4-Mini"),
    "gpt-5.3-codex": ("5.3", "GPT-5.3-Codex"),
    "gpt-5.2": ("5.2", "GPT-5.2"),
}


def default_model_catalog_options(current_model: str = "") -> list[dict[str, Any]]:
    options = [
        {
            "key": model_id,
            "id": model_id,
            "version": version,
            "label": version,
            "displayName": display_name,
            "source": "official",
        }
        for model_id, (version, display_name) in OFFICIAL_MODELS.items()
    ]
    current = str(current_model or "").strip()
    if current and not any(item.get("id") == current for item in options):
        options.insert(
            0,
            {
                "key": current,
                "id": current,
                "label": label_from_model_name(current),
                "displayName": current,
                "source": "local",
            },
        )
    return options


def read_model_catalog_options(settings: Settings) -> list[dict[str, Any]]:
    config_text = _read_codex_config(settings)
    current_model = _toml_string_value(config_text, "model")

    def fallback() -> list[dict[str, Any]]:
        return default_model_catalog_options(current_model)

    catalog_path = _resolve_model_catalog_path(settings, config_text)
    if not catalog_path:
        return fallback()

    try:
        parsed = json.loads(catalog_path.read_text(encoding="utf-8"))
    except OSError:
        return fallback()
    except json.JSONDecodeError:
        return fallback()

    rows = parsed.get("models") if isinstance(parsed, dict) else None
    if not isinstance(rows, list):
        return fallback()
    models = [item for item in (_normalize_model_option(row) for row in rows) if item]
    return models or fallback()


def model_options_from_display_names(settings: Settings, display_names: list[str]) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in display_names:
        text = re.sub(r"\s+", " ", str(raw or "")).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        info = model_info_from_display_name(settings, text)
        if not info.get("available"):
            continue
        model_id = str(info.get("id") or text).strip()
        if not model_id or model_id in {item.get("id") for item in options}:
            continue
        options.append(
            {
                "key": model_id,
                "id": model_id,
                "label": str(info.get("label") or label_from_model_name(text) or text),
                "displayName": str(info.get("displayName") or text),
                "source": str(info.get("source") or "official"),
            }
        )
    return options


def merge_model_option_lists(*sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in sources:
        for item in source:
            model_id = str(item.get("id") or item.get("key") or "").strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            merged.append(item)
    return merged


def find_model_option(settings: Settings, model_id: str = "") -> dict[str, Any] | None:
    target = str(model_id or "").strip()
    if not target:
        return None
    return next((item for item in read_model_catalog_options(settings) if item.get("id") == target or item.get("key") == target), None)


def model_info_from_id(settings: Settings, model_id: str = "", updated_at: str = "") -> dict[str, Any]:
    model_id = str(model_id or "").strip()
    option = find_model_option(settings, model_id)
    if option:
        return {**option, "available": True, "updatedAt": updated_at}

    if model_id in OFFICIAL_MODELS:
        version, display_name = OFFICIAL_MODELS[model_id]
        return {
            "available": True,
            "id": model_id,
            "version": version,
            "source": "official",
            "label": version,
            "displayName": display_name,
            "updatedAt": updated_at,
        }

    return {
        "available": bool(model_id),
        "id": model_id,
        "version": "",
        "source": "official" if model_id.startswith("gpt-") else "unknown" if model_id else "",
        "label": label_from_model_name(model_id),
        "displayName": model_id,
        "updatedAt": updated_at,
    }


def normalize_codex_menu_name(name: str = "") -> str:
    return re.sub(r"\s+", "-", str(name or "").strip())


def footer_label_from_menu_text(menu_text: str = "") -> str:
    text = re.sub(r"\s+", " ", str(menu_text or "")).strip()
    match = re.match(r"^GPT[-\s]+(.+)$", text, re.I)
    if match:
        return normalize_codex_menu_name(match.group(1))
    return text


def codex_menu_display_name(display_name: str = "", model_id: str = "") -> str:
    text = re.sub(r"\s+", " ", str(display_name or "").strip())
    model_id = str(model_id or "").strip()
    if model_id in OFFICIAL_MODELS:
        return OFFICIAL_MODELS[model_id][1]
    legacy = {
        "GPT-5.4 Mini": "GPT-5.4-Mini",
        "GPT-5.3 Codex": "GPT-5.3-Codex",
    }
    if text in legacy:
        return legacy[text]
    normalized = normalize_codex_menu_name(text)
    return normalized or model_id


def model_info_from_display_name(settings: Settings, display_name: str = "", updated_at: str = "") -> dict[str, Any]:
    text = re.sub(r"\s+", " ", str(display_name or "")).strip()
    if not text:
        return model_info_from_id(settings, "", updated_at)
    option = next(
        (
            item
            for item in read_model_catalog_options(settings)
            if item.get("displayName") == text
            or item.get("label") == text
            or item.get("id") == text
            or normalize_codex_menu_name(str(item.get("displayName") or "")) == normalize_codex_menu_name(text)
        ),
        None,
    )
    if option:
        return {**option, "available": True, "updatedAt": updated_at}
    footer_key = normalize_codex_menu_name(text)
    for model_id, (version, display_name) in OFFICIAL_MODELS.items():
        if footer_label_from_menu_text(display_name) == footer_key or normalize_codex_menu_name(version) == footer_key:
            return {**model_info_from_id(settings, model_id, updated_at), "footerLabel": footer_key}
    match = re.match(r"^GPT-?(\d+(?:\.\d+)?)(?:[-\s]?(Mini|Codex))?", text, re.I)
    if match:
        version = "mini" if match.group(2) and re.search("mini", match.group(2), re.I) else match.group(1)
        return {
            "available": True,
            "id": re.sub(r"\s+", "-", text.lower()),
            "version": version,
            "source": "official",
            "label": version,
            "displayName": text,
            "updatedAt": updated_at,
        }
    return {"available": True, "id": text, "version": "", "source": "unknown", "label": text, "displayName": text, "updatedAt": updated_at}


def current_model_from_items(settings: Settings, items: list[dict[str, Any]]) -> dict[str, Any]:
    model_id = ""
    updated_at = ""
    for item in items:
        payload = item.get("payload") or {}
        if item.get("type") == "session_meta" and payload.get("model"):
            model_id = str(payload.get("model") or "")
            updated_at = item.get("timestamp") or payload.get("timestamp") or updated_at
        if item.get("type") == "turn_context" and payload.get("model"):
            model_id = str(payload.get("model") or "")
            updated_at = item.get("timestamp") or updated_at
    return model_info_from_id(settings, model_id, updated_at)


def reasoning_mode_from_value(value: str = "", updated_at: str = "") -> dict[str, Any]:
    raw = str(value or "").strip()
    normalized = raw.lower()
    aliases = {
        "low": "low",
        "低": "low",
        "medium": "medium",
        "med": "medium",
        "middle": "medium",
        "中": "medium",
        "high": "high",
        "高": "high",
        "xhigh": "xhigh",
        "x-high": "xhigh",
        "extra-high": "xhigh",
        "extreme": "xhigh",
        "max": "xhigh",
        "超高": "xhigh",
        "极高": "xhigh",
    }
    key = aliases.get(normalized, "")
    target = REASONING_MODE_TARGETS.get(key)
    return {
        "available": bool(target or raw),
        "key": target["key"] if target else "",
        "value": target["value"] if target else raw,
        "label": target["label"] if target else "",
        "displayName": target["displayName"] if target else raw,
        "updatedAt": updated_at,
    }


def current_reasoning_mode_from_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    value = ""
    updated_at = ""
    for item in items:
        payload = item.get("payload") or {}
        collaboration = payload.get("collaboration_mode") if isinstance(payload.get("collaboration_mode"), dict) else {}
        settings = collaboration.get("settings") if isinstance(collaboration.get("settings"), dict) else {}
        reasoning = payload.get("reasoning") if isinstance(payload.get("reasoning"), dict) else {}
        next_value = (
            payload.get("reasoning_effort")
            or payload.get("reasoningMode")
            or payload.get("reasoning_mode")
            or settings.get("reasoning_effort")
            or reasoning.get("effort")
            or ""
        )
        if item.get("type") == "turn_context" and next_value:
            value = str(next_value)
            updated_at = item.get("timestamp") or updated_at
    return reasoning_mode_from_value(value, updated_at)


def reasoning_target_for_key(target_key: str = "", current: dict[str, Any] | None = None) -> dict[str, str]:
    explicit = str(target_key or "").strip()
    if explicit in REASONING_MODE_TARGETS:
        return REASONING_MODE_TARGETS[explicit]
    order = ["low", "medium", "high", "xhigh"]
    current_key = str((current or {}).get("key") or "")
    index = order.index(current_key) if current_key in order else 0
    return REASONING_MODE_TARGETS[order[(index + 1) % len(order)]]


def model_target_for_key(settings: Settings, target_key: str = "", current: dict[str, Any] | None = None) -> dict[str, Any]:
    explicit = str(target_key or "").strip()
    if explicit:
        option = find_model_option(settings, explicit)
        if option:
            return option
        raise ValueError("目标模型不在本机模型目录中。")
    options = read_model_catalog_options(settings)
    current_id = str((current or {}).get("id") or "")
    target = next((item for item in options if item.get("id") != current_id), None) or (options[0] if options else None)
    if not target:
        raise ValueError("未读取到可切换的本机模型。")
    return target


def label_from_model_name(name: str = "") -> str:
    text = str(name or "").strip()
    if not text:
        return ""
    return re.sub(r"^codex-", "", re.sub(r"^gpt-", "", re.sub(r"^GPT-", "", re.sub(r"[（(].*?[）)]", "", text), flags=re.I), flags=re.I), flags=re.I).strip() or text


def _normalize_model_option(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict) or row.get("visibility") == "hide":
        return None
    model_id = str(row.get("slug") or row.get("id") or row.get("model") or "").strip()
    if not model_id:
        return None
    display_name = str(row.get("display_name") or row.get("name") or row.get("label") or model_id).strip()
    return {
        "key": model_id,
        "id": model_id,
        "label": label_from_model_name(display_name or model_id),
        "displayName": display_name or model_id,
        "source": "local",
    }


def _read_codex_config(settings: Settings) -> str:
    try:
        return (settings.paths.codex_home / "config.toml").read_text(encoding="utf-8")
    except OSError:
        return ""


def _resolve_model_catalog_path(settings: Settings, config_text: str) -> Path | None:
    configured = _toml_string_value(config_text, "model_catalog_json")
    candidates: list[Path] = []
    if configured:
        configured_path = Path(configured.replace("~", str(Path.home()), 1) if configured.startswith("~") else configured).expanduser()
        candidates.append(configured_path)
    candidates.append(settings.paths.codex_home / "model_catalog.json")
    for path in candidates:
        if path.is_file():
            return path
    return None


def _toml_string_value(text: str, key: str) -> str:
    escaped = re.escape(key)
    match = re.search(rf'^\s*{escaped}\s*=\s*"([^"]*)"\s*$', text, re.M)
    return match.group(1) if match else ""
