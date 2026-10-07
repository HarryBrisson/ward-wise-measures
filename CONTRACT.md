# The byop/v1 contract

A measure source publishes a folder (the *layers dir*) containing `aggregation_spec.json` and the
files it names. A consumer reads only that folder and aggregates each metric to whatever target
polygons it holds. Nothing about the consumer's geography is baked into the source: the same
release serves Chicago wards, community areas, a square-mile grid, or another city's districts.

## aggregation_spec.json

```json
{
  "contract": "byop/v1",
  "source": "sunscore",
  "source_url": "https://github.com/HarryBrisson/sunscore",
  "layers": {
    "sun_annual": {"file": "sun_access_annual.tif", "kind": "raster",
                   "value": "per-cell direct-sun fraction, NaN off the ground mask"}
  },
  "metrics": {
    "annual_sun_access_pct": {
      "layer": "sun_annual", "combine": "mean", "scale": 100,
      "unit": "percent", "direction": "higher",
      "label": "Sun Access",
      "description": "Share of daylight that ground-level spots receive direct sun, averaged over the year.",
      "methodology": "Simulate the sun across the day and seasons over a 2022 LiDAR surface model …",
      "category": "physical_environment",
      "default_weight": 0.5,
      "nominator": {"name": "Jackie Schmitz", "ward_id": "43"}
    }
  },
  "fixed_geography_metrics": {
    "permit_zone_block_faces_per_sqkm": "ward-tagged address ranges with no point geometry"
  }
}
```

### Top level

| Field | Required | Meaning |
|---|---|---|
| `contract` | yes | exactly `"byop/v1"` |
| `source` | yes | short slug, `[a-z0-9_-]+`; the registry key |
| `source_url` | recommended | the repo |
| `layers` | yes | the fine data files, by name |
| `metrics` | yes | what to compute from them, by `metric_id` |
| `fixed_geography_metrics` | no | metrics the source can only report on its own geography, with a one-line reason; consumers may estimate them |
| `synthetic_estimate`, `caveat` | no | set `synthetic_estimate: true` and explain when values are modeled rather than measured (consumers label them and lower their confidence) |

Any other top-level keys are kept as provenance and ignored by consumers.

### Layers

| `kind` | File | Geometry | Used by |
|---|---|---|---|
| `points` | GeoJSON FeatureCollection of Point features with `properties` | its own | `count`, `ratio`, `share` |
| `raster` | GeoTIFF, any projected CRS, NaN = no data | its own | `mean` |
| `polygon_values` | CSV with an `id_field` column naming a standard census polygon (tract GEOID, ZCTA) and one column per value/weight | the consumer supplies standard census geometries | `weighted_mean` |

Each layer: `file` (relative to the spec), `kind`, optional `value` (a human sentence describing one
cell/point/row), and for `polygon_values` the `id_field`.

### Metrics

| Field | Required | Meaning |
|---|---|---|
| `layer` | yes | a layer name, or a list of names when the same metric is published at several geographies (`["tract", "zcta"]`) |
| `combine` | yes | one of the rules below |
| `unit` | yes | `percent`, `count`, `rate`, `currency`, `index_0_100`, `minutes`, `miles`, … (Penlight's units; free text is accepted but won't format) |
| `direction` | yes | `higher` or `lower` = which way is better for a resident (`higher_better` / `lower_better` accepted) |
| `label` | yes | 1–3 words, the chip on the map |
| `description` | yes | one sentence a resident understands |
| `methodology` | yes | how it was computed, 1–3 sentences, with the data source |
| `category` | recommended | a Penlight domain: `physical_environment`, `community_vitality`, `material_wellbeing`, `health`, `good_governance`, `education`, `safety`, `time_balance`, `psychological_wellbeing`, `culture`; unknown categories land in `other` |
| `default_weight` | no | 0–1; weight in the default index (0 = available but not weighted in) |
| `nominator` | no | `{"name": ..., "ward_id": "43"}` — the resident who proposed the measure, credited on the map |
| `scale`, `per`, `flag`, `numerator`, `denominator`, `value`, `weight`, `ci` | per rule | see below |

### Combine rules

| `combine` | Layer kind | Result for a target polygon |
|---|---|---|
| `count` | points | number of points inside ÷ `per` (`"area_km2"`, or omit for a raw count) |
| `ratio` | points | Σ `numerator` ÷ Σ `denominator` over points inside, × `scale` (default 1) |
| `share` | points | fraction of points inside whose `flag` property is truthy, × `scale` (default 100) |
| `mean` | raster | area-weighted mean of the cells inside, NaN ignored, × `scale` (default 1) |
| `weighted_mean` | polygon_values | Σ(`weight` · overlap · `value`) ÷ Σ(`weight` · overlap) over source polygons overlapping the target |

A target with nothing inside gets no value (not zero).

## Publishing

Attach the layers dir's files, flat, to a GitHub Release of the source repo, tagged
`vYYYY.MM.DD` or semver. `aggregation_spec.json` must be one of the assets. The reusable workflow in
this repo does it: see `ADDING_A_MEASURE.md`. Size limits: 2 GB per asset (GitHub's), and a consumer
may cap what it downloads (Penlight: 500 MB per asset). Big point layers can publish a documented
sample (rentrate publishes a parcel-digit sample of its 1.6 M parcels).

## Versioning

`byop/v1` is frozen: new optional fields may be added, nothing required changes. A breaking change
becomes `byop/v2` and consumers announce support before sources need it.
