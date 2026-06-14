"""
GXP app schema validation.

Rules enforced before any save or publish:
1. No 'scripts' key anywhere in the component tree (prevents XSS / code injection)
2. All component type strings must be in the known closed set
3. datasourceBinding references must point to a declared datasource ID

The closed set of valid types matches what is registered in the runtime's
component-registry.ts.  Any type not in the set is stripped and logged.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

VALID_COMPONENT_TYPES = frozenset({
    "gxp-text", "gxp-button", "gxp-form", "gxp-table", "gxp-card",
    "gxp-tabs", "gxp-modal", "gxp-container", "gxp-image", "gxp-divider",
})

_FORBIDDEN_KEYS = frozenset({"scripts", "script", "eval", "innerHTML"})


class SchemaValidationError(Exception):
    pass


def validate_and_sanitize(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Validate a GXP AppSchema dict.  Returns a sanitized copy.
    Raises SchemaValidationError if the schema is structurally invalid.
    """
    if "pages" not in schema:
        raise SchemaValidationError("Schema must contain a 'pages' array")

    datasource_ids = {ds["id"] for ds in schema.get("datasources", []) if "id" in ds}

    sanitized_pages = []
    for page in schema["pages"]:
        sanitized_pages.append({
            **{k: v for k, v in page.items() if k != "components"},
            "components": _sanitize_nodes(page.get("components", []), datasource_ids),
        })

    return {**schema, "pages": sanitized_pages}


def _sanitize_nodes(nodes: list[dict], datasource_ids: set[str]) -> list[dict]:
    result = []
    for node in nodes:
        # Strip forbidden keys
        if _FORBIDDEN_KEYS.intersection(node.keys()):
            forbidden = _FORBIDDEN_KEYS.intersection(node.keys())
            logger.warning("Stripping forbidden keys from component %s: %s", node.get("id"), forbidden)
            node = {k: v for k, v in node.items() if k not in _FORBIDDEN_KEYS}

        ctype = node.get("type", "")
        if ctype not in VALID_COMPONENT_TYPES:
            logger.warning("Skipping unknown component type: %s", ctype)
            continue

        # Validate datasource binding
        binding = node.get("datasourceBinding")
        if binding and isinstance(binding, dict):
            ds_id = binding.get("datasourceId")
            if ds_id and ds_id not in datasource_ids:
                logger.warning("datasourceBinding references unknown datasource '%s', clearing", ds_id)
                node = {**node, "datasourceBinding": None}

        # Also strip forbidden keys from attributes
        attrs = node.get("attributes", {})
        if isinstance(attrs, dict):
            attrs = {k: v for k, v in attrs.items() if k not in _FORBIDDEN_KEYS}

        result.append({
            **node,
            "attributes": attrs,
            "children": _sanitize_nodes(node.get("children", []), datasource_ids),
        })
    return result


def gjs_to_gxp_components(gjs_components: list[dict]) -> list[dict]:
    """
    Convert GrapesJS component tree to GXP ComponentNode format.

    GrapesJS stores components with type + attributes + components (children).
    GXP uses type + attributes + children + datasourceBinding.

    This is a best-effort structural mapping; component-specific attribute
    translation is handled by the individual GXP component blocks defined
    in the portal's GrapesJS configuration.
    """
    result = []
    for comp in gjs_components:
        gxp_type = comp.get("type", "")
        # GrapesJS custom types registered as 'gxp-*' map directly
        if not gxp_type.startswith("gxp-"):
            # Default: wrap non-GXP elements as gxp-container if they have children
            if comp.get("components"):
                gxp_type = "gxp-container"
            else:
                continue

        result.append({
            "type": gxp_type,
            "id": comp.get("attributes", {}).get("id") or comp.get("ccid", ""),
            "attributes": {k: v for k, v in comp.get("attributes", {}).items() if k != "id"},
            "datasourceBinding": comp.get("datasourceBinding"),
            "children": gjs_to_gxp_components(comp.get("components", [])),
        })
    return result
