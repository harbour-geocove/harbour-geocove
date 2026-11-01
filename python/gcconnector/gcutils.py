"""Port of GCUtils.java: GC code <-> numeric id conversions."""
from typing import Optional

_SEQ = "0123456789ABCDEFGHJKMNPQRTVWXYZ"
_BASE31 = 31
_BASE16 = 16


def _index(c: str) -> int:
    return _SEQ.find(c)  # -1 for invalid characters


def _code_to_id(prefix: str, code: Optional[str], ignore_wrong: bool = False) -> int:
    if not code or not code.strip() or len(code) < len(prefix) + 1 or not code.startswith(prefix):
        return 0
    base = _BASE31
    body = code[len(prefix):].upper()
    if len(body) < 4 or (len(body) == 4 and _index(body[0]) < 16):
        base = _BASE16
    gcid = 0
    for ch in body:
        idx = _index(ch)
        if idx < 0 and not ignore_wrong:
            return 0  # invalid character in code
        gcid = base * gcid + idx
    if base == _BASE31:
        gcid += 16 ** 4 - 16 * 31 ** 3
    return gcid


def _id_to_code(prefix: str, id_: int) -> str:
    id_ = max(id_, 0)
    low = id_ <= 65535
    base = _BASE16 if low else _BASE31
    div = id_ if low else id_ + 411120
    code = ""
    while div != 0:
        code = _SEQ[div % base] + code
        div //= base
    return prefix + code if code.strip() else ""


def gc_code_to_gc_id(gccode: Optional[str]) -> int:
    """GC code -> (old) numeric id; 0 for invalid codes."""
    return _code_to_id("GC", gccode)


def gc_like_code_to_gc_like_id(code: Optional[str]) -> int:
    """Like gc_code_to_gc_id but for any two-letter prefix, ignoring bad characters."""
    if not code or len(code) < 2:
        return 0
    return _code_to_id(code[:2], code, True)


def gc_id_to_gc_code(gc_id: int) -> str:
    return _id_to_code("GC", gc_id)


def log_code_to_log_id(log_code: Optional[str]) -> int:
    return _code_to_id("GL", log_code)


def log_id_to_log_code(log_id: int) -> str:
    return _id_to_code("GL", log_id)
