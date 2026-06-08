from __future__ import annotations

from pathlib import Path
import json
import os
import re
import time
from typing import Any

from codex_go.config import Settings


THREAD_RE = re.compile(r"([a-f0-9]{8}-[a-f0-9-]{27,})\.jsonl$", re.I)


def is_codex_thread_id(value: str | None) -> bool:
    return bool(isinstance(value, str) and re.match(r"^[a-f0-9]{8}-[a-f0-9-]{27,}$", value, re.I))


def thread_id_from_session_file(file: str | Path) -> str:
    match = THREAD_RE.search(Path(file).name if file else "")
    return match.group(1) if match else ""


class SessionStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._files_cache_at = 0.0
        self._files_cache: list[Path] = []

    def list_session_files(self, force: bool = False) -> list[Path]:
        now = time.time()
        if not force and self._files_cache and now - self._files_cache_at <= 1.2:
            return self._files_cache
        root = self.settings.paths.sessions_dir
        if not root.exists():
            self._files_cache = []
            self._files_cache_at = now
            return []
        files = sorted(root.rglob("*.jsonl"))
        self._files_cache = files
        self._files_cache_at = now
        return files

    def find_by_thread_id(self, thread_id: str) -> Path | None:
        if not is_codex_thread_id(thread_id):
            return None
        best: Path | None = None
        best_mtime = -1.0
        for file in self.list_session_files():
            if thread_id not in file.name:
                continue
            try:
                mtime = file.stat().st_mtime
            except OSError:
                continue
            if mtime > best_mtime:
                best = file
                best_mtime = mtime
        return best

    def find_by_name(self, name: str) -> Path | None:
        if not name or "/" in name or ".." in name:
            return None
        for file in self.list_session_files():
            if file.name == name:
                return file
        return None

    def find_latest(self, exclude_thread_id: str = "", after_ms: float = 0, cwd: str = "") -> Path | None:
        best: Path | None = None
        best_mtime = -1.0
        expected_cwd = os.path.normpath(cwd) if cwd else ""
        for file in self.list_session_files(force=bool(after_ms)):
            thread_id = thread_id_from_session_file(file)
            if exclude_thread_id and thread_id == exclude_thread_id:
                continue
            try:
                stat = file.stat()
            except OSError:
                continue
            if after_ms and stat.st_mtime * 1000 < after_ms - 2500:
                continue
            if expected_cwd:
                meta_cwd = os.path.normpath(str(self.read_session_meta(file).get("cwd") or ""))
                if meta_cwd != expected_cwd:
                    continue
            if stat.st_mtime > best_mtime:
                best = file
                best_mtime = stat.st_mtime
        return best

    def read_jsonl_tail_objects(self, file: Path, max_bytes: int) -> list[dict[str, Any]]:
        lines = self.read_tail_lines(file, max_bytes)
        out: list[dict[str, Any]] = []
        for line in lines:
            try:
                item = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                out.append(item)
        return out

    def read_tail_lines(self, file: Path, max_bytes: int) -> list[str]:
        try:
            size = file.stat().st_size
            start = max(0, size - max_bytes)
            with file.open("rb") as handle:
                handle.seek(start)
                data = handle.read()
        except OSError:
            return []
        text = data.decode("utf-8", errors="replace")
        if start > 0:
            _, _, text = text.partition("\n")
        return [line for line in text.splitlines() if line.strip()]

    def read_session_meta(self, file: Path) -> dict[str, Any]:
        try:
            with file.open("rb") as handle:
                data = handle.read(64 * 1024)
        except OSError:
            return {}
        for line in data.decode("utf-8", errors="replace").splitlines()[:80]:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if item.get("type") == "session_meta" and isinstance(item.get("payload"), dict):
                return item["payload"]
        return {}

    def read_thread_index(self) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        try:
            text = self.settings.paths.session_index.read_text(encoding="utf-8")
        except OSError:
            return index
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            thread_id = item.get("id")
            if not thread_id:
                continue
            index[str(thread_id)] = {
                "id": str(thread_id),
                "name": item.get("thread_name") or "",
                "updatedAt": item.get("updated_at") or "",
            }
        return index
