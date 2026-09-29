# Operator scenario evidence for Issues 01 and 02

Agreed scope: Transmission Constraint; High Frequency / Minimum Generation; SNSP. High Frequency and Minimum Generation share one published reason code, with cause tags to distinguish their cases. The examples below are documented patterns or clearly proposed cases, not live operating instructions.

## Real data and its limit

EirGrid and SONI report 1,475,913 MWh of Irish wind dispatch-down in 2025: 862,252 MWh transmission (58.4%), 516,840 MWh combined High Frequency / Minimum Generation (35.0%), and 96,582 MWh SNSP (6.5%). The combined code cannot be split into its two causes. Historic dispatch-down is not the amount recoverable by a new tool. [2025 annual report](https://cms.eirgrid.ie/sites/default/files/publications/Annual-Renewable-Constraint-and-Curtailment-Report-2025-V1.0.pdf).

The repo's Irish wind-and-solar half-hour labels for January–August 2026 total 710,371 MWh transmission, 415,471 MWh combined High Frequency / Minimum Generation, and 144,470 MWh SNSP. See [the processed labels](../data/processed/dispatch_down_labels_ie_2021_2026.csv) and [data guide](DATA_GUIDE.md). These national reason-code fields do not identify a particular circuit, exact cause inside the combined code, or viable alternative action.

Compare each proposed action against the current plan, including existing instructions, over the same window. If two limits apply together, both must pass before claiming saved energy.

## Transmission Constraint

**Meaning:** A local line or transformer cannot safely carry more renewable export. The product needs the equipment, present and forecast power flow, rating, topology, outage state, and post-failure result. Transmission-line voltage is outside this scenario's inputs and cases. EirGrid groups wind and solar sites by how strongly their output affects a given overload; topology changes can change the group. [Wind Dispatch Tool overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

**Case tags and documented examples:**
- **Intact overload:** Even with all equipment available, admitting more renewable power would exceed a rating. EirGrid documents a base-case limitation on Ballynahulla–Glenlara 110 kV.
- **Single-failure risk:** Present flow is safe, but one credible equipment trip would overload the remaining route. EirGrid describes protecting Limerick–Rathkeale 110 kV against loss of North Kerry 220 kV circuits.
- **Outage plus failure risk:** A planned outage removes one route and a further trip threatens another. EirGrid documents outage-driven Arklow–Ballybeg 110 kV and transformer cases. These are published constraint-group examples, not claims of current overload. [Constraint-group overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

**Action candidates:** paired generator MW redispatch at useful locations; charge an available battery on the exporting side; use an approved switching option when studied; or impose the smallest local renewable-group limit that restores security. Each action needs a demonstrated before/after effect on the limiting flow and worst credible post-failure flow. EirGrid describes conventional redispatch and sectionalising as South East management options; batteries have joined real-time energy scheduling. [Constraint-group overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf), [battery update](https://www.eirgrid.ie/news/grid-upgrade-boost-battery-storage-role-power-system).

**Operator measures:** limiting element and rating, flow now and after, worst post-failure margin, affected renewable group, time to act, avoided and remaining dispatch-down MWh, and system cost.

## High Frequency / Minimum Generation

**Meaning:** EirGrid's one reason code covers emergency high-frequency action and conventional generation kept online for minimum-unit, reserve, priority-dispatch or ramping needs. The same code needs a cause tag before selecting inputs or actions. [2025 annual report, reason codes](https://cms.eirgrid.ie/sites/default/files/publications/Annual-Renewable-Constraint-and-Curtailment-Report-2025-V1.0.pdf).

**Case tags and examples:**
- **High frequency active:** measured frequency is rising because generation exceeds consumption. Loss of a 500 MW interconnector export is an over-frequency contingency EirGrid and SONI studied. [Over Frequency Generation Shedding Schedule study](https://cms.eirgrid.ie/sites/default/files/publications/OPI_INN_Over_Frequency_Generation_Shedding_Schedule_Summary_Report.pdf).
- **Minimum units on:** low demand and high renewables meet a rule requiring qualified conventional units to run. The 2025 roadmap records four units in Ireland and three in Northern Ireland at that time. Use the rule effective for the case. [Operational Policy Roadmap](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf).
- **Reserve or ramping floor:** enough units may be online, yet output or headroom must remain for a required response or forthcoming ramp. [Operational Policy Roadmap](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf).
- **Cause unconfirmed:** the combined code is known, but the measured frequency and binding operating requirement are missing. Ask for clarification before suggesting an action.

**Action candidates:** For an active frequency event, test only qualified, available actions fast enough to matter: increase battery or pumped-storage consumption, reduce discharge, or lower controllable generation. EirGrid and SONI list changes to generation, storage, demand and wind set-points in frequency-control arrangements. For minimum units, test a lower valid MW for an online unit or an eligible unit swap while preserving the required count and services. For reserve or ramping, test qualified replacement service before reducing conventional output. Renewable curtailment is the fallback when the confirmed cause cannot be cleared another way. A battery or synchronous condenser must not be counted as a conventional unit unless the applicable policy allows it. [Frequency-control agreement](https://cms.eirgrid.ie/sites/default/files/publications/LFC-Block-Proposal-Submission-for-Ireland-and-Northern-Ireland-V3.0-%28pos....pdf), [system-services testing](https://www.eirgrid.ie/grid/grid-codes-and-compliance-overview/grid-code-compliance-testing/system-services-testing).

**Operator measures:** confirmed cause; frequency and trend for an event, or the exact unit/reserve/ramping rule; eligible assets, response time, before/after security margin, avoided and remaining MWh, and cost. Do not allocate the historical 516,840 MWh across these case tags without a separate source.

## SNSP

**Meaning:** System Non-Synchronous Penetration is the ratio of non-synchronous generation plus relevant net HVDC imports to demand plus relevant net HVDC exports. When its effective all-island limit binds, more wind or solar may require curtailment. It is not a wind-only percentage. EirGrid's 2025 roadmap gives a 75% status and planned trials; the July 2026 statement describes the system as able to operate with up to 75% variable renewables at that time. Every case needs the policy version effective at its timestamp. [Operational Policy Roadmap](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf), [July 2026 EirGrid statement](https://www.eirgrid.ie/news/eirgrid-statement-renewable-integration-and-dispatch-down).

**Case tags and examples:**
- **Binding now:** more renewable output would breach the ratio, even if the measured ratio is at the limit after an existing curtailment.
- **Forecast to bind:** demand falls or renewable availability rises in a coming interval. EirGrid's 2024 report shows more curtailment overnight when demand is lower. [2024 annual report](https://cms.eirgrid.ie/sites/default/files/publications/Annual-Renewable-Constraint-and-Curtailment-Report-2024-V1.0.pdf).
- **SNSP plus local constraint:** both the all-island rule and a local network bottleneck restrict the same available energy; both must clear.

**Action candidates:** an agreed, timely reduction in net HVDC imports may reduce the ratio numerator; EirGrid says countertrading requires another operator's agreement and often cannot proceed when GB is congested. A named battery-charging or generation-mix change can be tested only after recalculating the entire SNSP ratio and power balance. Charging alone is not automatically an SNSP solution: adding 100 MW of demand and admitting 100 MW more wind at a binding 75% ratio would raise the ratio above 75%. If no feasible alternative passes, apply the minimum necessary all-island renewable limit. [2025 annual report](https://cms.eirgrid.ie/sites/default/files/publications/Annual-Renewable-Constraint-and-Curtailment-Report-2025-V1.0.pdf), [battery update](https://www.eirgrid.ie/news/grid-upgrade-boost-battery-storage-role-power-system), [Wind Dispatch Tool overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

**Operator measures:** ratio before and after, effective limit and margin, formula inputs, imports/exports, forecasts, dispatch response, avoided and remaining MWh, other active limits, and cost.

## Reasoning and next evidence

Transmission has the greatest recorded energy loss and published local examples, so it is the strongest first candidate. The combined family is second by recorded MWh but must use different tags to avoid conflating an urgent event with a planned operating minimum. SNSP is a clear system-wide comparator with explicit arithmetic, yet intuitive charging ideas can fail the ratio. This is a research ranking, not an operator-approved priority order or an estimate of recoverable energy.

Seek one redacted real case per family: timestamp, current plan, exact cause, available assets, action deadline, security results, instruction chosen and observed outcome. Ask operators which three measures they consult first for each case and which alternatives they can actually instruct.

## Can we measure a percentage for each case tag?

**Current answer: no for the transmission subcases.** The public half-hour dispatch-down file has one transmission-constraint MWh field, with no intact, single-failure, or outage-plus-failure field. EirGrid's annual report gives transmission totals and regional patterns, and its Wind Dispatch Tool overview defines the three operating conditions, but neither reports their historical MWh or incident shares. Sources: [2025 annual report](https://cms.eirgrid.ie/sites/default/files/publications/Annual-Renewable-Constraint-and-Curtailment-Report-2025-V1.0.pdf), [Wind Dispatch Tool overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf), [public data catalogue](https://www.eirgrid.ie/grid/system-and-renewable-data-reports).

| Scenario case | Historical share of its family from the public file | Closest EirGrid publication |
| --- | --- | --- |
| Transmission: intact overload | Unknown | Wind Dispatch Tool overview describes the case and named constraint groups; no observed share. |
| Transmission: single-failure risk | Unknown | Same overview describes N-1 risk; no observed share. |
| Transmission: outage plus failure risk | Unknown | Same overview describes N-1-1 risk; no observed share. |
| High Frequency / Minimum Generation: high-frequency active | Unknown | One combined reason code prevents separation. |
| High Frequency / Minimum Generation: minimum units, reserve or ramping | Unknown | One combined reason code prevents separation. |
| SNSP: binding now versus forecast to bind | Unknown | SNSP MWh are published, but this is not split into forecast versus already active conditions. |

The [ECP Constraint Forecast Reports](https://www.eirgrid.ie/industry/customer-information/ecp-constraint-forecast-reports) are the closest additional numerical source. They model **future** constraint percentages by area and compare cases with and without representative maintenance outages. Their maintenance difference is a modelled change in constraint percentage of available energy, not the observed share of outage-plus-failure incidents or MWh. For example, Table 5-1 in the [ECP-2.4 methodology](https://cms.eirgrid.ie/sites/default/files/publications/ECP-2.4-Solar-and-Wind-Constraints-Report-Assumptions-and-Methodology-v1.1.pdf) shows a 4-percentage-point maintenance effect for 2027 non-priority solar in subgroup H2 & K. That number cannot be applied to Ireland's historical transmission total.

EirGrid's [dispatch-down reporting guide](https://cms.eirgrid.ie/sites/default/files/publications/New-Wind-DD-Calc-Userguide-v1.1.pdf) says its Wind Dispatch Tool uses timestamped instructions and sends individual wind-farm reports with reason-code breakdowns. The guide's published reason list still has a single TSO Constraints category; individual reports do not by themselves establish the intact/N-1/N-1-1 cause.

To calculate defensible percentages, obtain time-linked dispatch instructions and affected groups, equipment outage and switching state, base-case and N-1 security results, and the energy curtailed during each instruction. Agree whether the denominator is **transmission-constrained MWh** or **distinct constraint episodes**. Keep multiple simultaneous causes tagged; allocate MWh to one cause only when the underlying analysis supports that attribution.
