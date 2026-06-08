class CdpError(RuntimeError):
    code = "CODEX_CDP_FAILED"


class CdpUnavailable(CdpError):
    code = "CODEX_CDP_UNAVAILABLE"


class CdpSocketError(CdpError):
    code = "CODEX_CDP_SOCKET_FAILED"


class CdpDomError(CdpError):
    code = "CODEX_CDP_DOM_FAILED"


class CdpTimeout(CdpError):
    code = "CODEX_CDP_FAILED"
