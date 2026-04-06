"""
Wire protocol: 4-byte big-endian length prefix + UTF-8 JSON payload.

Event types:
  mv  – mouse move delta        {"t": "mv", "dx": int, "dy": int}
  mc  – mouse click             {"t": "mc", "b": "left|right|middle", "p": bool}
  ms  – mouse scroll            {"t": "ms", "dx": float, "dy": float}
  kp  – key press/release       {"t": "kp", "k": "<key_name>", "p": bool}
  sw  – switch control          {"t": "sw", "dir": "to_client|to_server"}
  ping                          {"t": "ping"}
"""

import json
import struct

_HEADER = struct.Struct(">I")
HEADER_SIZE = _HEADER.size


def encode(event: dict) -> bytes:
    payload = json.dumps(event, separators=(",", ":")).encode("utf-8")
    return _HEADER.pack(len(payload)) + payload


def decode_from_buffer(buf: bytearray):
    """
    Returns (event_dict, remaining_buffer) when a full message is in buf,
    or (None, buf) when more data is needed.
    """
    if len(buf) < HEADER_SIZE:
        return None, buf
    (length,) = _HEADER.unpack_from(buf, 0)
    total = HEADER_SIZE + length
    if len(buf) < total:
        return None, buf
    event = json.loads(buf[HEADER_SIZE:total].decode("utf-8"))
    return event, buf[total:]
