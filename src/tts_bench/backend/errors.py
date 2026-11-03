"""Domain errors of the gateway, mapped to ErrorBody by app.py (contracts/api.md)."""

from __future__ import annotations

STATUS = {
    "bad_request": 400,
    "unknown_engine": 404,
    "unknown_voice": 400,
    "voice_not_permitted": 403,
    "engine_unavailable": 409,
    "text_empty": 400,
    "text_too_long": 400,
    "engine_busy": 429,
    "synthesis_failed": 500,
    "empty_audio": 500,
    "worker_crashed": 500,
    "worker_timeout": 504,
    "load_failed": 500,
    "cancelled": 499,
}


class BackendError(Exception):
    """`extra` holds the optional ErrorBody fields (available, limit, received, queue_depth, ...)."""

    def __init__(self, code: str, message: str, **extra) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = {k: v for k, v in extra.items() if v is not None}

    @property
    def status(self) -> int:
        return STATUS.get(self.code, 500)

    def body(self) -> dict:
        return {"error": self.code, "message": self.message, **self.extra}
