# Cashla–Flagford planning scenario

This is a reproducible **planning scenario** using the EirGrid TYTFS summer 2024
PSS/E V33 study case. It compares the intact static case, one reviewed scheduled
outage, and one additional selected contingency. It does not describe the actual
September 2026 switch state or predict future line loading.

## Reviewed assets and sources

| Role | Source and review | TYTFS asset ID |
| --- | --- | --- |
| Scheduled outage | [2026 Transmission Outage Programme, 7 September file](https://cms.eirgrid.ie/sites/default/files/publications/2026-Transmission-Outage-Programme-20260907.xlsx), `GEN_ALL` row 1212, `TO-26-CSH-FLA-1-03`, `220kV FEEDER - CASHLA 220-FLAGFORD 220-1`, status `Scheduled`, window 24 September–2 October 2026. The [Week 40–41 summary](https://cms.eirgrid.ie/sites/default/files/publications/Transmission-Outage-Summary-2026-Week-40-41.xlsx) row 73 highlights the named Cashla–Flagford entry on 27 September–2 October. Normalized endpoints, 220 kV and circuit 1 uniquely identify an in-service TYTFS branch. | `1642:2522:1` |
| Selected additional contingency | Cashla–Prospect 220 kV circuit 1 is an in-service TYTFS branch sharing the Cashla bus with the planned-outage branch. It is a chosen study contingency, not a second published outage. | `1642:4522:1` |
| Monitored branch | Cashla–Tynagh 220 kV circuit 1 is an in-service TYTFS branch. Its **RAW rate A** is 761 MVA. | `1642:5172:1` |

The short-term workbook's highlighted day cells are schedule markers. Neither
workbook establishes that equipment was actually out of service on those days.
The 2024 topology and injections are not a 2026 operational snapshot.

## Reproduce

Download the sources with `.venv/bin/python scripts/download_network_study_sources.py`, then:

```bash
.venv/bin/python -m scripts.import_tytfs_case \
  --zip data/raw/network_feasibility/TYTFS2024_studyfiles.zip \
  --output-dir data/raw/network_case

.venv/bin/python -m scripts.compare_network_scenarios \
  --case-dir data/raw/network_case \
  --outage-type branch --outage-id 1642:2522:1 \
  --outage-reference 'TO-26-CSH-FLA-1-03; annual GEN_ALL row 1212; Week 40-41 row 73; scheduled only' \
  --contingency-type branch --contingency-id 1642:4522:1 \
  --contingency-reference 'Cashla-Prospect 220 kV circuit 1; adjacent in-service TYTFS branch' \
  --monitor-type branch --monitor-id 1642:5172:1 \
  --output-json data/raw/network_case/cashla_flagford_scenario.json
```

The generated JSON includes all case flows, scenario status, component/slack
information, flow changes from both the intact and planned-outage states,
the selected monitor's rating and loading proxy, and failure reasons if a
case cannot be solved. The files under `data/raw/` remain local and untracked.

## Observed screen on the downloaded case

The same original case injections were used in each solve; the only changes
were the named branch removals. The active-power flow sign follows the RAW
branch orientation (Cashla to Tynagh).

| Run | Cashla–Tynagh flow | DC loading proxy against 761 MVA rate A | Solver status |
| --- | ---: | ---: | --- |
| Intact | -157.010 MW | 20.632% | `ok` |
| Cashla–Flagford removed | -108.265 MW | 14.227% | `ok` |
| Plus Cashla–Prospect removed | -138.597 MW | 18.212% | `ok` |

The scheduled-outage change is +48.744 MW in signed flow on this monitor
relative to intact; the additional contingency changes it by -30.331 MW
relative to the planned-outage run. These are model outputs, not measured
flows. No overload is shown on this selected monitor in this case.

The DC solver omits voltage, reactive power, losses, controls, re-dispatch
and dynamics. Comparing active MW with an MVA rating is a screening proxy,
not measured thermal headroom. This one contingency is not an EirGrid N-1
security verdict. The case's original balance and transformer-model caveats
are recorded in `validation_report.json` after import.
