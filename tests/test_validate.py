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


def test_publish_dry_run_names_only_the_spec_files_and_pins_them(tmp_path):
    from byop.publish import publish, registry_entry
    (tmp_path / "aggregation_spec.json").write_text(json.dumps(_spec()))
    (tmp_path / "pts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-87.6, 41.9]}, "properties": {"ok": True}}]}))
    (tmp_path / "scratch.csv").write_text("not published")
    files = publish(tmp_path, repo="a/b", tag="v1", dry_run=True)
    assert [f.name for f in files] == ["aggregation_spec.json", "pts.geojson"]
    entry = registry_entry(tmp_path, name="demo", repo="a/b", tag="v1", targets=["community_area"])
    assert set(entry["assets"]) == {"aggregation_spec.json", "pts.geojson"}
    assert reg.validate_registry({"contract": "byop/v1", "measures": [entry]}) == []


def _timed_spec(**metric_over):
    spec = _spec()
    spec["layers"]["pts"]["as_of"] = "2026-10-19"
    metric = {"layer": "pts", "combine": "sum", "value": "sqft", "per": "area_km2", "time_field": "passed",
              "years": [2012, 2026], "unit": "count", "direction": "higher", "label": "Capacity",
              "description": "A demo.", "methodology": "Summed."}
    metric.update(metric_over)
    spec["metrics"]["demo_capacity"] = metric
    return spec


def _write_points(tmp_path: Path, spec, props_list):
    (tmp_path / "aggregation_spec.json").write_text(json.dumps(spec))
    (tmp_path / "pts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-87.6, 41.9]}, "properties": p}
        for p in props_list]}))


def test_time_value_year_parses_years_and_dates():
    from byop import time_value_year
    assert time_value_year(2019) == 2019
    assert time_value_year("2019") == 2019
    assert time_value_year("2019-06-12") == 2019
    assert time_value_year("2019-06-12T00:00:00.000") == 2019
    assert time_value_year(None) is None
    assert time_value_year("June 2019") is None
    assert time_value_year(True) is None


def test_timed_sum_spec_is_valid():
    assert validate_spec(_timed_spec()) == []


def test_sum_needs_value_and_points():
    spec = _timed_spec()
    spec["metrics"]["demo_capacity"].pop("value")
    assert any("needs 'value'" in p for p in validate_spec(spec))


def test_time_field_and_years_rules():
    spec = _timed_spec(years=[2026, 2012])
    assert any("start <= end" in p for p in validate_spec(spec))
    spec = _timed_spec()
    del spec["metrics"]["demo_capacity"]["time_field"]
    assert any("years needs a time_field" in p for p in validate_spec(spec))
    spec = _spec(layers={"pts": {"file": "pts.geojson", "kind": "points"}, "sun": {"file": "s.tif", "kind": "raster"}})
    spec["metrics"]["sun_mean"] = {"layer": "sun", "combine": "mean", "time_field": "year", "unit": "percent",
                                   "direction": "higher", "label": "Sun", "description": "x", "methodology": "x"}
    assert any("points layers only" in p for p in validate_spec(spec))


def test_as_of_must_be_iso_date():
    spec = _timed_spec()
    spec["layers"]["pts"]["as_of"] = "Oct 2026"
    assert any("as_of" in p for p in validate_spec(spec))


def test_time_field_values_are_checked_in_files(tmp_path: Path):
    _write_points(tmp_path, _timed_spec(), [{"ok": True, "sqft": 10}])
    with pytest.raises(ValidationError) as excinfo:
        validate_layers_dir(tmp_path)
    assert any("time_field 'passed' is not a property" in p for p in excinfo.value.problems)

    _write_points(tmp_path, _timed_spec(), [{"ok": True, "sqft": 10, "passed": "last spring"}])
    with pytest.raises(ValidationError) as excinfo:
        validate_layers_dir(tmp_path)
    assert any("not a year or ISO date" in p for p in excinfo.value.problems)

    _write_points(tmp_path, _timed_spec(), [{"ok": True, "sqft": 10, "passed": None}])
    with pytest.raises(ValidationError) as excinfo:
        validate_layers_dir(tmp_path)
    assert any("empty on every sampled point" in p for p in excinfo.value.problems)

    _write_points(tmp_path, _timed_spec(), [{"ok": True, "sqft": 10, "passed": "2019-06-12"},
                                            {"ok": False, "sqft": -4, "passed": None}])
    assert validate_layers_dir(tmp_path)["layers"]["pts"]["features"] == 2
