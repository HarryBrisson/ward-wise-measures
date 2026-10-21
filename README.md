# ward-wise-measures

The contract, validator and registry for **bring-your-own-polygons (byop/v1) measures** — the way an
independent GitHub repo publishes a Chicago (or any-city) measure that
[Penlight](https://www.wardwise.org) can roll up to wards, neighborhoods and χGRID cells.

A measure repo computes something fine-grained (points, a raster, or values on census polygons),
publishes a `layers/` folder with an `aggregation_spec.json`, and attaches it to a **GitHub Release**.
Penlight's pipeline reads only those published files — never the repo's code — and aggregates them
to its geographies. This repo is the glue:

| Piece | What it is |
|---|---|
| [`CONTRACT.md`](CONTRACT.md) | The byop/v1 spec: layer kinds, combine rules, and the catalog fields a metric carries |
| [`schema/aggregation_spec.schema.json`](schema/aggregation_spec.schema.json) | The same contract as a JSON Schema |
| `byop validate <layers_dir>` | Checks a spec and its files the way the pipeline will read them (`pip install git+https://github.com/HarryBrisson/ward-wise-measures`) |
| [`measures.json`](measures.json) | **The registry**: every admitted source, pinned to a release tag and the sha256 of each asset |
| [`.github/workflows/publish-measure.yml`](.github/workflows/publish-measure.yml) | A reusable workflow a measure repo calls on tag to validate and publish its release |
| [`ADDING_A_MEASURE.md`](ADDING_A_MEASURE.md) | The walkthrough, start to finish |

## How admission works

Anyone can publish a conforming release from their own repo; nobody needs access to Penlight's
infrastructure. A measure enters Penlight when a pull request adds (or bumps) its entry in
`measures.json` and a maintainer merges it. The pin — tag plus sha256 per asset — is the trust
boundary: the pipeline downloads exactly those bytes and nothing else, so a later change to the
source repo changes nothing in Penlight until someone opens a new PR here.

## Existing measures

| Source | Repo | Layers | Metrics |
|---|---|---|---|
| sunscore | [HarryBrisson/sunscore](https://github.com/HarryBrisson/sunscore) | 3 rasters (18 m, street-level sun access) | annual / summer / winter sun access |
| zonewise | [HarryBrisson/zonewise](https://github.com/HarryBrisson/zonewise) | passed rezonings 2011+ (dated points; byop v1.1 `time_field`) + current zoning map (6 rasters, `as_of`) | yearly rezonings per km², upzoning share, to-multifamily share, zoned capacity added; % single-family / multifamily / business / manufacturing / PD zoning, zoned FAR |
| parkability | [HarryBrisson/parkability](https://github.com/HarryBrisson/parkability) | parking sites, 311 complaints, car ownership (points) | 3 per-km² / per-household rates |
| rentrate | [HarryBrisson/rentrate](https://github.com/HarryBrisson/rentrate) | residential parcels, rental profit parcels (points) | absentee-owner share, landlord-profit shares |
| microhappiness | [HarryBrisson/microhappiness](https://github.com/HarryBrisson/microhappiness) | nationwide tract + ZCTA tables (polygon_values) | 16 modeled wellbeing / time-use / religion estimates |

parkability, rentrate and microhappiness predate the registry and are listed with `pending_release: true` until each publishes
its first tagged release; Penlight still reads them from local checkouts in the meantime.

MIT © Harry Brisson.
