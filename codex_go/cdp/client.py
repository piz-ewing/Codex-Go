from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.request import urlopen

from codex_go.config import CdpSettings

from .errors import CdpSocketError, CdpTimeout, CdpUnavailable


@dataclass(frozen=True)
class CdpTarget:
    id: str
    type: str
    url: str
    title: str
    web_socket_debugger_url: str


class CdpClient:
    def __init__(self, settings: CdpSettings):
        self.settings = settings

    async def list_targets(self) -> list[CdpTarget]:
        errors: list[str] = []
        hosts = [self.settings.host, "[::1]", "127.0.0.1", "localhost"]
        seen = set()
        for host in hosts:
            if host in seen:
                continue
            seen.add(host)
            url = f"http://{host}:{self.settings.port}/json/list"
            try:
                data = await asyncio.to_thread(self._fetch_json, url)
                return [
                    CdpTarget(
                        id=str(item.get("id") or ""),
                        type=str(item.get("type") or ""),
                        url=str(item.get("url") or ""),
                        title=str(item.get("title") or ""),
                        web_socket_debugger_url=str(item.get("webSocketDebuggerUrl") or ""),
                    )
                    for item in data
                    if isinstance(item, dict)
                ]
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{host}: {exc}")
        raise CdpUnavailable(f"Codex CDP 页面不可用，端口 {self.settings.port}。尝试过：{'；'.join(errors)}")

    def _fetch_json(self, url: str) -> list[dict[str, Any]]:
        with urlopen(url, timeout=self.settings.timeout_seconds) as response:  # noqa: S310
            payload = response.read()
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, list):
            raise ValueError("CDP target list is not an array")
        return data

    async def get_page_target(self) -> CdpTarget:
        targets = await self.list_targets()
        for target in targets:
            if target.type == "page" and target.web_socket_debugger_url and target.url.startswith("app://-/index.html"):
                return target
        raise CdpUnavailable("Codex CDP 已连接，但没有找到 Codex Desktop page target。")

    async def inspect(self) -> dict[str, Any]:
        try:
            targets = await self.list_targets()
            page = next(
                (
                    target
                    for target in targets
                    if target.type == "page" and target.web_socket_debugger_url and target.url.startswith("app://-/index.html")
                ),
                None,
            )
            return {
                "ok": bool(page),
                "port": self.settings.port,
                "host": self.settings.host,
                "page": page.__dict__ if page else None,
                "targets": [target.__dict__ for target in targets],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "port": self.settings.port,
                "host": self.settings.host,
                "error": str(exc),
                "targets": [],
            }

    async def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            import websockets
        except Exception as exc:  # noqa: BLE001
            raise CdpSocketError("当前 Python 环境缺少 websockets，无法连接 CDP。") from exc

        target = await self.get_page_target()
        request = {"id": 1, "method": method, "params": params or {}}
        try:
            async with websockets.connect(target.web_socket_debugger_url, open_timeout=self.settings.timeout_seconds) as websocket:
                await asyncio.wait_for(websocket.send(json.dumps(request)), timeout=self.settings.timeout_seconds)
                while True:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=self.settings.timeout_seconds)
                    message = json.loads(raw)
                    if message.get("id") != 1:
                        continue
                    if message.get("error"):
                        raise CdpSocketError(json.dumps(message["error"], ensure_ascii=False))
                    return message.get("result") or {}
        except asyncio.TimeoutError as exc:
            raise CdpTimeout(f"CDP {method} 超时。") from exc
        except CdpSocketError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise CdpSocketError(f"CDP WebSocket 连接失败：{exc}") from exc

    async def set_file_input_files(self, prepare_expression: str, files: list[str], after_expression: str) -> dict[str, Any]:
        try:
            import websockets
        except Exception as exc:  # noqa: BLE001
            raise CdpSocketError("当前 Python 环境缺少 websockets，无法连接 CDP。") from exc

        target = await self.get_page_target()
        request_id = 0

        async def call_on_socket(websocket: Any, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
            nonlocal request_id
            request_id += 1
            request = {"id": request_id, "method": method, "params": params or {}}
            await asyncio.wait_for(websocket.send(json.dumps(request)), timeout=self.settings.timeout_seconds)
            while True:
                raw = await asyncio.wait_for(websocket.recv(), timeout=self.settings.timeout_seconds)
                message = json.loads(raw)
                if message.get("id") != request_id:
                    continue
                if message.get("error"):
                    raise CdpSocketError(json.dumps(message["error"], ensure_ascii=False))
                return message.get("result") or {}

        def evaluation_value(result: dict[str, Any], fallback: str) -> Any:
            if result.get("exceptionDetails"):
                raise CdpSocketError(result["exceptionDetails"].get("text") or fallback)
            return (result.get("result") or {}).get("value")

        try:
            async with websockets.connect(target.web_socket_debugger_url, open_timeout=self.settings.timeout_seconds) as websocket:
                prepared_result = await call_on_socket(
                    websocket,
                    "Runtime.evaluate",
                    {"expression": prepare_expression, "returnByValue": True, "awaitPromise": True},
                )
                prepared = evaluation_value(prepared_result, "CDP 准备附件入口失败。")
                if not isinstance(prepared, dict) or not prepared.get("ok"):
                    return prepared if isinstance(prepared, dict) else {"ok": False, "reason": "CDP 准备附件入口失败。"}

                object_result = await call_on_socket(
                    websocket,
                    "Runtime.evaluate",
                    {"expression": "window.__codexGoAttachmentInput || null", "returnByValue": False},
                )
                if object_result.get("exceptionDetails"):
                    raise CdpSocketError(object_result["exceptionDetails"].get("text") or "CDP 读取附件入口失败。")
                object_id = ((object_result.get("result") or {}).get("objectId")) or ""
                if not object_id:
                    return {"ok": False, "reason": "CDP 没有拿到附件 input 对象。", "prepared": prepared}

                request_node_error = ""
                node_id = 0
                try:
                    await call_on_socket(websocket, "DOM.enable")
                    node_result = await call_on_socket(websocket, "DOM.requestNode", {"objectId": object_id})
                    node_id = int(node_result.get("nodeId") or 0)
                except CdpSocketError as exc:
                    request_node_error = str(exc)

                file_input_target = {
                    "nodeId": node_id,
                    "usedObjectIdFallback": not bool(node_id),
                    "requestNodeError": request_node_error,
                }
                set_params: dict[str, Any] = {"files": files}
                if node_id:
                    set_params["nodeId"] = node_id
                else:
                    set_params["objectId"] = object_id
                try:
                    await call_on_socket(websocket, "DOM.setFileInputFiles", set_params)
                except CdpSocketError:
                    if not node_id:
                        raise
                    file_input_target["usedObjectIdFallback"] = True
                    await call_on_socket(websocket, "DOM.setFileInputFiles", {"objectId": object_id, "files": files})
                after_result = await call_on_socket(
                    websocket,
                    "Runtime.evaluate",
                    {"expression": after_expression, "returnByValue": True, "awaitPromise": True},
                )
                after = evaluation_value(after_result, "CDP 触发附件事件失败。")
                if not isinstance(after, dict):
                    return {"ok": False, "reason": "CDP 触发附件事件失败。", "prepared": prepared}
                return {"ok": bool(after.get("ok")), **after, "prepared": prepared, "fileInputTarget": file_input_target}
        except asyncio.TimeoutError as exc:
            raise CdpTimeout("CDP 附件上传超时。") from exc
        except CdpSocketError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise CdpSocketError(f"CDP 附件上传失败：{exc}") from exc

    async def evaluate(self, expression: str) -> Any:
        result = await self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        if result.get("exceptionDetails"):
            raise CdpSocketError(result["exceptionDetails"].get("text") or "Codex CDP DOM 执行失败。")
        return (result.get("result") or {}).get("value")
