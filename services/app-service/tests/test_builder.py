"""Tests for GXP schema validation and GrapesJS conversion."""
from __future__ import annotations

import pytest

from app.services.builder import (
    SchemaValidationError,
    VALID_COMPONENT_TYPES,
    gjs_to_gxp_components,
    validate_and_sanitize,
)


# ── validate_and_sanitize ─────────────────────────────────────────────────────

def _minimal_schema(**extra):
    return {
        "pages": [{"id": "p1", "route": "/", "components": [], "styles": {}}],
        **extra,
    }


def test_valid_schema_passes():
    schema = _minimal_schema()
    result = validate_and_sanitize(schema)
    assert result["pages"][0]["id"] == "p1"


def test_missing_pages_raises():
    with pytest.raises(SchemaValidationError, match="pages"):
        validate_and_sanitize({"datasources": []})


def test_forbidden_scripts_key_stripped():
    schema = {
        "pages": [{
            "id": "p1",
            "route": "/",
            "components": [{
                "type": "gxp-text",
                "id": "c1",
                "scripts": "alert(1)",
                "children": [],
            }],
            "styles": {},
        }],
    }
    result = validate_and_sanitize(schema)
    comp = result["pages"][0]["components"][0]
    assert "scripts" not in comp
    assert comp["type"] == "gxp-text"


def test_forbidden_eval_key_stripped():
    schema = {
        "pages": [{
            "id": "p1", "route": "/",
            "components": [{"type": "gxp-button", "id": "b1", "eval": "bad()", "children": []}],
            "styles": {},
        }],
    }
    result = validate_and_sanitize(schema)
    comp = result["pages"][0]["components"][0]
    assert "eval" not in comp


def test_unknown_component_type_stripped():
    schema = {
        "pages": [{
            "id": "p1", "route": "/",
            "components": [
                {"type": "gxp-text", "id": "ok", "children": []},
                {"type": "malicious-component", "id": "bad", "children": []},
            ],
            "styles": {},
        }],
    }
    result = validate_and_sanitize(schema)
    types = [c["type"] for c in result["pages"][0]["components"]]
    assert "malicious-component" not in types
    assert "gxp-text" in types


def test_invalid_datasource_binding_cleared():
    schema = {
        "datasources": [{"id": "ds-good"}],
        "pages": [{
            "id": "p1", "route": "/",
            "components": [{
                "type": "gxp-table",
                "id": "t1",
                "datasourceBinding": {"datasourceId": "ds-NONEXISTENT"},
                "children": [],
            }],
            "styles": {},
        }],
    }
    result = validate_and_sanitize(schema)
    comp = result["pages"][0]["components"][0]
    assert comp["datasourceBinding"] is None


def test_valid_datasource_binding_preserved():
    schema = {
        "datasources": [{"id": "ds-1"}],
        "pages": [{
            "id": "p1", "route": "/",
            "components": [{
                "type": "gxp-table",
                "id": "t1",
                "datasourceBinding": {"datasourceId": "ds-1"},
                "children": [],
            }],
            "styles": {},
        }],
    }
    result = validate_and_sanitize(schema)
    comp = result["pages"][0]["components"][0]
    assert comp["datasourceBinding"]["datasourceId"] == "ds-1"


def test_nested_forbidden_keys_stripped():
    schema = {
        "pages": [{
            "id": "p1", "route": "/",
            "components": [{
                "type": "gxp-container",
                "id": "c1",
                "children": [{
                    "type": "gxp-text",
                    "id": "inner",
                    "scripts": "evil()",
                    "children": [],
                }],
            }],
            "styles": {},
        }],
    }
    result = validate_and_sanitize(schema)
    inner = result["pages"][0]["components"][0]["children"][0]
    assert "scripts" not in inner
    assert inner["type"] == "gxp-text"


def test_all_valid_component_types_accepted():
    components = [
        {"type": t, "id": f"c-{i}", "children": []}
        for i, t in enumerate(VALID_COMPONENT_TYPES)
    ]
    schema = {"pages": [{"id": "p1", "route": "/", "components": components, "styles": {}}]}
    result = validate_and_sanitize(schema)
    result_types = {c["type"] for c in result["pages"][0]["components"]}
    assert result_types == VALID_COMPONENT_TYPES


# ── gjs_to_gxp_components ────────────────────────────────────────────────────

def test_gjs_gxp_type_maps_directly():
    gjs = [{"type": "gxp-text", "attributes": {"id": "t1", "content": "Hello"}, "components": []}]
    result = gjs_to_gxp_components(gjs)
    assert len(result) == 1
    assert result[0]["type"] == "gxp-text"
    assert result[0]["attributes"]["content"] == "Hello"
    assert "id" not in result[0]["attributes"]  # id moved to top-level id field


def test_gjs_non_gxp_with_children_becomes_container():
    gjs = [{
        "type": "div",
        "attributes": {},
        "components": [{"type": "gxp-text", "attributes": {}, "components": []}],
    }]
    result = gjs_to_gxp_components(gjs)
    assert result[0]["type"] == "gxp-container"
    assert result[0]["children"][0]["type"] == "gxp-text"


def test_gjs_non_gxp_without_children_dropped():
    gjs = [{"type": "span", "attributes": {}, "components": []}]
    result = gjs_to_gxp_components(gjs)
    assert result == []


def test_gjs_preserves_datasource_binding():
    gjs = [{
        "type": "gxp-table",
        "attributes": {},
        "datasourceBinding": {"datasourceId": "ds-1"},
        "components": [],
    }]
    result = gjs_to_gxp_components(gjs)
    assert result[0]["datasourceBinding"] == {"datasourceId": "ds-1"}


def test_gjs_empty_list():
    assert gjs_to_gxp_components([]) == []
