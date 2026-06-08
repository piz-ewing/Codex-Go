from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, Query, Request

from codex_go.config import Settings
from codex_go.services import AppServices


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_services(request: Request) -> AppServices:
    return request.app.state.services


def require_token(
    request: Request,
    token: str = Query(default=""),
    x_codex_go_token: Annotated[str, Header(alias="x-codex-go-token")] = "",
) -> None:
    settings: Settings = request.app.state.settings
    cookie_token = request.cookies.get("codexGoToken") or ""
    provided = token or x_codex_go_token or cookie_token
    if provided != settings.token:
        raise HTTPException(status_code=401, detail={"ok": False, "code": "UNAUTHORIZED", "message": "访问令牌不正确。"})
