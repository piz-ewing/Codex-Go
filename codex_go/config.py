from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import secrets
import tempfile


REPO_ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str = "") -> str:
    return os.environ.get(f"CODEX_GO_{name}") or default


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _int_env(name: str, default: int) -> int:
    raw = _env(name, str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class CdpSettings:
    host: str
    port: int
    timeout_seconds: float


@dataclass(frozen=True)
class PathSettings:
    public_dir: Path
    state_dir: Path
    state_file: Path
    codex_home: Path
    sessions_dir: Path
    session_index: Path
    desktop_logs_dir: Path
    upload_dir: Path


@dataclass(frozen=True)
class LimitSettings:
    max_body_bytes: int
    max_text_length: int
    max_attachments: int
    max_attachment_bytes: int
    max_history_messages: int
    session_tail_bytes: int
    activity_tail_bytes: int
    history_tail_bytes: int
    history_initial_tail_bytes: int
    title_scan_bytes: int


@dataclass(frozen=True)
class Settings:
    app_name: str
    service_slug: str
    host: str
    port: int
    token: str
    cdp: CdpSettings
    paths: PathSettings
    limits: LimitSettings


def _default_token_file() -> Path:
    return Path.home() / "Library/Application Support/Codex Go/CDP Worker/codex-go-token"


def _load_access_token() -> str:
    env_token = os.environ.get("CODEX_GO_TOKEN", "").strip()
    if env_token:
        return env_token
    token_file = _path(_env("TOKEN_FILE", str(_default_token_file())))
    if token_file.is_file():
        token = token_file.read_text(encoding="utf-8").strip()
        if token:
            return token
    return secrets.token_urlsafe(12)


def load_settings() -> Settings:
    app_name = _env("APP_NAME", os.environ.get("CODEX_GO_APP_NAME", "Codex Go"))
    host = os.environ.get("HOST") or _env("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT") or _env("PORT", "8080"))
    token = _load_access_token()

    codex_home = _path(_env("CODEX_HOME", str(Path.home() / ".codex")))
    sessions_dir = _path(_env("SESSIONS_DIR", str(codex_home / "sessions")))
    session_index = _path(_env("SESSION_INDEX", str(codex_home / "session_index.jsonl")))
    state_dir = _path(_env("STATE_DIR", str(Path.home() / ".codex-go")))
    public_dir = _path(_env("PUBLIC_DIR", str(REPO_ROOT / "public")))

    paths = PathSettings(
        public_dir=public_dir,
        state_dir=state_dir,
        state_file=state_dir / "state.json",
        codex_home=codex_home,
        sessions_dir=sessions_dir,
        session_index=session_index,
        desktop_logs_dir=_path(_env("DESKTOP_LOGS_DIR", str(Path.home() / "Library" / "Logs" / "com.openai.codex"))),
        upload_dir=_path(_env("UPLOAD_DIR", str(Path(tempfile.gettempdir()) / "codex-go-uploads"))),
    )

    limits = LimitSettings(
        max_body_bytes=_int_env("MAX_BODY_BYTES", 28 * 1024 * 1024),
        max_text_length=_int_env("MAX_TEXT_LENGTH", 8000),
        max_attachments=_int_env("MAX_ATTACHMENTS", 6),
        max_attachment_bytes=_int_env("MAX_ATTACHMENT_BYTES", 8 * 1024 * 1024),
        max_history_messages=_int_env("MAX_HISTORY_MESSAGES", 120),
        session_tail_bytes=_int_env("SESSION_TAIL_BYTES", 5 * 1024 * 1024),
        activity_tail_bytes=_int_env("ACTIVITY_TAIL_BYTES", 512 * 1024),
        history_tail_bytes=_int_env("HISTORY_TAIL_BYTES", 128 * 1024 * 1024),
        history_initial_tail_bytes=_int_env("HISTORY_INITIAL_TAIL_BYTES", 8 * 1024 * 1024),
        title_scan_bytes=_int_env("TITLE_SCAN_BYTES", 12 * 1024 * 1024),
    )

    cdp_timeout_ms = _int_env("CDP_TIMEOUT_MS", 5000)
    cdp = CdpSettings(
        host=_env("CDP_HOST", "localhost"),
        port=_int_env("CDP_PORT", 39443),
        timeout_seconds=max(0.1, cdp_timeout_ms / 1000),
    )

    return Settings(
        app_name=app_name,
        service_slug="codex-go",
        host=host,
        port=port,
        token=token,
        cdp=cdp,
        paths=paths,
        limits=limits,
    )
