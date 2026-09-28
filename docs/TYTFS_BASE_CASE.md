# TYTFS 2024 summer planning case: base DC check

This importer uses `TYTFS2024_SV2024_V33.raw` from [EirGrid's 2024 TYTFS study archive](https://cms.eirgrid.ie/sites/default/files/publications/TYTFS2024_studyfiles.zip). Its header identifies PSS/E RAW **version 33**, 100 MVA base, `CASE: 2024; SUMMER 01/07/2024`. The archive was published for planning reference. Its disclaimer says the modelled demand, generation and power flow are **not real-time operating conditions**. These exports are a TYTFS 2024 planning scenario, not a 2026 operational network.

## Reproduce

From a fresh checkout with the README's Python 3.11 environment, download the public archive and run:

```bash
mkdir -p data/raw/network_feasibility
curl -fL 'https://cms.eirgrid.ie/sites/default/files/publications/TYTFS2024_studyfiles.zip' \
  -o data/raw/network_feasibility/TYTFS2024_studyfiles.zip
python -m scripts.import_tytfs_case \
  --zip data/raw/network_feasibility/TYTFS2024_studyfiles.zip \
  --output-dir data/raw/network_case
```

The command writes `buses.csv`, `branches.csv`, `transformers.csv`, `generators.csv`, `loads.csv`, `provenance.json`, and `validation_report.json` under the chosen output directory. `data/raw/` is ignored by Git. The provenance file records the source member and SHA-256 of the extracted RAW bytes, so a refreshed download can be compared with this check. The checked case SHA-256 is `b73cf0ca51cea4ab8f58cfc4e9e1021f561c877e4880ed979213747b8d667450`. The external ECP line ratings workbook is not merged.

`load_case(output_dir)` in `backend.app.network` reads the CSVs. `solve_dc_case(case, disabled_branches=(), disabled_transformers=(), injection_overrides_mw=None)` returns status, branch and transformer MW flows, source-bus angles, injection residual, islands and diagnostics. Source branch IDs are `from_bus:to_bus:circuit_id`; transformer IDs use that format for two-winding devices and `from_bus:to_bus:third_bus:circuit_id` for three-winding devices. Three-winding result flows append `/w1`, `/w2`, or `/w3`; disabling the parent transformer ID removes all windings. Injection overrides replace net generation minus load at a bus in MW.

## Observed base state

| Check | Result |
| --- | ---: |
| RAW buses / active buses | 1,979 / 1,977 |
| RAW branches / active branches | 1,120 / 1,072 |
| RAW transformers | 1,272: 1,168 two-winding and 104 three-winding; all active |
| RAW generators / active generators | 558 / 18 |
| RAW loads / active loads | 264 / 231 |
| Active source generation / constant-power load | 3,424.416 / 3,402.300 MW |
| Source net injection / DC slack adjustment | +22.116 / -22.116 MW |
| Connected components | One 1,976-bus grid and one isolated zero-injection bus 86221 |
| Main-grid slack | Bus 52071, selected from the RAW type-3 buses |
| DC flow records / with usable rate A | 2,552 / 1,041 |
| Largest absolute DC flow | 456 MW |
| Largest MW/MVA rate A proxy | 84.92%; none over 100% in this base solve |
| Maximum nodal balance residual after slack | Below 3e-10 MW |

The feasibility inventory and issue #9 mentioned **1,298 transformers**. Reading this specific V33 summer file by PSS/E record lengths gives 5,192 transformer-section lines: `1,168 × 4 + 104 × 5 = 5,192`, or **1,272 transformer records**. The 1,298 figure is not reproduced for this selected case; it may refer to another scenario or an earlier rough count. This discrepancy should not be interpreted as 26 missing imported devices.

## Interpretation and limits

The DC solve is internally balanced after assigning the 22.116 MW residual to the chosen slack. It is **not** a reproduction of the original AC solution. The RAW file carries solved bus voltages and angles, but no authoritative solved branch MW-flow table to compare directly. The DC approximation omits resistance and losses, reactive power, voltage limits, shunts, converter transfers, load current/admittance terms and transformer controls. It uses fixed PSS/E active-power injections and source in-service flags.

Three-winding transformers are reduced to a star equivalent. Twenty calculated star-leg reactances are negative, which is possible even when their pairwise values are positive; they are retained in the linear solve. Zero legs, if encountered, are approximated by `1e-8` pu. This is sufficient for a bounded scenario prototype, not an AC-grade transformer model.

The source's rate A/B/C fields are MVA. The solver reports `abs(DC MW) / rate A MVA` only as a screening proxy, not thermal loading. Zero and values at or above 9,000 MVA are treated as absent or placeholders. In this case, 178 branches and 1,133 transformers have such rate A values; three-winding winding 2/3 ratings are not applied. Published ECP ratings need a verified asset crosswalk before use. An outage that splits an active, loaded island returns `status="islanded"` and identifies islands without online generation; those islands require a dispatch response outside this solver.
