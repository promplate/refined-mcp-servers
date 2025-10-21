type JSON = dict[str, JSON] | list[JSON] | tuple[JSON, ...] | str | int | float | bool | None


def readable_yaml_dumps(data: JSON):
    """
    Minimal YAML serializer optimized for readability.

    Uses literal block style (|) for all multi-line strings.
    Single-line strings are output without quotes when possible.

    Note: Generated output is for display only, not meant to be parsed.
    """
    lines: list[str] = []
    _serialize(data, lines, indent=0)
    return "".join(lines)


def _serialize(data: JSON, lines: list[str], indent: int):
    """Recursively serialize data into YAML format."""
    prefix = "  " * indent

    if isinstance(data, dict):
        _serialize_dict(data, lines, indent, prefix)
    elif isinstance(data, (list, tuple)):
        _serialize_list(data, lines, indent, prefix)
    elif isinstance(data, str):
        _serialize_string(data, lines, prefix)
    else:
        lines.append(f"{prefix}{_serialize_scalar(data)}\n")


def _serialize_dict(data: dict, lines: list[str], indent: int, prefix: str):
    """Serialize dictionary with key: value pairs."""
    if not data:
        lines.append(f"{prefix}{{}}\n")
        return

    for key, value in data.items():
        key_str = _serialize_scalar(key)

        if isinstance(value, (dict, list, tuple)):
            lines.append(f"{prefix}{key_str}:\n")
            _serialize(value, lines, indent + 1)
        elif isinstance(value, str) and "\n" in value:
            lines.append(f"{prefix}{key_str}:")
            _append_literal_block(value, lines, indent + 1)
        else:
            lines.append(f"{prefix}{key_str}: {_serialize_scalar(value)}\n")


def _serialize_list(data: list | tuple, lines: list[str], indent: int, prefix: str):
    """Serialize list/tuple with dash-style items."""
    if not data:
        lines.append(f"{prefix}[]\n")
        return

    for item in data:
        if isinstance(item, dict):
            if not item:
                lines.append(f"{prefix}- {{}}\n")
            else:
                _serialize_dict_in_list(item, lines, indent, prefix)
        elif isinstance(item, (list, tuple)):
            if not item:
                lines.append(f"{prefix}- []\n")
            else:
                lines.append(f"{prefix}-\n")
                _serialize(item, lines, indent + 1)
        elif isinstance(item, str) and "\n" in item:
            lines.append(f"{prefix}-")
            _append_literal_block(item, lines, indent + 1)
        else:
            lines.append(f"{prefix}- {_serialize_scalar(item)}\n")


def _serialize_dict_in_list(data: dict, lines: list[str], indent: int, prefix: str):
    """Serialize a non-empty dict as a list item, with first key inline."""
    lines.append(f"{prefix}-")
    item_prefix = "  " * (indent + 1)

    for i, (key, value) in enumerate(data.items()):
        key_str = _serialize_scalar(key)
        line_prefix = " " if i == 0 else item_prefix

        if isinstance(value, (dict, list, tuple)):
            # For empty collections, inline them
            if not value:
                inline_repr = "{}" if isinstance(value, dict) else "[]"
                lines.append(f"{line_prefix}{key_str}: {inline_repr}\n")
            else:
                lines.append(f"{line_prefix}{key_str}:\n")
                _serialize(value, lines, indent + 2)
        elif isinstance(value, str) and "\n" in value:
            lines.append(f"{line_prefix}{key_str}:")
            _append_literal_block(value, lines, indent + 2)
        else:
            lines.append(f"{line_prefix}{key_str}: {_serialize_scalar(value)}\n")


def _serialize_string(value: str, lines: list[str], prefix: str):
    """Serialize a string value (standalone, not as dict/list value)."""
    if "\n" in value:
        lines.append(f"{prefix}")
        _append_literal_block(value, lines, indent=1)
    else:
        lines.append(f"{prefix}{_serialize_scalar(value)}\n")


def _append_literal_block(value: str, lines: list[str], indent: int):
    """
    Append a multi-line string in literal block style (|).

    Chomping indicator selection:
    - |- (strip): If no trailing newline
    - | (clip): If has single trailing newline (default)
    - |+ (keep): If has multiple trailing newlines
    """
    block_prefix = "  " * indent

    # Determine chomping indicator
    trailing_newlines = len(value) - len(value.rstrip("\n"))
    if trailing_newlines == 0:
        # No trailing newlines: use strip
        lines.append(" |-\n")
        stripped_value = value
    elif trailing_newlines == 1:
        # Single trailing newline: use clip (default)
        lines.append(" |\n")
        stripped_value = value.rstrip("\n")
    else:
        # Multiple trailing newlines: use keep
        lines.append(" |+\n")
        stripped_value = value

    # Output content lines
    lines.extend(f"{block_prefix}{line}\n" for line in stripped_value.split("\n"))


def _serialize_scalar(value: str | int | float | bool | None):
    """Convert scalar values to YAML string representation."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        # Single-line string: quote if contains special chars or quotes
        if any(c in value for c in ":[{}],&*#?|-<>!`@\n'\""):
            # Prefer single quotes (simpler escaping rules in YAML)
            # but must escape single quotes as ''
            if "'" in value:
                escaped = value.replace("'", "''")
                return f"'{escaped}'"
            return f"'{value}'"
        return value
    else:
        return str(value)


__all__ = "JSON", "readable_yaml_dumps"
