from __future__ import annotations

from dataclasses import dataclass

from codex_go.cdp import CdpClient, CodexCdpActions
from codex_go.config import Settings
from codex_go.state import StateStore
from .codex_bridge import CodexBridgeService


@dataclass
class AppServices:
    settings: Settings
    state: StateStore
    cdp: CodexCdpActions
    bridge: CodexBridgeService

    @classmethod
    def create(cls, settings: Settings) -> "AppServices":
        state = StateStore(settings)
        cdp = CodexCdpActions(CdpClient(settings.cdp))
        return cls(
            settings=settings,
            state=state,
            cdp=cdp,
            bridge=CodexBridgeService(settings=settings, cdp=cdp, state=state),
        )
