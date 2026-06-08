from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import base64
import binascii
import re
import time
import uuid

from codex_go.config import Settings


DATA_URL_RE = re.compile(r"^data:(?P<header>[^,]*),(?P<data>.*)$", re.DOTALL)

IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "image/avif": ".avif",
    "image/bmp": ".bmp",
}

KNOWN_EXTENSIONS_BY_MIME = {
    "application/json": ".json",
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/gzip": ".gz",
    "application/x-tar": ".tar",
    "application/x-7z-compressed": ".7z",
    "application/x-rar-compressed": ".rar",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/msword": ".doc",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.ms-powerpoint": ".ppt",
    "text/csv": ".csv",
    "text/html": ".html",
    "text/markdown": ".md",
    "text/plain": ".txt",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}

TEXT_EXTENSIONS = {
    ".c",
    ".cc",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".log",
    ".md",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

BLOCKED_EXTENSIONS = {
    ".app",
    ".bat",
    ".cmd",
    ".com",
    ".dmg",
    ".exe",
    ".pkg",
    ".scr",
}


@dataclass(frozen=True)
class PreparedAttachment:
    name: str
    type: str
    path: Path
    size: int

    def response_payload(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "size": self.size, "filePath": str(self.path)}


class AttachmentError(ValueError):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def prepare_attachments(raw_attachments: list[dict[str, Any]], settings: Settings) -> list[PreparedAttachment]:
    if not raw_attachments:
        return []
    if len(raw_attachments) > settings.limits.max_attachments:
        raise AttachmentError("TOO_MANY_ATTACHMENTS", f"附件太多了，最多一次发送 {settings.limits.max_attachments} 个。", 413)

    request_dir = settings.paths.upload_dir / time.strftime("%Y%m%d") / f"send-{int(time.time() * 1000)}-{uuid.uuid4().hex[:10]}"
    prepared: list[PreparedAttachment] = []
    for index, item in enumerate(raw_attachments, start=1):
        if not isinstance(item, dict):
            raise AttachmentError("BAD_ATTACHMENT", "附件格式不正确。")
        name = str(item.get("name") or f"attachment-{index}")
        declared_type = _normalize_mime(str(item.get("type") or ""))
        data_url = str(item.get("dataUrl") or "")
        mime, content = _decode_data_url(data_url, declared_type)
        detected_type = _detect_image_type(content)
        if declared_type.startswith("image/") or mime.startswith("image/") or detected_type:
            if not detected_type:
                raise AttachmentError("BAD_ATTACHMENT_TYPE", "图片附件内容无法识别。", 415)
            if mime and mime != detected_type:
                raise AttachmentError("BAD_ATTACHMENT_TYPE", "图片内容和声明的类型不一致。", 415)
            final_type = detected_type
        else:
            final_type = _safe_non_image_mime(mime or declared_type, name)
        if final_type == "image/svg+xml":
            raise AttachmentError("BAD_ATTACHMENT_TYPE", "暂不支持 SVG 图片附件。", 415)
        if _is_blocked_file_name(name):
            raise AttachmentError("BAD_ATTACHMENT_TYPE", "暂不支持发送可执行程序或安装包附件。", 415)
        if len(content) > settings.limits.max_attachment_bytes:
            limit_mb = max(1, settings.limits.max_attachment_bytes // (1024 * 1024))
            raise AttachmentError("ATTACHMENT_TOO_LARGE", f"单个附件太大了，请控制在 {limit_mb} MB 以内。", 413)

        request_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_attachment_name(index, name, _extension_for_attachment(final_type, name))
        path = request_dir / safe_name
        path.write_bytes(content)
        prepared.append(PreparedAttachment(name=safe_name, type=final_type, path=path, size=len(content)))
    return prepared


def prepare_image_attachments(raw_attachments: list[dict[str, Any]], settings: Settings) -> list[PreparedAttachment]:
    return prepare_attachments(raw_attachments, settings)


def _decode_data_url(data_url: str, declared_type: str = "") -> tuple[str, bytes]:
    match = DATA_URL_RE.match(data_url)
    if not match:
        raise AttachmentError("BAD_ATTACHMENT_DATA", "附件数据格式不正确。")
    header = match.group("header") or ""
    if not re.search(r"(^|;)base64($|;)", header, re.IGNORECASE):
        raise AttachmentError("BAD_ATTACHMENT_DATA", "附件数据格式不正确。")
    header_mime = header.split(";", 1)[0]
    mime = _normalize_mime(header_mime or declared_type)
    if mime == "image/svg+xml":
        raise AttachmentError("BAD_ATTACHMENT_TYPE", "暂不支持 SVG 图片附件。", 415)
    encoded = re.sub(r"\s+", "", match.group("data") or "")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AttachmentError("BAD_ATTACHMENT_DATA", "附件 base64 数据无法解析。") from exc
    if not content:
        raise AttachmentError("EMPTY_ATTACHMENT", "附件为空。")
    return mime, content


def _detect_image_type(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"BM"):
        return "image/bmp"
    if len(content) >= 12 and content[4:8] == b"ftyp":
        brand = content[8:12].decode("latin1", errors="ignore").lower()
        if brand in {"heic", "heix", "hevc", "hevx"}:
            return "image/heic"
        if brand in {"mif1", "msf1"}:
            return "image/heif"
        if brand == "avif":
            return "image/avif"
    return ""


def _normalize_mime(value: str = "") -> str:
    mime = value.split(";", 1)[0].strip().lower()
    return "image/jpeg" if mime == "image/jpg" else mime


def _safe_non_image_mime(mime: str, name: str) -> str:
    ext = Path(name).suffix.lower()
    if mime.startswith("text/"):
        return mime
    if ext in TEXT_EXTENSIONS and (not mime or mime == "application/octet-stream"):
        return "text/plain"
    if mime in KNOWN_EXTENSIONS_BY_MIME:
        return mime
    if mime in {"application/octet-stream", ""}:
        return "application/octet-stream"
    if mime.startswith(("application/", "audio/", "video/", "model/")):
        return mime
    return "application/octet-stream"


def _extension_for_attachment(mime: str, name: str) -> str:
    existing = Path(name).suffix
    if existing:
        return existing[:16]
    if mime in IMAGE_TYPES:
        return IMAGE_TYPES[mime]
    return KNOWN_EXTENSIONS_BY_MIME.get(mime, ".bin")


def _is_blocked_file_name(name: str) -> bool:
    return Path(name).suffix.lower() in BLOCKED_EXTENSIONS


def _safe_attachment_name(index: int, name: str, extension: str) -> str:
    stem = Path(name).stem or f"attachment-{index}"
    safe_stem = re.sub(r"[^A-Za-z0-9._ -]+", "-", stem).strip(" .-_") or f"attachment-{index}"
    safe_stem = safe_stem[:72].strip(" .-_") or f"attachment-{index}"
    return f"{index:02d}-{uuid.uuid4().hex[:8]}-{safe_stem}{extension}"
