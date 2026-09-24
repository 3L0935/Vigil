"""Small, strict boundary between model output and desktop actions."""

import json
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ToolResult:
    status: Literal["ok", "not_found", "needs_choice", "error"]
    data: dict
    retry_context: str | None = None


@dataclass(frozen=True)
class PendingChoice:
    action: Literal["launch", "close", "open_file"]
    candidates: tuple[str, ...]

    def __post_init__(self):
        if not 1 <= len(self.candidates) <= 10:
            raise ValueError("pending choices must be bounded")


def message_result(status: str, key: str, *, retry_context: str | None = None,
                   **params) -> ToolResult:
    return ToolResult(status, {"kind": "message", "key": key, "params": params},
                      retry_context)


class InvalidToolCall(ValueError):
    pass


def validate_call(call: dict, advertised: list[dict]) -> tuple[str, dict]:
    if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
        raise InvalidToolCall("missing function")
    function = call["function"]
    name = function.get("name")
    definitions = {item["function"]["name"]: item["function"]["parameters"]
                   for item in advertised}
    if name not in definitions:
        raise InvalidToolCall("unavailable tool")
    raw = function.get("arguments")
    if isinstance(raw, str):
        if len(raw.encode("utf-8")) > 4096:
            raise InvalidToolCall("oversized arguments")
        try:
            args = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise InvalidToolCall("invalid JSON") from exc
    else:
        args = raw
    if not isinstance(args, dict):
        raise InvalidToolCall("arguments must be an object")
    spec = definitions[name]
    properties = spec["properties"]
    if set(args) - set(properties) or set(spec.get("required", ())) - set(args):
        raise InvalidToolCall("unknown or missing field")
    for key, value in args.items():
        field = properties[key]
        kind = field["type"]
        if kind == "string":
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise InvalidToolCall("invalid string")
        elif kind == "integer":
            if type(value) is not int or not 1 <= value <= 10:
                raise InvalidToolCall("invalid result count")
        elif kind == "boolean":
            if type(value) is not bool:
                raise InvalidToolCall("invalid boolean")
        elif kind == "array":
            if (not isinstance(value, list) or not 2 <= len(value) <= 4
                    or any(not isinstance(v, str) or not v.strip() or len(v) > 128
                           for v in value)):
                raise InvalidToolCall("invalid options")
        else:
            raise InvalidToolCall("unsupported field type")
        if "enum" in field and value not in field["enum"]:
            raise InvalidToolCall("invalid option")
    return name, args
