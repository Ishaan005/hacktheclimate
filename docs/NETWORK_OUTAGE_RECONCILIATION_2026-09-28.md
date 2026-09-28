# 2026 outage publication reconciliation

Checked 28 September 2026 for [issue #11](https://github.com/Ishaan005/hacktheclimate/issues/11). This is a **planned-outage scenario crosswalk**, not a record of actual switch positions. Neither workbook confirms that equipment was out of service. The 2024 TYTFS case is a planning model, not the 2026 operating network.

## Sources and timing

| Source | File timestamp from EirGrid HTTP `Last-Modified` | Used fields |
| --- | --- | --- |
| [2026 Transmission Outage Programme](https://cms.eirgrid.ie/sites/default/files/publications/2026-Transmission-Outage-Programme-20260907.xlsx), `GEN_ALL` | 7 Sep 2026 13:15:28 UTC | Outage ID, equipment description, status, start, finish |
| [Week 40–41 Transmission Outage Summary](https://cms.eirgrid.ie/sites/default/files/publications/Transmission-Outage-Summary-2026-Week-40-41.xlsx) | 17 Sep 2026 14:16:45 UTC | Outage ID, plant, section, filled calendar cells for 27 Sep–12 Oct |
| [2024 TYTFS study files](https://cms.eirgrid.ie/sites/default/files/publications/TYTFS2024_studyfiles.zip), `TYTFS2024_SV2024_V33.raw` | 2024 planning case | Bus names/voltages, branch endpoints/circuit ID, initial branch status |

The HTTP dates are server file timestamps, **not verified first availability times**. The short-term workbook does not include an outage status or time of day. Its date cells have no text values; the script retains their fill markers and dates without treating a colored cell as proof of actual outage. A few rows color every grid day, so those rows cannot yield an exact planned start or finish from the grid. Both September publications are ineligible as features for January–August 2026 backtests.

## Reconciliation

The script reads only the annual `GEN_ALL` sheet, avoiding duplicate area sheets, and identifies short-term rows by `TO-` ID. It retains the original status and raw dates, including 21 month-only `Planned` rows without full calendar dates.

| Comparison | IDs | Interpretation |
| --- | ---: | --- |
| Annual programme | 1,559 | All statuses and dates in the 7 Sep file |
| Week 40–41 summary | 178 | Listed for the two-week report |
| Same ID in both | 87 | ID-level reconciliation only; not proof of unchanged timing or state |
| In short-term summary, absent from annual programme | 91 | Could be additions or changed identifiers; no automatic asset switch |
| In annual programme, absent from short-term summary | 1,472 | Mostly outside the short reporting window; absence is not a cancellation |

Among the 87 shared IDs, annual statuses are 58 `Scheduled`, 25 `Proposed`, 2 `Planned`, 1 `Reference`, and 1 `Reference (Proposed)`. The summary adds no explicit status. Two summary rows have blank plant descriptions (`TO-26-CBR-SVC-02`, `TO-26-PB-R2001-02`).

Sixteen shared IDs have at least one `indexed:23` marked calendar date outside the annual start–finish range. These are **timing discrepancies to review**, not confirmed changes: the workbook has no legend tying this fill to a switch event. Examples: `TO-26-DRY-GOR-1-03` is 30 Sep only in the annual file but is marked through 2 Oct in the summary; `TO-26-220 kV B1 @ CSH-01` ends 11 Sep in the annual file but is marked in October; `TO-26-TRI-CAP1-02` is 15–17 Sep in the annual file but is marked 6–8 Oct. The generated JSON lists all 91 short-term-only IDs and all 16 discrepancies with source rows.

## Reviewed demonstration crosswalk

`TO-26-CSH-FLA-1-03` is in the annual programme at `GEN_ALL!A1212` as **“220kV FEEDER - CASHLA 220-FLAGFORD 220-1”**, status `Scheduled`, 24 Sep–2 Oct 2026. The short-term summary lists **“CASHLA FLAGFORD”** at `A73:B73`, with `indexed:23` marks 27 Sep–2 Oct. The extra 27 Sep column is padding before the report's 28 Sep start; it does not conflict with the annual window.

Manual comparison against the exported 2024 SV V33 case finds one branch with both terminal names, both **220 kV** voltages, and circuit **1**: `asset_id=1642:2522:1`, from bus `1642` (CASHLA) to bus `2522` (FLAGFORD). Its planning-case `in_service` field is `True`. Match confidence is **high for asset identity** because the case has one exact candidate on those three fields. This does not establish whether the same circuit was available on a 2026 operating day.

The explicit **scenario** operation is `set_in_service(asset_type="branch", asset_id="1642:2522:1", value=False)`. Use it only on a copy of the intact TYTFS planning case, with its source vintage displayed. No automatic switch is emitted for zero or multiple exact matches, and a unique match still requires an explicit `--reviewed-asset-id` argument. Other equipment classes and approximate name matches remain unresolved.

## Reproduce

Keep both source workbooks and generated TYTFS CSVs in ignored local storage. Generate the detailed audit JSON with:

```bash
python scripts/reconcile_network_outages.py \
  --annual data/raw/network_feasibility/2026-Transmission-Outage-Programme-20260907.xlsx \
  --summary data/raw/network_feasibility/Transmission-Outage-Summary-2026-Week-40-41.xlsx \
  --buses data/raw/network_case/buses.csv \
  --branches data/raw/network_case/branches.csv \
  --transformers data/raw/network_case/transformers.csv \
  --outage-id TO-26-CSH-FLA-1-03 \
  --reviewed-asset-id 1642:2522:1 \
  --output .cache/outage-audit.json
```

The `network_case` CSVs come from the TYTFS import work in issue #10. If they are unavailable, omit the three case arguments and `--reviewed-asset-id` to audit the two publications without an asset switch.
