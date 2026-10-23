"""Offline MIBR/3 FRAME + snapshot contract. No socket, disk, QNX or writes.

A stable reference for native work and later J9 clients; not a live daemon,
authentication implementation, persistence or runtime activation proof.
"""
import re
from urllib.parse import unquote_to_bytes

VERSION = "MIBR/3"
REQUEST_MAX = 4096
RESPONSE_MAX = 16384
VALUE_MAX = 512
RID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z", re.ASCII)
FIELD = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z", re.ASCII)
ENCODED = re.compile(r"(?:[A-Za-z0-9_.~-]|%[0-9A-F]{2})+\Z", re.ASCII)
UNRESERVED = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.~-")
OPERATIONS = frozenset((
    "HELLO", "CAPABILITIES", "STATUS", "SNAPSHOT", "GET", "SET",
    "BATCH", "RESET", "TEST_SET", "TEST_CLEAR", "TEST_LIST",
    "ACTIVATE", "ACTION", "ACTION_STATUS", "REQUEST_STATUS",
    "ENGINE_GET", "ENGINE_SET", "VIEW_GET", "VIEW_SET",
))
ERRORS = frozenset((
    "INVALID_FRAME", "UNSUPPORTED_VERSION", "AUTH_REQUIRED", "FORBIDDEN",
    "INVALID_REQUEST", "INVALID_KEY", "INVALID_VALUE", "READ_ONLY",
    "DEPENDENCY_CONFLICT", "OVERRIDE_ACTIVE", "STALE_REVISION",
    "IDEMPOTENCY_COLLISION", "NOT_READY", "POLICY_BLOCKED",
    "SNAPSHOT_TOO_LARGE", "STORAGE_UNAVAILABLE", "DURABILITY_UNCONFIRMED",
    "RO_RESTORE_FAILED", "SESSION_STALE", "ACTIVATION_UNSUPPORTED",
    "ACTIVATION_FAILED", "TIMEOUT", "UNKNOWN_COMMIT", "ENGINE_FAILED", "VIEW_FAILED",
))


class FrameError(ValueError):
    pass


def encode_value(value):
    if not isinstance(value, str):
        raise FrameError("INVALID_VALUE")
    raw = value.encode("utf-8", errors="strict")
    if not raw or len(raw) > VALUE_MAX or any(c < 32 or c == 127 for c in raw):
        raise FrameError("INVALID_VALUE")
    return "".join(chr(c) if c in UNRESERVED else "%%%02X" % c for c in raw)


def decode_value(raw):
    if not isinstance(raw, str) or not ENCODED.fullmatch(raw):
        raise FrameError("INVALID_FRAME")
    try:
        value = unquote_to_bytes(raw).decode("utf-8", errors="strict")
    except (UnicodeError, ValueError):
        raise FrameError("INVALID_FRAME") from None
    if encode_value(value) != raw:
        raise FrameError("INVALID_FRAME")
    return value


def _fields_to_wire(fields):
    if fields is None:
        return ""
    if not isinstance(fields, dict):
        raise FrameError("INVALID_REQUEST")
    parts = []
    for k, v in fields.items():
        if not isinstance(k, str) or not FIELD.fullmatch(k):
            raise FrameError("INVALID_REQUEST")
        parts.append(k + "=" + encode_value(v))
    return ";".join(parts)


def _wire_to_fields(raw):
    if raw is None:
        return {}
    if not raw:
        raise FrameError("INVALID_FRAME")
    out = {}
    for part in raw.split(";"):
        if "=" not in part:
            raise FrameError("INVALID_FRAME")
        k, v = part.split("=", 1)
        if not FIELD.fullmatch(k) or k in out:
            raise FrameError("INVALID_FRAME")
        out[k] = decode_value(v)
    return out


def request(request_id, operation, fields=None):
    if not RID.fullmatch(str(request_id)) or operation not in OPERATIONS:
        raise FrameError("INVALID_REQUEST")
    args = _fields_to_wire(fields)
    frame = VERSION + " " + request_id + " " + operation + (" " + args if args else "") + "\n"
    if len(frame.encode("ascii")) > REQUEST_MAX:
        raise FrameError("INVALID_FRAME")
    return frame.encode("ascii")


def response(request_id, fields=None, error=None):
    if not RID.fullmatch(str(request_id)):
        raise FrameError("INVALID_REQUEST")
    if error is not None and error not in ERRORS:
        raise FrameError("INVALID_REQUEST")
    args = _fields_to_wire(fields)
    frame = (VERSION + " " + request_id + (" ERR " + error if error else " OK") +
             (" " + args if args else "") + "\n")
    if len(frame.encode("ascii")) > RESPONSE_MAX:
        raise FrameError("SNAPSHOT_TOO_LARGE")
    return frame.encode("ascii")


def parse(frame, *, is_response=False):
    if not isinstance(frame, bytes):
        raise FrameError("INVALID_FRAME")
    cap = RESPONSE_MAX if is_response else REQUEST_MAX
    if not frame.endswith(b"\n") or not frame or len(frame) > cap or b"\r" in frame or b"\x00" in frame:
        raise FrameError("INVALID_FRAME")
    try:
        line = frame[:-1].decode("ascii", errors="strict")
    except UnicodeError:
        raise FrameError("INVALID_FRAME") from None
    parts = line.split(" ")
    if len(parts) < 3 or any(not p for p in parts):
        raise FrameError("INVALID_FRAME")
    version, rid, kind = parts[:3]
    if version != VERSION:
        raise FrameError("UNSUPPORTED_VERSION")
    if not RID.fullmatch(rid):
        raise FrameError("INVALID_FRAME")
    if is_response:
        if kind not in ("OK", "ERR"):
            raise FrameError("INVALID_FRAME")
        if kind == "ERR":
            if len(parts) not in (4, 5) or parts[3] not in ERRORS:
                raise FrameError("INVALID_FRAME")
            code = parts[3]
            raw = parts[4] if len(parts) == 5 else None
        else:
            if len(parts) not in (3, 4):
                raise FrameError("INVALID_FRAME")
            code = None
            raw = parts[3] if len(parts) == 4 else None
    else:
        if kind not in OPERATIONS or len(parts) not in (3, 4):
            raise FrameError("INVALID_REQUEST")
        code = None
        raw = parts[3] if len(parts) == 4 else None
    return {"request_id": rid, "kind": kind, "error": code, "fields": _wire_to_fields(raw)}


def snapshot_fields(snapshot, registry, visible, *, scope="ui", role="ui"):
    """Project immutable *supplied observations*; NEVER infer actual values.

    HOST reference only. It does not read anything or assert a durable writer.
    """
    if scope not in ("ui", "all") or scope == "all" and role != "shell":
        raise FrameError("FORBIDDEN")
    rows = registry["settings"]
    if registry.get("schema") != 2 or len(rows) != 48 or len({r["key"] for r in rows}) != 48:
        raise FrameError("NOT_READY")
    keys = [r["key"] for r in rows]
    if (not isinstance(visible, (list, tuple)) or len(visible) != 11 or
            len(set(visible)) != 11 or not set(visible).issubset(keys)):
        raise FrameError("NOT_READY")
    if not snapshot or set(snapshot.values) != set(keys) or set(snapshot.sources) != set(keys):
        raise FrameError("NOT_READY")
    selected = list(visible) if scope == "ui" else keys
    index = {r["key"]: r for r in rows}
    result = {
        "row_count": str(len(selected)),
        "revision": str(snapshot.revision),
        "stored": "VERIFIED" if snapshot.persisted_verified else "UNCONFIRMED",
        "durable_generation": "UNKNOWN",
        "runtime_correlated": "1" if snapshot.runtime_correlated else "0",
        "connected": ("UNKNOWN" if not snapshot.runtime_correlated else
                      ("1" if snapshot.connected else "0")),
        "session": str(snapshot.session_id) if snapshot.connected else "NONE",
        "session_generation": str(snapshot.generation) if snapshot.connected else "UNKNOWN",
        "pending": "UNKNOWN",
        "phase": "HOST_ONLY_NO_IO",
    }
    for i, key in enumerate(selected):
        prefix = "row.%d." % i
        result[prefix + "key"] = key
        result[prefix + "value"] = str(snapshot.values[key])
        result[prefix + "source"] = str(snapshot.sources[key])
        result[prefix + "apply"] = index[key]["apply"]
        result[prefix + "active"] = (str(snapshot.active[key]) if snapshot.active_verified
                                      and key in snapshot.active else "UNKNOWN")
        result[prefix + "advertised"] = (str(snapshot.advertised[key]) if snapshot.connected
                                          and key in snapshot.advertised else "UNKNOWN")
    return result


def read_only_host(request_frame, snapshot, registry, visible, *, role="ui"):
    """No native action is dispatched; all mutations fail closed."""
    req = parse(request_frame)
    rid, op, args = req["request_id"], req["kind"], req["fields"]
    if op == "HELLO":
        return response(rid, {"version": VERSION, "phase": "HOST_ONLY_NO_IO",
                              "registry_keys": "48", "durable_set": "0",
                              "activation": "0", "test_override": "0"})
    if op == "CAPABILITIES":
        return response(rid, {"snapshot": "1", "durable_set": "0",
                              "presentation_refresh": "0", "reconnect": "0",
                              "test_override": "0", "phase": "HOST_ONLY_NO_IO"})
    if op == "STATUS":
        return response(rid, {"ready": "HOST_MODEL_ONLY", "stored": "UNCONFIRMED",
                              "activation": "UNSUPPORTED", "phase": "HOST_ONLY_NO_IO"})
    if op == "SNAPSHOT":
        if set(args) - {"scope"}:
            return response(rid, error="INVALID_REQUEST")
        try:
            result = snapshot_fields(snapshot, registry, visible,
                                     scope=args.get("scope", "ui"), role=role)
            return response(rid, result)
        except FrameError as exc:
            return response(rid, error=str(exc))
    return response(rid, error="POLICY_BLOCKED")
