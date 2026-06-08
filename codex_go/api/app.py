from __future__ import annotations

from typing import Any
import asyncio
import mimetypes
import socket

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from codex_go.cdp.errors import CdpError
from codex_go.codex import is_codex_thread_id, list_threads, parse_history, parse_status
from codex_go.codex.models import model_info_from_display_name, reasoning_mode_from_value
from codex_go.config import Settings, load_settings
from codex_go.services import AppServices
from codex_go.services.codex_bridge import BridgeError

from .deps import get_services, get_settings, require_token


class SendRequest(BaseModel):
    clientRequestId: str = ""
    text: str = ""
    target: str = "codex"
    threadId: str = ""
    previousThreadId: str = ""
    expectedCwd: str = ""
    newThreadScope: str = ""
    projectPath: str = ""
    isProjectThread: bool | None = None
    expectNewThread: bool = False
    directPasteWithoutClick: bool = False
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class StopRequest(BaseModel):
    threadId: str = ""


class ThreadActionRequest(BaseModel):
    threadId: str
    action: str
    name: str = ""


class NewThreadRequest(BaseModel):
    threadId: str = ""
    projectPath: str = ""
    scope: str = ""
    isProjectThread: bool | None = None


class PendingSendActionRequest(BaseModel):
    threadId: str
    action: str
    text: str = ""


class PermissionActionRequest(BaseModel):
    threadId: str
    callId: str = ""
    action: str


class SwitchRequest(BaseModel):
    threadId: str = ""
    target: str = ""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Codex Go", version="0.1.0")
    app.state.settings = settings
    app.state.services = AppServices.create(settings)
    app.state.title_status_task = None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["content-type", "x-codex-go-token"],
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"ok": False, "message": str(exc.detail)})

    @app.exception_handler(CdpError)
    async def cdp_exception_handler(_: Request, exc: CdpError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"ok": False, "code": exc.code, "message": str(exc)})

    @app.exception_handler(BridgeError)
    async def bridge_exception_handler(_: Request, exc: BridgeError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=exc.payload())

    @app.on_event("startup")
    async def startup_title_status() -> None:
        app.state.title_status_task = asyncio.create_task(_title_status_loop(app.state.services))

    @app.on_event("shutdown")
    async def shutdown_services() -> None:
        task = getattr(app.state, "title_status_task", None)
        if task:
            task.cancel()

    @app.get("/codex/health")
    async def health(_: None = Depends(require_token), settings: Settings = Depends(get_settings)) -> dict[str, Any]:
        return {"ok": True, "service": settings.service_slug, "appName": settings.app_name, "time": _iso_now()}

    @app.get("/codex/cdp-health")
    async def cdp_health(_: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        status = await services.cdp.inspect()
        return {
            "ok": bool(status.get("ok")),
            **status,
            "code": "CODEX_CDP_READY" if status.get("ok") else "CODEX_CDP_UNAVAILABLE",
            "message": "Codex CDP 可连接。" if status.get("ok") else f"Codex CDP 端口 {services.settings.cdp.port} 不可用或没有 page target。",
        }

    @app.get("/codex/config")
    async def client_config(_: None = Depends(require_token), settings: Settings = Depends(get_settings), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        return {
            "ok": True,
            "service": settings.service_slug,
            "appName": settings.app_name,
            "localOnly": True,
            "localApiBases": _lan_api_bases(settings.port),
            "modelOptions": services.bridge.model_options(),
            "appearanceSettings": services.state.read().get("appearanceSettings") or {"colorFlowEnabled": True},
        }

    @app.get("/codex/appearance-settings")
    async def get_appearance(_: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        return {"ok": True, "settings": services.state.read().get("appearanceSettings") or {"colorFlowEnabled": True}}

    @app.post("/codex/appearance-settings")
    async def post_appearance(payload: dict[str, Any], _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        def update(state: dict[str, Any]) -> dict[str, Any]:
            current = state.get("appearanceSettings") if isinstance(state.get("appearanceSettings"), dict) else {}
            incoming = payload.get("settings") if isinstance(payload.get("settings"), dict) else payload
            state["appearanceSettings"] = {**current, **incoming}
            return state

        state = services.state.update(update)
        return {"ok": True, "settings": state.get("appearanceSettings") or {}, "message": "设置已保存"}

    @app.get("/codex/threads")
    async def threads(limit: int = 80, _: None = Depends(require_token), settings: Settings = Depends(get_settings)) -> dict[str, Any]:
        return {"ok": True, "threads": list_threads(settings, limit)}

    @app.get("/codex/history")
    async def history(thread: str = "", limit: int = 120, _: None = Depends(require_token), settings: Settings = Depends(get_settings)) -> JSONResponse:
        result = parse_history(settings, thread, limit)
        status = 400 if result.get("ok") is False else 200
        return JSONResponse(status_code=status, content=result)

    @app.get("/codex/status")
    async def status(
        since: str = "",
        thread: str = "",
        session: str = "",
        expectNewThread: bool = False,
        excludeThreadId: str = "",
        cwd: str = "",
        _: None = Depends(require_token),
        settings: Settings = Depends(get_settings),
        services: AppServices = Depends(get_services),
    ) -> dict[str, Any]:
        result = parse_status(
            settings,
            since=since,
            thread_id=thread,
            session_file=session,
            expect_new_thread=expectNewThread,
            exclude_thread_id=excludeThreadId,
            cwd=cwd,
        )
        if thread and result.get("available") and not result.get("permissionRequest"):
            try:
                gui = await services.cdp.read_gui_status(thread)
            except Exception:
                gui = {}
            gui_request = gui.get("permissionRequest") if isinstance(gui, dict) else None
            if gui.get("activeThreadMatches") is not False and isinstance(gui_request, dict) and gui_request.get("pending"):
                result["status"] = "permission_required"
                result["active"] = True
                result["permissionRequest"] = gui_request
                result["preview"] = f"Codex 正在等待你确认：{gui_request.get('justification') or gui_request.get('text') or '请在 Codex 桌面端确认。'}"
                result["steps"] = [
                    *[step for step in (result.get("steps") or []) if isinstance(step, dict)],
                    {
                        "kind": "permission",
                        "label": "等待确认",
                        "text": gui_request.get("text") or gui_request.get("justification") or "Codex 正在等待确认。",
                        "time": result.get("updatedAt") or "",
                        "callId": gui_request.get("callId") or "",
                        "pending": True,
                    },
                ][-30:]
        return result

    @app.get("/codex/gui-status")
    async def gui_status(thread: str = "", _: None = Depends(require_token), settings: Settings = Depends(get_settings), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        result = await services.cdp.read_gui_status(thread)
        updated_at = _iso_now()
        return {
            "ok": True,
            "available": bool(result.get("ok")),
            **result,
            "model": model_info_from_display_name(settings, result.get("modelDisplayName") or "", updated_at),
            "reasoningMode": reasoning_mode_from_value(result.get("reasoningLabel") or "", updated_at),
            "updatedAt": updated_at,
        }

    @app.post("/send")
    async def send(payload: SendRequest, _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        return await services.bridge.send(payload)

    @app.post("/codex/stop")
    async def stop(payload: StopRequest, _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> JSONResponse:
        if payload.threadId and not is_codex_thread_id(payload.threadId):
            return JSONResponse(status_code=400, content={"ok": False, "code": "BAD_THREAD_ID", "message": "线程 ID 不正确。"})
        result = await services.cdp.stop_response(payload.threadId)
        return JSONResponse(status_code=200, content={"ok": True, "threadId": payload.threadId, "result": result, "message": "已向 Codex 发送终止指令。"})

    @app.post("/codex/select")
    async def select_thread(payload: StopRequest, _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> JSONResponse:
        if payload.threadId and not is_codex_thread_id(payload.threadId):
            return JSONResponse(status_code=400, content={"ok": False, "code": "BAD_THREAD_ID", "message": "线程 ID 不正确。"})
        result = await services.cdp.select_thread(payload.threadId)
        return JSONResponse(status_code=200, content={"ok": True, "threadId": payload.threadId, "result": result, "message": "已切换到 Codex 线程。"})

    @app.post("/codex/thread-action")
    async def thread_action(payload: ThreadActionRequest, _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> JSONResponse:
        return JSONResponse(status_code=200, content=await services.bridge.thread_action(payload))

    @app.post("/codex/new-thread")
    async def new_thread(payload: NewThreadRequest, _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        return await services.bridge.create_new_thread(payload)

    @app.get("/codex/pending-sends")
    async def pending_sends(thread: str = "", _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        return await services.bridge.pending_sends(thread)

    @app.post("/codex/pending-send-action")
    async def pending_send_action(payload: PendingSendActionRequest, _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        return await services.bridge.pending_send_action(payload)

    @app.post("/codex/permission-action")
    async def permission_action(payload: PermissionActionRequest, _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        return await services.bridge.permission_action(payload)

    @app.get("/codex/model-options")
    async def model_options(_: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        return {"ok": True, "modelOptions": await services.bridge.resolve_model_options()}

    @app.post("/codex/model-switch")
    async def model_switch(payload: SwitchRequest, _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        return await services.bridge.switch_model(payload)

    @app.post("/codex/reasoning-mode")
    async def reasoning_mode(payload: SwitchRequest, _: None = Depends(require_token), services: AppServices = Depends(get_services)) -> dict[str, Any]:
        return await services.bridge.switch_reasoning(payload)

    @app.get("/{full_path:path}")
    async def static_files(full_path: str, request: Request, settings: Settings = Depends(get_settings)) -> Response:
        return _serve_static(settings, full_path, request)

    return app


def _serve_static(settings: Settings, full_path: str, request: Request) -> Response:
    path = settings.paths.public_dir / (full_path or "index.html")
    try:
        resolved = path.resolve()
        public_root = settings.paths.public_dir.resolve()
        resolved.relative_to(public_root)
    except Exception:
        raise HTTPException(status_code=404, detail={"ok": False, "code": "NOT_FOUND", "message": "Not found"})
    if resolved.is_dir():
        resolved = resolved / "index.html"
    if not resolved.exists():
        raise HTTPException(status_code=404, detail={"ok": False, "code": "NOT_FOUND", "message": "Not found"})
    stat = resolved.stat()
    media_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
    response = FileResponse(resolved, media_type=media_type)
    if resolved.suffix in {".html", ".js", ".css", ".webmanifest"}:
        response.headers["Cache-Control"] = "no-store"
    else:
        response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Content-Length"] = str(stat.st_size)
    if resolved.suffix == ".html" and request.query_params.get("token") == settings.token:
        response.set_cookie("codexGoToken", settings.token, max_age=31536000, samesite="lax")
    return response


def _lan_api_bases(port: int) -> list[str]:
    bases = {f"http://localhost:{port}"}
    try:
        hostname = socket.gethostname()
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            if family == socket.AF_INET:
                address = sockaddr[0]
                if not address.startswith("127."):
                    bases.add(f"http://{address}:{port}")
    except OSError:
        pass
    return sorted(bases)


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


async def _title_status_loop(services: AppServices) -> None:
    last_injected = 0.0
    while True:
        try:
            now = asyncio.get_running_loop().time()
            if now - last_injected >= 1.8:
                await services.cdp.inject_title_status(
                    {
                        "appName": services.settings.app_name,
                        "apiBase": f"http://127.0.0.1:{services.settings.port}",
                        "token": services.settings.token,
                        "service": {"online": True, "label": "Go", "fallbackLabel": "Go"},
                        "updatedAt": _iso_now(),
                    }
                )
                last_injected = now
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(0.9)
