"""Length-prefixed frames between gateway and worker (standard library only).

Frame: 4-byte big-endian header length, 4-byte payload length, UTF-8 JSON header, payload.
"""

from __future__ import annotations

import json
import struct

TYPES = {"describe", "load", "synthesize", "cancel", "ready", "loaded", "start", "chunk", "done", "error"}
_PREFIX = struct.Struct(">II")


class ProtocolError(Exception):
    pass


def encode_frame(header: dict, payload: bytes = b"") -> bytes:
    h = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _PREFIX.pack(len(h), len(payload)) + h + payload


def write_frame(stream, header: dict, payload: bytes = b"") -> None:
    stream.write(encode_frame(header, payload))
    stream.flush()


def _read_exact(stream, n: int, *, allow_eof: bool = False) -> bytes | None:
    data = b""
    while len(data) < n:
        part = stream.read(n - len(data))
        if not part:
            if allow_eof and not data:
                return None
            raise ProtocolError("truncated frame")
        data += part
    return data


def read_frame(stream) -> tuple[dict, bytes] | None:
    prefix = _read_exact(stream, _PREFIX.size, allow_eof=True)
    if prefix is None:
        return None
    hlen, plen = _PREFIX.unpack(prefix)
    header_bytes = _read_exact(stream, hlen)
    payload = _read_exact(stream, plen) if plen else b""
    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtocolError("invalid frame header") from exc
    return header, payload
