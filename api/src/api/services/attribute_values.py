from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from api.models import AttributeDefinition, ProductAttributeValue

_COLUMNS = ("value_text", "value_number", "value_bool", "value_choices")


def value_columns(definition: AttributeDefinition, value: Any) -> dict[str, Any]:
    """Turn a Python value into the one value column that matches the attribute's type.

    Raises ValueError with a readable message when the value doesn't fit the definition.
    """
    key = definition.key
    kind = definition.data_type
    if kind == "multi_choice":
        if not isinstance(value, list) or not value:
            raise ValueError(f"'{key}' needs a non-empty list of options")
        bad = [v for v in value if v not in (definition.choices or [])]
        if bad:
            raise ValueError(f"'{key}': {bad} are not valid options")
        if len(set(value)) != len(value):
            raise ValueError(f"'{key}' lists an option more than once")
        return {"value_choices": list(value)}
    if kind == "single_choice":
        if not isinstance(value, str) or value not in (definition.choices or []):
            raise ValueError(f"'{key}': {value!r} is not a valid option")
        return {"value_text": value}
    if kind == "text":
        if not isinstance(value, str) or not 1 <= len(value) <= 200:
            raise ValueError(f"'{key}' needs text of 1 to 200 characters")
        return {"value_text": value}
    if kind == "number":
        if isinstance(value, bool):
            raise ValueError(f"'{key}' needs a number")
        try:
            return {"value_number": Decimal(str(value))}
        except InvalidOperation:
            raise ValueError(f"'{key}' needs a number")
    if kind == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"'{key}' needs true or false")
        return {"value_bool": value}
    raise ValueError(f"'{key}' has an unknown type {kind!r}")


def row_columns(row: ProductAttributeValue) -> dict[str, Any]:
    return {name: getattr(row, name) for name in _COLUMNS}


def display_value(columns: dict[str, Any]):
    """The value as the API shows it. Also used to compare old and new values."""
    if columns.get("value_choices") is not None:
        return list(columns["value_choices"])
    if columns.get("value_number") is not None:
        return format(columns["value_number"].normalize(), "f")
    if columns.get("value_bool") is not None:
        return columns["value_bool"]
    return columns.get("value_text")