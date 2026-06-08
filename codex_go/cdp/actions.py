from __future__ import annotations

import asyncio
import mimetypes
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .client import CdpClient
from .dom import (
    attachment_drop_target_expression,
    attachment_snapshot_expression,
    click_send_expression,
    click_thread_expression,
    focus_composer_expression,
    new_thread_expression,
    pending_send_action_expression,
    pending_sends_expression,
    permission_action_expression,
    read_gui_status_expression,
    stop_response_expression,
    list_model_options_expression,
    switch_model_expression,
    switch_reasoning_expression,
    thread_action_expression,
    title_status_expression,
)
from .errors import CdpDomError


class CodexCdpActions:
    def __init__(self, client: CdpClient):
        self.client = client

    async def inspect(self) -> dict[str, Any]:
        return await self.client.inspect()

    async def read_gui_status(self, thread_id: str = "") -> dict[str, Any]:
        result = await self.client.evaluate(read_gui_status_expression(thread_id))
        if not isinstance(result, dict) or not result.get("ok"):
            raise CdpDomError("读取 Codex GUI 状态失败。")
        return result

    async def inject_title_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self.client.evaluate(title_status_expression(payload))
        if not isinstance(result, dict) or not result.get("ok"):
            raise CdpDomError("注入 Codex Go 状态胶囊失败。")
        return result

    async def select_thread(self, thread_id: str, title: str = "") -> dict[str, Any]:
        if not thread_id:
            return {"ok": True, "skipped": True}
        result = await self.client.evaluate(click_thread_expression(thread_id, title))
        if not isinstance(result, dict) or not result.get("ok"):
            raise CdpDomError(str((result or {}).get("reason") or "CDP 切线程失败。"))
        await asyncio.sleep(0.56)
        return result

    async def send_text(self, text: str, thread_id: str = "", title: str = "", attachments: list[str | Path] | None = None) -> dict[str, Any]:
        attachment_paths = [str(Path(path).expanduser().resolve()) for path in attachments or []]
        selected = await self.select_thread(thread_id, title) if thread_id else {"ok": True, "skipped": True}
        focused = await self.client.evaluate(focus_composer_expression(clear=True))
        if not isinstance(focused, dict) or not focused.get("ok"):
            raise CdpDomError(str((focused or {}).get("reason") or "CDP 聚焦 Codex 输入框失败。"))
        uploaded: dict[str, Any] = {"ok": True, "fileCount": 0, "skipped": True}
        if attachment_paths:
            uploaded = await self._drag_attachments(attachment_paths)
            if not isinstance(uploaded, dict) or not uploaded.get("ok"):
                raise CdpDomError(str((uploaded or {}).get("reason") or "CDP 添加附件失败。"))
            await asyncio.sleep(0.38)
        if text:
            await self.client.call("Input.insertText", {"text": str(text)})
            await asyncio.sleep(0.08)
        if attachment_paths:
            sent = await self._submit_by_enter()
        else:
            sent = await self.client.evaluate(click_send_expression())
            if not isinstance(sent, dict) or not sent.get("ok"):
                raise CdpDomError(str((sent or {}).get("reason") or "CDP 点击发送按钮失败。"))
        await asyncio.sleep(0.18)
        return {"ok": True, "method": "cdp", "selected": selected, "attachments": uploaded, "sent": sent}

    async def _drag_attachments(self, attachment_paths: list[str]) -> dict[str, Any]:
        payloads = _file_payloads(attachment_paths)
        before = await self.client.evaluate(attachment_snapshot_expression(payloads))
        target = await self.client.evaluate(attachment_drop_target_expression())
        if not isinstance(target, dict) or not target.get("ok"):
            raise CdpDomError(str((target or {}).get("reason") or "找不到可拖拽的 Codex 输入区域。"))
        items = [
            {
                "mimeType": payload.get("type") or "application/octet-stream",
                "data": payload.get("name") or "attachment",
                "title": payload.get("name") or "attachment",
                "baseURL": "",
            }
            for payload in payloads
        ]
        data = {"items": items, "files": attachment_paths, "dragOperationsMask": 1}
        common = {"x": int(target["x"]), "y": int(target["y"]), "data": data}
        await self.client.call("Input.dispatchDragEvent", {"type": "dragEnter", **common})
        await asyncio.sleep(0.12)
        await self.client.call("Input.dispatchDragEvent", {"type": "dragOver", **common})
        await asyncio.sleep(0.12)
        await self.client.call("Input.dispatchDragEvent", {"type": "drop", **common})
        waited = await self._wait_for_attachment_acceptance(before if isinstance(before, dict) else {}, payloads)
        if not waited.get("ok"):
            return {
                "ok": False,
                "reason": "Codex Desktop 没有接收原生拖拽附件，已取消发送以避免只发送文字。",
                "method": "native-drag",
                "fileCount": len(attachment_paths),
                "target": target,
                "snapshot": waited.get("snapshot"),
                "before": before,
            }
        return {
            "ok": True,
            "method": "native-drag",
            "fileCount": len(attachment_paths),
            "target": target,
            "snapshot": waited.get("snapshot"),
            "before": before,
        }

    async def _wait_for_attachment_acceptance(self, before: dict[str, Any], payloads: list[dict[str, str]], timeout_seconds: float = 3.6) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        last: dict[str, Any] = {}
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.18)
            snapshot = await self.client.evaluate(attachment_snapshot_expression(payloads))
            if isinstance(snapshot, dict):
                last = snapshot
                if _attachment_snapshot_increased(before, snapshot, len(payloads)):
                    return {"ok": True, "snapshot": snapshot}
        return {"ok": False, "snapshot": last}

    async def _submit_by_enter(self) -> dict[str, Any]:
        event = {
            "key": "Enter",
            "code": "Enter",
            "windowsVirtualKeyCode": 13,
            "nativeVirtualKeyCode": 13,
            "modifiers": 0,
        }
        await self.client.call("Input.dispatchKeyEvent", {"type": "keyDown", **event})
        await self.client.call("Input.dispatchKeyEvent", {"type": "keyUp", **event})
        return {"ok": True, "method": "enter"}

    async def stop_response(self, thread_id: str = "", title: str = "") -> dict[str, Any]:
        selected = await self.select_thread(thread_id, title) if thread_id else {"ok": True, "skipped": True}
        stopped = await self.client.evaluate(stop_response_expression())
        if not isinstance(stopped, dict) or not stopped.get("ok"):
            raise CdpDomError(str((stopped or {}).get("reason") or "CDP 停止回复失败。"))
        return {"ok": True, "selected": selected, "stopped": stopped}

    async def create_new_thread(self, project_name: str = "", anchor_thread_id: str = "") -> dict[str, Any]:
        selected = await self.select_thread(anchor_thread_id) if anchor_thread_id else {"ok": True, "skipped": True}
        result = await self.client.evaluate(new_thread_expression(project_name))
        if not isinstance(result, dict) or not result.get("ok"):
            raise CdpDomError(str((result or {}).get("reason") or "CDP 新建线程失败。"))
        await asyncio.sleep(0.74)
        return {"ok": True, "selected": selected, **result}

    async def list_pending_sends(self, thread_id: str) -> dict[str, Any]:
        selected = await self.select_thread(thread_id) if thread_id else {"ok": True, "skipped": True}
        result = await self.client.evaluate(pending_sends_expression())
        if not isinstance(result, dict) or not result.get("ok"):
            raise CdpDomError(str((result or {}).get("reason") or "CDP 读取排队消息失败。"))
        return {"ok": True, "selected": selected, **result}

    async def run_pending_send_action(self, thread_id: str, action: str, text_hint: str = "") -> dict[str, Any]:
        normalized = "delete" if action == "delete" else "guide" if action == "guide" else ""
        if not normalized:
            raise CdpDomError("排队消息操作不正确。")
        selected = await self.select_thread(thread_id) if thread_id else {"ok": True, "skipped": True}
        result = await self.client.evaluate(pending_send_action_expression(normalized, text_hint))
        if not isinstance(result, dict) or not result.get("ok"):
            raise CdpDomError(str((result or {}).get("reason") or "CDP 点击排队消息按钮失败。"))
        await asyncio.sleep(0.18)
        return {"ok": True, "selected": selected, **result}

    async def resolve_permission(self, thread_id: str, action: str, permission_request: dict[str, Any]) -> dict[str, Any]:
        selected = await self.select_thread(thread_id) if thread_id else {"ok": True, "skipped": True}
        result = await self.client.evaluate(
            permission_action_expression(
                action,
                str(permission_request.get("command") or ""),
                str(permission_request.get("justification") or permission_request.get("text") or ""),
            )
        )
        if not isinstance(result, dict) or not result.get("ok"):
            raise CdpDomError(str((result or {}).get("reason") or "CDP 点击权限按钮失败。"))
        await asyncio.sleep(0.18)
        return {"ok": True, "selected": selected, **result}

    async def switch_model(self, thread_id: str, target_display_name: str) -> dict[str, Any]:
        selected = await self.select_thread(thread_id) if thread_id else {"ok": True, "skipped": True}
        result = await self.client.evaluate(switch_model_expression(target_display_name))
        if not isinstance(result, dict) or not result.get("ok"):
            raise CdpDomError(str((result or {}).get("reason") or f"CDP 模型切换失败：{target_display_name}"))
        await asyncio.sleep(0.18)
        return {"ok": True, "selected": selected, **result}

    async def list_model_options(self) -> dict[str, Any]:
        result = await self.client.evaluate(list_model_options_expression())
        if not isinstance(result, dict):
            raise CdpDomError("读取 Codex 模型菜单失败。")
        return result

    async def switch_reasoning(self, thread_id: str, target_display_name: str) -> dict[str, Any]:
        selected = await self.select_thread(thread_id) if thread_id else {"ok": True, "skipped": True}
        result = await self.client.evaluate(switch_reasoning_expression(target_display_name))
        if not isinstance(result, dict) or not result.get("ok"):
            raise CdpDomError(str((result or {}).get("reason") or f"CDP 推理模式切换失败：{target_display_name}"))
        await asyncio.sleep(0.18)
        return {"ok": True, "selected": selected, **result}

    async def run_thread_action(self, thread_id: str, command: str, *, name: str = "", pinned: bool = True) -> dict[str, Any]:
        labels = {
            "archive": "归档对话",
            "pin": "置顶对话" if pinned else "取消置顶对话",
            "rename": "重命名对话",
        }
        action_label = labels.get(command, "")
        if not action_label:
            raise CdpDomError("不支持的线程操作。")
        selected = await self.select_thread(thread_id)
        result = await self.client.evaluate(thread_action_expression(command, action_label, name))
        if not isinstance(result, dict) or not result.get("ok"):
            raise CdpDomError(str((result or {}).get("reason") or f"CDP 线程操作失败：{command}"))
        await asyncio.sleep(0.18)
        return {"ok": True, "selected": selected, **result}

    async def with_cdp(self, fn: Callable[["CodexCdpActions"], Any]) -> Any:
        return await fn(self)


def _file_payloads(paths: list[str]) -> list[dict[str, str]]:
    payloads: list[dict[str, str]] = []
    for path_value in paths:
        path = Path(path_value)
        payloads.append({
            "path": str(path),
            "name": path.name,
            "type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        })
    return payloads


def _attachment_snapshot_score(snapshot: dict[str, Any]) -> int:
    return len(snapshot.get("matchedNames") or []) * 100 + int(snapshot.get("likelyCount") or 0) * 3 + int(snapshot.get("imageCount") or 0) + int(snapshot.get("previewCount") or 0)


def _attachment_snapshot_increased(before: dict[str, Any], after: dict[str, Any], expected_count: int) -> bool:
    matched = len(after.get("matchedNames") or [])
    if matched >= min(expected_count, 1):
        return True
    if int(after.get("imageCount") or 0) > int(before.get("imageCount") or 0):
        return True
    if int(after.get("previewCount") or 0) > int(before.get("previewCount") or 0):
        return True
    if int(after.get("likelyCount") or 0) > int(before.get("likelyCount") or 0):
        return True
    return _attachment_snapshot_score(after) > _attachment_snapshot_score(before) + 2
