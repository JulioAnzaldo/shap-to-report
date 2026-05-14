"""
Utility to convert a Pydantic model into an OpenAI strict-mode JSON schema.

Lifted from Project 4 (schema.py) and adapted for shap-to-report.
Rules applied:
  - Every object gets additionalProperties: false
  - Every property is listed in required
  - default keys are stripped (OpenAI strict mode rejects them)
  - Optional fields use anyOf: [{type: X}, {type: null}] instead of default
"""
from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel


def to_strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """
    Convert a Pydantic model class to an OpenAI strict-mode JSON schema.

    Args:
        model: A Pydantic BaseModel subclass.

    Returns:
        A JSON schema dict with strict-mode patches applied, ready for use as:
            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "...", "schema": to_strict_schema(MyModel), "strict": True}
            }
    """
    schema = copy.deepcopy(model.model_json_schema())
    _patch(schema)
    return schema


def _patch(node: Any) -> None:
    """Recursively patch all nodes in the schema."""
    if not isinstance(node, dict):
        return

    # Patch object nodes
    if node.get("type") == "object" and "properties" in node:
        node["additionalProperties"] = False
        node["required"] = list(node["properties"].keys())
        for prop_schema in node["properties"].values():
            _patch(prop_schema)

    # Strip defaults (OpenAI strict mode rejects them)
    node.pop("default", None)

    # Recurse into anyOf / allOf / oneOf
    for key in ("anyOf", "allOf", "oneOf"):
        for sub in node.get(key, []):
            _patch(sub)

    # Recurse into array items
    if "items" in node:
        _patch(node["items"])

    # Recurse into $defs / definitions
    for defs_key in ("$defs", "definitions"):
        for sub in node.get(defs_key, {}).values():
            _patch(sub)
