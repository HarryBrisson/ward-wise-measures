import json
from pathlib import Path

import pytest

from byop import ValidationError, validate_layers_dir, validate_spec
from byop import registry as reg


def _spec(**over):
    spec = {
        "contract": "byop/v1", "source": "demo",
        "layers": {"pts": {"file": "pts.geojson", "kind": "points"}},
        "metrics": {"demo_share_pct": {"layer": "pts", "combine": "share", "flag": "ok", "scale": 100, "unit": "percent",
                                        "direction": "higher", "label": "Demo", "description": "A demo.", "methodology": "Counted."}},
    }
    spec.update(over)
    return spec


def test_good_spec_has_no_problems():
    assert validate_spec(_spec()) == []


def test_rule_fields_and_layer_kinds_are_checked():
    spec = _spec()
    spec["metrics"]["demo_share_pct"].pop("flag")
    spec["metrics"]["bad_mean"] = {"layer": "pts", "combine": "mean", "unit": "percent", "direction": "higher",
                                   "label": "x", "description": "x", "methodology": "x"}
    problems = validate_spec(spec)
    assert any("needs 'flag'" in p for p in problems)
    assert any("needs a raster layer" in p for p in problems)


def test_catalog_fields_required_unless_lenient():
    spec = _spec()
    del spec["metrics"]["demo_share_pct"]["methodology"]
    assert any("methodology" in p for p in validate_spec(spec))
    assert validate_spec(spec, strict_catalog=False) == []


def test_files_and_properties_are_checked(tmp_path: Path):
    (tmp_path / "aggregation_spec.json").write_text(json.dumps(_spec()))
    (tmp_path / "pts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-87.6, 41.9]}, "properties": {"nope": 1}}]}))
    with pytest.raises(ValidationError) as excinfo:
        validate_layers_dir(tmp_path)
    assert any("flag 'ok' is not a property" in p for p in excinfo.value.problems)
    (tmp_path / "pts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-87.6, 41.9]}, "properties": {"ok": True}}]}))
    report = validate_layers_dir(tmp_path)
    assert report["layers"]["pts"]["features"] == 1


def test_registry_file_is_valid():
    assert reg.validate_registry(reg.load_registry()) == []


def test_registry_requires_pins_once_released():
    registry = {"contract": "byop/v1", "measures": [{"name": "x", "repo": "a/b", "tag": "v1", "targets": ["ward"],
                                                     "assets": {"aggregation_spec.json": "sha256:zz"}}]}
    problems = reg.validate_registry(registry)
    assert any("digest" in p for p in problems)
