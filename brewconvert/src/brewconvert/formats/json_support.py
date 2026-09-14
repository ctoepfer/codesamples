"""JSON serialization with exact Decimal number tokens and UTF-8 text."""

import json
from decimal import Decimal


def dumps(value, level=0):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite JSON number")
        return str(value)
    if isinstance(value, dict):
        if not value:
            return "{}"
        entries = [
            json.dumps(k, ensure_ascii=False) + ": " + dumps(v, level + 1)
            for k, v in value.items()
        ]
        opening, closing = "{", "}"
    elif isinstance(value, list):
        if not value:
            return "[]"
        entries = [dumps(v, level + 1) for v in value]
        opening, closing = "[", "]"
    else:
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    indent = "  " * (level + 1)
    return (
        opening
        + "\n"
        + indent
        + (",\n" + indent).join(entries)
        + "\n"
        + "  " * level
        + closing
    )
