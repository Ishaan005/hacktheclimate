# ECP generator-to-bus review and illustrative injection allocation

This workflow joins the [ECP GSS 2 connection-study workbook](https://cms.eirgrid.ie/sites/default/files/publications/ECP-GSS-2-Constraint-Analysis-Excel-Report.xlsx) to **TYTFS2024_SV2024_V33** buses. Both are planning inputs. A normalized station-name match is a candidate, not proof of the electrical connection or present-day output. Keep the workbook, TYTFS archive, derived crosswalk, and scenario CSVs under ignored `data/raw/`; check EirGrid redistribution terms before publishing derived project records. See the [network feasibility study](NETWORK_DATA_FEASIBILITY_2026-09-28.md).

## Crosswalk

The script accepts a bus export with at least `bus_id,name,base_kv`; optional `in_service` is enforced when reviewing a bus. The TYTFS importer for issue #9 exports this schema as `data/raw/network_case/buses.csv`. The reviewed file [`config/network_review_f_ballylickey.csv`](../config/network_review_f_ballylickey.csv) is pinned to the ECP workbook SHA-256 and checks selected bus name and voltage. Its `accepted_proxy` status means an **upstream station proxy** suitable for a planning scenario, not a verified farm terminal. A bus with several voltage levels, duplicate bus IDs at one station, or a spelling variant remains ambiguous until someone checks the network case and connection evidence. Manual overrides of non-name matches require an explicit reason.

```bash
python scripts/network_generators.py crosswalk \
  --workbook data/raw/network_feasibility/ECP-GSS-2-Constraint-Analysis-Excel-Report.xlsx \
  --buses data/raw/network_case/buses.csv \
  --reviews config/network_review_f_ballylickey.csv \
  --output data/raw/network_case/generator_crosswalk.csv \
  --report data/raw/network_case/generator_crosswalk_report.json
```

On the inspected files, all **822** project rows parse. The **377 connected** rows total **7,504.287 MW MEC**: six reviewed station proxies at **53.95 MW**, 348 ambiguous at **6,650.217 MW**, and 23 unmatched at **800.12 MW**. The **445 `due to connected`** rows total **25,747.859 MW MEC** and remain outside current injections. The report also separates TSO/DSO and wind/solar/battery/offshore wind. Offshore wind appears only among the future rows in this workbook. These totals describe *maximum export capacity*, not forecast or actual production.

### Manual area F check

I checked area F's **21 connected source rows** against the workbook and the 2024 summer V33 bus table. Six DSO wind rows, workbook rows **476, 570, 571, 572, 752, and 790**, name Ballylickey as their node. The network case has one normalized Ballylickey bus: **1281, 110 kV**. Their MEC sum is **53.95 MW**. The review file accepts that bus only as the common station-level proxy. The other **15 rows, 170.71 MW MEC**, remain ambiguous, mostly because names such as Bandon, Macroom, and Dunmanway have several voltage or same-name bus candidates. The workbook does not give a terminal or circuit ID, and a DSO project may connect downstream of the 110 kV station. This check therefore does not establish the actual connection path.

## Allocation for a selected case

Input renewable forecasts are explicit `allocation_region,generation_type,forecast_mw` rows, where type is `wind` or `solar`. A reviewed subset can use a narrow region such as `F:Ballylickey`. The script distributes each MW value among that group's **connected, reviewed** projects in proportion to MEC; it rejects groups with no reviewed projects, unreviewed projects in the same group, or a forecast above reviewed MEC. Battery capacity does not become generation. MEC gives weights and a capacity ceiling only: the resulting project shares are hypothetical, never inferred farm output. An upstream forecast producer must provide the forecast vintage, valid time, weather-to-power method, and evidence that it was available at the decision time; this script does not create such a forecast.

`--load-weights` accepts either explicit `bus_id,weight` or TYTFS `loads.csv` with `bus_id,load_id,p_mw,in_service`. The latter aggregates positive in-service case loads by bus, then scales the shape to the supplied total load MW. **The summer 2024 case profile is a planning load shape**, not measured 2026 nodal load; use a correctly scoped all-island load assumption with the full case. The output sums renewable MW and load MW independently and reports the net injection. Other generation, interconnectors, and the balancing slack still need to be modelled before any power-flow result is meaningful.

For a transparent smoke case, write an *illustrative* 20 MW forecast for the reviewed Ballylickey subset:

```bash
mkdir -p data/raw/network_case
printf 'allocation_region,generation_type,forecast_mw\nF:Ballylickey,wind,20\n' > data/raw/network_case/illustrative_renewable.csv
python scripts/network_generators.py allocate \
  --crosswalk data/raw/network_case/generator_crosswalk.csv \
  --buses data/raw/network_case/buses.csv \
  --renewable-forecast data/raw/network_case/illustrative_renewable.csv \
  --load-weights data/raw/network_case/loads.csv \
  --total-load-mw 3402.3 \
  --output data/raw/network_case/illustrative_injections.csv \
  --report data/raw/network_case/illustrative_allocation_report.json
```

With the inspected case load profile, **3,402.3 MW** of in-service load weights were normalized to the same **3,402.3 MW** case-load assumption across 229 buses. The six projects place **20 MW** at bus 1281; total wind and load allocations reconcile to 20 and 3,402.3 MW within floating-point tolerance. Net injection is **-3,382.3 MW**, deliberately exposing the unmodelled supply/balancing requirement. This is a selected-subset example, not an all-island wind forecast or a balanced dispatch case.

The next step is to replace the illustrative 20 MW with a time-stamped forecast from the weather/forecast issues, review more station groups, and compare any regional generation allocation with independent generation evidence. Do not use same-period measured output as if it were a day-ahead forecast.
