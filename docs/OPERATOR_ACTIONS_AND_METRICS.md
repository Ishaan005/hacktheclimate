# What the operator sees, and what we could suggest

**Working draft, 29 September 2026.** The situation statements below restate only the situations in the [locked scenario scope](OPERATOR_SCENARIO_SCOPE.md), in the language an operator might use. Bracketed equipment and areas are fields to fill from a real case, not claims about a live event. Actions are candidates to confirm with EirGrid/SONI, not instructions issued by this project. Every action needs a named asset, valid authority, actual availability and passing security studies. EirGrid/SONI place operational security before priority-dispatch and market-efficiency objectives. [Balancing Market Principles Statement (BMPS) v9](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).

**Reading the bullets:** **Instruct** means the TSO has a dispatch route for a qualified, controllable asset; **coordinate** means switching, work or another control room must clear the step; **agree** means an external operator or customer must accept it. “Safety metrics” must pass **before** comparing renewable energy, cost or carbon. A battery, generator or load is available only within its declared MW range, response time, energy duration and service commitments. [BMPS v9, §§3.2 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).

## General safety metrics

Before comparing the actions below, apply the family-level safety gates in [General safety metrics for operator action combinations](OPERATOR_GENERAL_SAFETY_METRICS.md). This covers thermal and contingency margins for transmission; frequency, minimum units, reserve and ramping for High Frequency / Minimum Generation; and the SNSP ratio plus dynamic stability for SNSP. The extra go/no-go checks for actions such as switching, storage and interconnector changes are in [Action-specific safety metrics](OPERATOR_ACTION_SPECIFIC_SAFETY_METRICS.md).

## Transmission Constraint

These are **power-flow** problems on a named line, cable or transformer. The route may serve one local generating area, several areas sharing a corridor, or a wide renewable group. For every situation, record the actual topology, limiting asset/rating, affected renewable units, time window and whether an outage is planned or forced. A different area or asset changes the facts, not the type of situation. EirGrid's Wind Dispatch Tool (WDT) limits individual or grouped controllable wind/solar units; published examples also describe conventional redispatch and network sectionalising. [Locked scope](OPERATOR_SCENARIO_SCOPE.md); [WDT constraint-group overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “Our local export line is overloaded, and everything is in service.”

- **Instruct** a capable generator on the exporting side to reduce MW and, if needed, increase generation beyond the bottleneck. **Effect:** lowers the local flow. **Safety metrics:** local line/transformer MVA versus rating, replacement generation response, other line flows and reserve/inertia remaining. [BMPS v9, §§3.4.3 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Instruct** eligible storage to charge behind that bottleneck, or **agree** extra demand with a contracted local customer. **Effect:** uses power before it reaches the export route. **Safety metrics:** electrical location, route relief MW, charge/load limit, duration, later rebound and other limits. Ordinary demand-side-unit dispatch is for reducing demand, so extra demand needs its own arrangement. [EirGrid battery update](https://www.eirgrid.ie/news/grid-upgrade-boost-battery-storage-role-power-system); [EirGrid demand-side units](https://www.eirgrid.ie/grid/grid-codes-and-compliance-overview/grid-code-compliance-testing/dsu-setup-and-testing).
- **Instruct** the applicable WDT limit if relief cannot arrive in time. **Effect:** brings local export below its limit while renewable dispatch-down remains. **Safety metrics:** correct local group, delivered setpoint, route margin and all other active limits. [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “Output from several areas is overloading the shared route, with all equipment available.”

- **Instruct** paired MW redispatch across the relevant areas. **Effect:** shifts export away from the shared corridor. **Safety metrics:** corridor and other-route MVA/rating margins, power balance, unit ramp and reserves. [BMPS v9, §§3.4.3 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Coordinate** a studied switch/sectionalising arrangement. **Effect:** changes which routes carry the combined output. **Safety metrics:** all before/after flows, protection, islanding, switching authority and credible post-failure flows. A switch can worsen another line. [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).
- **Instruct** a shared-group WDT limit if other available actions do not clear the route. **Effect:** reduces combined renewable export. **Safety metrics:** current group members, each delivered MW reduction and worst corridor margin. [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “A route serving a wide renewable group is overloaded, although the network is intact.”

- **Instruct** locational generation redispatch or **coordinate** an approved flow-changing switch. **Effect:** may relieve the wide route without reducing the whole affected group's output. **Safety metrics:** named route and alternative-route ratings, N-1 flows, balance, reserve and stability. [BMPS v9, §3.4.3](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).
- **Agree** an interconnector trade only if a network study shows the transfer direction helps. **Effect:** changes wide-area flows and generation elsewhere. **Safety metrics:** route response, transfer/ramp capability, balance, SNSP and GB TSO acceptance. Normal coordinated trades need the other TSO's agreement. [BMPS v9, §3.4.6](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Instruct** the wide affected-group WDT limit if needed. **Effect:** restores flow headroom but leaves group-wide dispatch-down. **Safety metrics:** actual group membership, delivered output and route margin. [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “The local route is safe now, but losing one working circuit would overload its backup.”

- **Instruct** pre-emptive local redispatch or a local renewable setpoint. **Effect:** leaves enough headroom on the backup **after** the credible trip. **Safety metrics:** intact and worst post-trip MVA/rating margins, response time and reserve. [BMPS v9, §3.4.3](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).
- **Instruct/agree** useful local consumption that can continue through that trip. **Effect:** reduces export through the backup path. **Safety metrics:** post-trip connection, MW response, duration, storage energy and any service it displaces. [BMPS v9, §§3.2 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).

### “Several areas are fine now, but one trip would overload their shared backup corridor.”

- **Instruct** paired redispatch across the areas or **coordinate** a studied switching arrangement. **Effect:** reduces the worst post-trip shared flow. **Safety metrics:** every credible trip's corridor loading, all new paths, switching/protection and unit response. [BMPS v9, §3.4.3](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).
- **Instruct** a pre-constraint across the relevant group if necessary. **Effect:** preserves post-trip corridor headroom at the cost of renewable MWh. **Safety metrics:** group allocation, delivery before the risky interval and worst post-trip margin. [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “One trip would overload a route affecting a wide renewable group.”

- **Instruct** locational generation redispatch or **agree** a helpful transfer change if it can be in place before the risk. **Effect:** reduces the wide route's worst post-trip flow. **Safety metrics:** transfer and generator response, all credible post-trip flows, balance, reserve and SNSP. [BMPS v9, §§3.4.3 and 3.4.6](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Instruct** a wide-group pre-limit if other feasible actions cannot make enough room. **Effect:** preserves security but causes dispatch-down. **Safety metrics:** group setpoints, worst post-trip flow/rating and how long the limit must last. [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “A line is out, and the local area's remaining export route is overloaded.”

- **Coordinate** an earlier return to service **only if** the asset owner and work party release the equipment safely. **Effect:** may restore the missing path. **Safety metrics:** actual fault/work status, switching permission, return time and restored-grid loading. A forced fault cannot be assumed repairable on demand. [EirGrid outage information](https://www.eirgrid.ie/industry/customer-information/outage-information).
- **Instruct** local redispatch or eligible local charging; **agree** any extra customer demand. **Effect:** reduces the remaining route's flow while the outage persists. **Safety metrics:** outage-state MVA/rating, load/generator response, duration, rebound and reserves. [BMPS v9, §§3.4.3 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Instruct** the outage-specific WDT limit if needed. **Effect:** clears the working route but leaves local dispatch-down. **Safety metrics:** current outage group, actual output and remaining route margin. [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “An outage has diverted several areas' output onto a shared route, and it is overloaded.”

- **Coordinate** a safe return/deferment of planned work or approved switching. **Effect:** can restore or change the shared path. **Safety metrics:** work release, switching/protection, all outage-state flows and time to relief. [EirGrid outage information](https://www.eirgrid.ie/industry/customer-information/outage-information); [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).
- **Instruct** cross-area redispatch or the outage-specific WDT group limit. **Effect:** reduces combined flow; the WDT choice leaves renewable dispatch-down. **Safety metrics:** named route margin, new overloaded routes, generator ramp and group setpoint response. [BMPS v9, §3.4.3](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “During this outage, a route serving a wide renewable group has hit its limit.”

- **Coordinate** a safe equipment return or studied switch; **agree** a transfer change only if it reduces this route's flow. **Effect:** may create wide-area headroom without limiting the whole group. **Safety metrics:** work status, all route loadings, transfer availability, switching/protection and other system limits. [EirGrid outage information](https://www.eirgrid.ie/industry/customer-information/outage-information); [BMPS v9, §3.4.6](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Instruct** wide-group redispatch or the applicable outage-specific renewable limit. **Effect:** reduces the binding flow; a renewable limit leaves dispatch-down. **Safety metrics:** actual group, route MVA/rating, response time and other constraints. [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “One local route is already out; losing another would overload the last export path.”

- **Coordinate** safe return of the out-of-service route if physically possible. **Effect:** removes the first outage condition. **Safety metrics:** work/fault clearance, return time and full restored-network study. [EirGrid outage information](https://www.eirgrid.ie/industry/customer-information/outage-information).
- **Instruct** pre-positioned local redispatch or a renewable pre-limit. **Effect:** leaves the last path within its rating after the further trip. **Safety metrics:** outage-state and worst further-trip MVA/rating, response time and continued service. [BMPS v9, §3.4.3](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “A shared route is out, and one more trip would overload the remaining corridor.”

- **Coordinate** safe outage return or approved switching. **Effect:** may remove the vulnerable topology. **Safety metrics:** work/protection clearance, each new path, actual outage flow and worst further-trip flow. [EirGrid outage information](https://www.eirgrid.ie/industry/customer-information/outage-information); [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).
- **Instruct** cross-area redispatch or a pre-limit on the relevant renewable group. **Effect:** reduces the remaining corridor's post-trip loading; a limit leaves dispatch-down. **Safety metrics:** N-1-1 margin, correct group, ramp and persistence after the trip. [BMPS v9, §3.4.3](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

### “One route is out, and another trip would overload a route affecting a wide renewable group.”

- **Coordinate** safe return/switching or **agree** a helpful transfer change if studies and timing permit. **Effect:** may create wide-area post-trip headroom. **Safety metrics:** actual work status, transfer/ramp availability, all further-trip loadings and linked system limits. [EirGrid outage information](https://www.eirgrid.ie/industry/customer-information/outage-information); [BMPS v9, §3.4.6](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Instruct** wide-area redispatch or the outage-specific WDT pre-limit. **Effect:** keeps the surviving route secure after the extra failure; the limit leaves renewable MWh unused. **Safety metrics:** worst N-1-1 margin, delivery before the risk and ability to sustain the action. [WDT overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

**What we can show now:** The [GFS model](GFS_CONSTRAINT_TRAINING.md) forecasts **national constraint** probability/MWh, not a named route, case, farm or action effect. Its August expected-MWh error did not beat a zero forecast. The [network screen](NETWORK_SAFETY_ACTIONS.md) can show a **planning-case sensitivity** for a hypothetical flexible load paired with more renewable output and selected outages; its MWh is an upper bound, and it issues no safe recommendation. Live topology/flows, complete safety studies, actual instructions and site-level outcomes are still needed. [Network data feasibility audit](NETWORK_DATA_FEASIBILITY_2026-09-28.md).

## High Frequency / Minimum Generation

These are system-wide situations. The published dispatch-down data combine emergency high frequency with minimum-generation, reserve and ramping causes; our model cannot learn which one bound from that reason code alone. Several requirements can apply simultaneously. The following statements preserve every tracked situation in the [locked scope](OPERATOR_SCENARIO_SCOPE.md). [2025 dispatch-down report, reason codes](https://cms.eirgrid.ie/sites/default/files/publications/Annual-Renewable-Constraint-and-Curtailment-Report-2025-V1.0.pdf); [Operational Policy Roadmap](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf).

### “The export interconnector stopped taking power, and frequency is high.”

- **Instruct** fast capable generation reduction or storage/pumped consumption. **Effect:** removes the surplus left by lost export. **Safety metrics:** measured Hz and trend, response MW/seconds, unit minimums, battery energy and reserves after response. [LFC Block Operational Agreement, Arts 5–6](https://cms.eirgrid.ie/sites/default/files/publications/S2-LFC-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland-29.09.2022.pdf).
- **Coordinate/agree** emergency HVDC assistance if an available route can respond. **Effect:** may restore an export or otherwise reduce imbalance; the failed link is not assumed available. **Safety metrics:** link status, transfer direction, ramp and actual frequency recovery. [LFC Block Operational Agreement, Art. 5](https://cms.eirgrid.ie/sites/default/files/publications/S2-LFC-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland-29.09.2022.pdf).
- **Instruct** a controllable renewable limit if required. **Effect:** cuts generation to contain frequency, leaving dispatch-down. **Safety metrics:** actual setpoint delivery, Hz recovery and reserve. Pre-armed high-frequency shedding is a protection response, not an energy-saving suggestion. [LFC Block Operational Agreement, Art. 5](https://cms.eirgrid.ie/sites/default/files/publications/S2-LFC-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland-29.09.2022.pdf).

### “Demand just fell unexpectedly, and frequency is high.”

- **Instruct** eligible storage charging/pumping and reduce dispatchable generation. **Effect:** closes the supply-demand gap. **Safety metrics:** measured Hz/trend, response time, charge room, unit minima, network and reserve margins. [LFC Block Operational Agreement, Art. 5](https://cms.eirgrid.ie/sites/default/files/publications/S2-LFC-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland-29.09.2022.pdf).
- **Instruct** renewable setpoints if other timely capacity is insufficient. **Effect:** rapidly reduces surplus but leaves dispatch-down. **Safety metrics:** delivered MW, frequency recovery and risk of a later shortfall when demand returns. [LFC Block Operational Agreement, Art. 5](https://cms.eirgrid.ie/sites/default/files/publications/S2-LFC-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland-29.09.2022.pdf).

### “Generation or imports rose faster than expected, and frequency is high.”

- **Instruct** the capable source to reduce MW or storage to consume power; **agree** a transfer correction when the cause is an interconnector schedule and the route permits it. **Effect:** reduces the unexpected surplus. **Safety metrics:** measured Hz/trend, source/transfer response, ramp, reserves and other network limits. [LFC Block Operational Agreement, Art. 5](https://cms.eirgrid.ie/sites/default/files/publications/S2-LFC-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland-29.09.2022.pdf); [BMPS v9, §3.4.6](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Instruct** renewable limits if required to restore frequency. **Effect:** removes surplus but creates dispatch-down. **Safety metrics:** setpoint delivery, recovery and reserve left. [LFC Block Operational Agreement, Art. 5](https://cms.eirgrid.ie/sites/default/files/publications/S2-LFC-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland-29.09.2022.pdf).

### “We must keep the required conventional units on in Ireland, even at low demand.”

- **Instruct** eligible Irish units down to valid technical minimums. **Effect:** frees MW room for renewables while preserving the required count. **Safety metrics:** qualified Irish count, each minimum, inertia, local support, reserve and ramp. [Operational Policy Roadmap, minimum units](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf).
- **Instruct/coordinate** a qualified lower-minimum unit swap with sufficient notice, or eligible charging/pumping. **Effect:** lowers unavoidable output or absorbs energy. **Safety metrics:** count throughout the swap, start time, other services, storage duration and SNSP. Charging does not replace a required unit. [BMPS v9, §§3.2 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Instruct** the necessary renewable limit if room cannot be created safely. **Effect:** leaves dispatch-down while meeting the unit rule. **Safety metrics:** Irish count and all co-binding limits. [2025 dispatch-down report, reason codes](https://cms.eirgrid.ie/sites/default/files/publications/Annual-Renewable-Constraint-and-Curtailment-Report-2025-V1.0.pdf).

### “We must keep the required conventional units on in Northern Ireland.”

- **Instruct** eligible Northern Ireland units down to their valid minimum, or **coordinate** a qualified lower-minimum swap. **Effect:** may make room for renewables while keeping the required **Northern Ireland** count. **Safety metrics:** qualified NI count at every step, minima, inertia, north-south transfer and local services. [Operational Policy Roadmap, minimum units](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf).
- **Instruct/agree** eligible charging or contracted extra demand if it helps; otherwise **instruct** the necessary renewable limit. **Effect:** absorbs energy or leaves dispatch-down. **Safety metrics:** demand/storage duration, SNSP, regional flows and all simultaneous unit/reserve rules. [BMPS v9, §§3.2 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).

### “The minimum conventional-unit rules bind in both Ireland and Northern Ireland.”

- **Instruct/coordinate** MW reductions or qualified swaps in each jurisdiction. **Effect:** reduces combined minimum output without losing either required count. **Safety metrics:** **both** counts, unit minima throughout transitions, north-south flows, inertia, reserves and ramp. [Operational Policy Roadmap, minimum units](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf).
- **Instruct/agree** storage charging or extra demand where feasible, then apply the necessary renewable limit if still required. **Effect:** uses some surplus or leaves dispatch-down. **Safety metrics:** location, duration, SNSP, both unit rules and network effects. [BMPS v9, §§3.2 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).

### “We need enough upward reserve for a sudden loss of supply or rise in demand.”

- **Instruct** an already qualified provider to hold the required upward service, allowing a conventional unit to reduce output only if the replacement truly covers it. **Effect:** can free renewable room while preserving response. **Safety metrics:** required versus available MW by service tranche and jurisdiction, speed, sustain time, state of charge and unit count. [LFC Block Operational Agreement, Art. 8](https://cms.eirgrid.ie/sites/default/files/publications/S2-LFC-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland-29.09.2022.pdf); [system-services testing](https://www.eirgrid.ie/grid/grid-codes-and-compliance-overview/grid-code-compliance-testing/system-services-testing).
- **Instruct** capable generator/storage MW or commitment to create headroom if reserve is short. **Effect:** restores reserve coverage, possibly reducing renewable room. **Safety metrics:** actual qualified headroom and response, inertia, ramp, SNSP and network. A renewable output limit alone does not supply missing qualified reserve. [BMPS v9, §§3.4.4 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).

### “We need downward reserve for a sudden surplus.”

**Use this situation only when the rule effective for the event requires downward reserve and it is the confirmed limiting cause.** The public roadmap discusses introducing downward products; it does not prove a particular event had that requirement. [Locked scope](OPERATOR_SCENARIO_SCOPE.md); [Operational Policy Roadmap, reserves](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf).

- **Instruct** an eligible, qualified provider to hold downward capability, such as generation reduction or storage consumption where that exact service is credited. **Effect:** preserves response to a sudden surplus while potentially releasing an inflexible conventional unit. **Safety metrics:** effective downward requirement, qualified MW, response time, sustain time, energy room and unit count. [BMPS v9, §§3.2 and 3.4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Instruct** a necessary renewable limit if minimum conventional output still leaves no balance room. **Effect:** reduces current supply but does **not** create qualified downward reserve by itself. **Safety metrics:** downward coverage, balance, SNSP and remaining dispatch-down. [BMPS v9, §§4.4–4.5](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).

### “Over the next hours, demand may rise or renewables/imports may fall; we need power to ramp up.”

- **Instruct/commit** qualified units, storage or demand-reduction capability before the rise. **Effect:** provides upward MW at the required one-, three- or eight-hour point. **Safety metrics:** required versus available ramp at each deadline, start notice, MW/minute, sustained output, storage energy and reserve. The published RM1/RM3/RM8 products specify different delivery and hold periods. [EirGrid/SONI ramping requirements](https://www.sem-o.com/documents/general-publications/Ramping_Margin_Requirements_in_Scheduling.pdf).
- **Instruct** a renewable limit only if needed to keep capable conventional output/headroom available. **Effect:** may protect a future ramp but leaves current dispatch-down. **Safety metrics:** the full forecast trajectory, actual deliverable ramp and every co-binding requirement; curtailment itself does not supply upward ramp. [BMPS v9, §4.3.2](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).

### “Over the next hours, demand may fall, renewables may rise, or an export may drop; we need power to ramp down.”

- **Instruct** capable conventional generation to lower output or eligible storage to charge/pump ahead of the fall. **Effect:** creates downward room. **Safety metrics:** unit technical minimum and downward MW/minute, charge headroom/duration, rebound, reserve, minimum-unit count and network. Confirm the effective downward ramp policy; the published RM1/RM3/RM8 definitions describe upward capability. [BMPS v9, §§3.2 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [ramping requirements](https://www.sem-o.com/documents/general-publications/Ramping_Margin_Requirements_in_Scheduling.pdf).
- **Instruct** a renewable limit if the downward change cannot otherwise be accommodated. **Effect:** prevents a surplus but leaves dispatch-down. **Safety metrics:** forecast net-load path, response/duration and all simultaneous reserve/SNSP limits. [BMPS v9, §§4.3.2 and 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).

**What we can show now:** Our [half-hour labels](DATA_GUIDE.md) have only the **combined** High Frequency / Minimum Generation reason, so they cannot tell which statement above caused a recorded MWh or what a replacement action would have saved. H1 also needs high-rate frequency/response data; H2–H4 need effective rules, unit declarations, service awards and instruction logs. We can illustrate rule calculations with operator-supplied facts, then validate against real cases. [Data feasibility audit](NETWORK_DATA_FEASIBILITY_2026-09-28.md).

## SNSP

### “The all-island non-synchronous share is at its operating limit.”

The operator may add: “wind or solar is rising,” “demand is falling,” “net imports are rising,” or “net exports are falling.” These are the four tracked ways to reach the **same single situation**, now or at a forecast time. Use the ratio and limit effective for that interval, including the correct treatment of batteries and signed interconnector transfers. [Locked scope](OPERATOR_SCENARIO_SCOPE.md); [Operational Policy Roadmap, SNSP definition](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf); [2025 dispatch-down report, §4](https://cms.eirgrid.ie/sites/default/files/publications/Annual-Renewable-Constraint-and-Curtailment-Report-2025-V1.0.pdf).

- **Agree** a lower import or greater export, when the direction and counterpart allow it. **Effect:** may reduce the SNSP ratio and admit more renewable output. **Safety metrics:** recalculated numerator, denominator and percentage-point margin; transfer/ramp capacity, balance, network, reserve and GB TSO acceptance. EirGrid/SONI examine local actions first; coordinated trades can be refused. [BMPS v9, §3.4.6](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
- **Instruct** eligible battery charging/pumping, or **agree** extra customer consumption. **Effect:** can absorb energy, but may **worsen a binding ratio** if equal additional non-synchronous renewable output is admitted: `(N + Δ)/(D + Δ) > N/D` when the original ratio is below 100%, where N and D are the current ratio numerator and denominator. **Safety metrics:** full recalculated ratio, charge/load duration, later discharge/rebound, inertia, RoCoF, reserve and local line loading. [Operational Policy Roadmap, SNSP definition](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf); [EirGrid battery update](https://www.eirgrid.ie/news/grid-upgrade-boost-battery-storage-role-power-system).
- **Instruct** the required all-island WDT renewable limit. **Effect:** lowers the non-synchronous share but leaves dispatch-down. **Safety metrics:** measured/forecast ratio against the effective limit, output response, dynamic security and every overlapping transmission/H-family requirement. Changing the limit itself needs a policy/trial decision. [BMPS v9, §§4.4–4.5](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [Operational Policy Roadmap, dynamic stability](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf).

**What we can show now:** [Processed system context](EIRGRID_SOURCES.md) and [SNSP dispatch-down labels](DATA_GUIDE.md) support retrospective ratio and national MWh displays. A what-if ratio can be calculated from **explicitly supplied, correctly signed** inputs. The data do not establish a safe live action or its avoided dispatch-down without the effective rule, point-in-time forecast, asset response and linked security studies. Same-period measurements cannot stand in for a forward forecast. [Data feasibility audit](NETWORK_DATA_FEASIBILITY_2026-09-28.md).

## How we would show the result of any suggested action

The comparison starts from the **current operating plan, including instructions already in force**. Show that plan, continuation with no new instruction, our candidate and an alternative entered by the operator over the **same time window**. “Do nothing” does not remove existing limits. Reject a candidate if any required safety check fails or is unknown. EirGrid/SONI distinguish indicative schedules from actual instructions and continually reassess the schedule. [BMPS v9, §§4.3–4.5](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).

| Measure to show | Calculation against the current plan | What we can claim today |
| --- | --- | --- |
| **Safety, response and margin** | Named limit minus worst calculated flow/ratio, or qualified capability minus required MW; show before/after, worst credible failure, response deadline and duration. | A planning sensitivity for selected T networks; **no live safety pass** from current data. [Network safety screen](NETWORK_SAFETY_ACTIONS.md). |
| **Avoided and remaining renewable dispatch-down** | `avoided MWh = current-plan DD − candidate DD`; `remaining MWh = candidate DD`, using site availability and *all* active setpoints, without double-counting overlapping causes. | Historic national reason-code MWh and a modeled T capture **upper bound** only. Action-specific avoided MWh is **unavailable**. [WDT dispatch-down guide](https://cms.eirgrid.ie/sites/default/files/publications/New-Wind-DD-Calc-Userguide-v1.1.pdf); [network safety screen](NETWORK_SAFETY_ACTIONS.md). |
| **Net system resource cost** | Candidate minus current plan for fuel, starts, variable running cost, storage wear/loss/recharge, services, transfers and any moved outage work; report market payments separately. | **Unavailable** without offers/contracts and an action-aware dispatch comparison. Renewable MWh saved does not automatically save money. [BMPS v9, §§2.5 and 4.3](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf). |
| **Carbon impact** | Candidate minus current plan tonnes CO₂ from units actually started/displaced, storage losses and changed imports, with a stated accounting boundary. | **Unavailable** without the counterfactual generation/import mix. An observed average grid-intensity factor is not an action effect. [EirGrid Carbon Clock guide](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-Group-Carbon-Clock-User-Guide.pdf); [SEAI displacement method](https://www.seai.ie/sites/default/files/publications/Energy-in-Ireland-2021_Final.pdf). |
| **Uncertainty** | Forecast issue/valid times and ranges for demand, renewables, outage return, response and credible failures; show the worst passing safety margin. | National forecast uncertainty exists; it is **not** validated site/action uncertainty. [GFS model evaluation](GFS_CONSTRAINT_TRAINING.md). |

## Decisions needed before these become operator suggestions

1. Confirm these action candidates, instruction authority, actual controllable assets, notice times and counterparties with operators using one redacted case from each family.
2. Agree the mandatory safety studies and effective rules for each situation, including simultaneous limits, downward reserve/ramping and the SNSP treatment of storage and transfers.
3. Obtain case-linked instructions, renewable availability, asset response and security results to validate action effects against the **current-plan** counterfactual.
4. Ask operators which safety result and deadline they want first on screen, then confirm the value of avoided/remaining MWh, net resource cost, carbon and uncertainty. Do not infer numerical preferences from public dispatch-down totals. [BMPS v9, §2.5](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf).
## Action and data index by real-world situation

This index covers every action candidate above, in the same situation order. **Control room** data means live measurements, grid topology, existing instructions and the security study for the proposed action. **Asset** data means declared status, location, MW range, response, energy and service qualification from the provider. **Other party** data means permission or agreement from a work party, customer or interconnector counterparty. An action is usable only if its safety checks pass; the data below identify what the operator needs to make that decision. Dispatch declarations and instructions, coordinated trades and network operations follow distinct EirGrid/SONI processes. [Balancing Market Principles Statement (BMPS) v9](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [outage information](https://www.eirgrid.ie/industry/customer-information/outage-information).

**Available in this project:** Half-hour national system context and historical dispatch-down labels can describe the past and anchor a current-plan comparison. They do not contain case-linked instructions, live frequency response, unit declarations or validated action-specific outcomes. The existing network screen is a planning sensitivity, not an operational safety pass. Avoided MWh, net resource cost and carbon need a same-window action comparison with the **current plan, including instructions already in force**. [Data guide](DATA_GUIDE.md); [network safety screen](NETWORK_SAFETY_ACTIONS.md); [data feasibility audit](NETWORK_DATA_FEASIBILITY_2026-09-28.md).

### General safety metrics

Before comparing the actions below, apply the family-level safety gates in [General safety metrics for operator action combinations](OPERATOR_GENERAL_SAFETY_METRICS.md). This covers thermal and contingency margins for transmission; frequency, minimum units, reserve and ramping for High Frequency / Minimum Generation; and the SNSP ratio plus dynamic stability for SNSP. The extra go/no-go checks for actions such as switching, storage and interconnector changes are in [Action-specific safety metrics](OPERATOR_ACTION_SPECIFIC_SAFETY_METRICS.md).

## Transmission Constraint

**“Our local export line is overloaded, and everything is in service.”**

- **Instruct local generator down and replacement generation up.** **Data:** control-room line flow/rating, other-route study and active instructions; asset locations, MW ranges and ramps. **Use:** confirm the overload clears without losing balance or reserve.
- **Instruct local storage charging or agree contracted extra demand.** **Data:** control-room connection and flow sensitivity; asset/customer MW, energy, duration and contract. **Use:** confirm local consumption relieves this line soon enough and lasts through the risk.
- **Instruct local WDT renewable limit.** **Data:** control-room group membership, current setpoints, delivered output and line margin. **Use:** clear the overload and show renewable MWh still dispatched down.

**“Output from several areas is overloading the shared route, with all equipment available.”**

- **Instruct paired generator redispatch.** **Data:** control-room corridor and alternative-route flows, active instructions; asset locations and ramps. **Use:** move flow off the corridor without causing another overload or reserve gap.
- **Coordinate studied switching or sectionalising.** **Data:** network owner/control-room switch state, protection permission and before/after failure studies. **Use:** establish whether the new topology is safe and executable.
- **Instruct shared-group WDT limit.** **Data:** control-room group membership, unit setpoint delivery and corridor margin. **Use:** verify combined output falls enough; show remaining dispatch-down.

**“A route serving a wide renewable group is overloaded, although the network is intact.”**

- **Instruct locational redispatch or coordinate an approved switch.** **Data:** control-room route sensitivities, alternative routes and N-1 study; asset ramp or switching clearance. **Use:** test selective relief without limiting the whole group.
- **Agree a helpful interconnector transfer.** **Data:** control-room transfer-to-flow and SNSP studies; other TSO capacity, ramp and agreement. **Use:** ensure the transfer direction actually relieves the route and can arrive in time.
- **Instruct wide-group WDT limit.** **Data:** control-room group members, delivered MW and route margin. **Use:** secure the route and quantify group-wide dispatch-down.

**“The local route is safe now, but losing one working circuit would overload its backup.”**

- **Instruct pre-emptive local redispatch or a renewable setpoint.** **Data:** control-room intact and worst post-trip flow, existing instructions; asset response. **Use:** make the backup safe before a credible trip.
- **Instruct or agree local consumption that survives the trip.** **Data:** control-room post-trip connection and flow study; asset/customer MW, energy, duration and permission. **Use:** count relief only if it remains available after the trip.

**“Several areas are fine now, but one trip would overload their shared backup corridor.”**

- **Instruct paired redispatch or coordinate studied switching.** **Data:** control-room flows for every credible trip; network-owner switching/protection clearance; asset ramp. **Use:** make the worst post-trip margin safe without moving the risk elsewhere.
- **Instruct group renewable pre-limit.** **Data:** control-room group setpoints, delivery time and worst post-trip corridor flow. **Use:** create headroom before the risk interval and show dispatched-down MWh.

**“One trip would overload a route affecting a wide renewable group.”**

- **Instruct locational redispatch or agree a helpful transfer change.** **Data:** control-room worst post-trip flows and transfer sensitivity; asset/other TSO ramp, capacity and agreement. **Use:** test whether selective relief is timely and secure across credible trips.
- **Instruct wide-group pre-limit.** **Data:** control-room WDT members, setpoints, post-trip route margin and risk window. **Use:** preserve headroom for the necessary duration; show remaining dispatch-down.

**“A line is out, and the local area's remaining export route is overloaded.”**

- **Coordinate safe return of the out-of-service asset.** **Data:** network owner/work party fault or work clearance, permission and return time; control-room restored-topology study. **Use:** restore a path only when physically released and secure.
- **Instruct local redispatch or charging; agree contracted extra demand.** **Data:** control-room outage-state flows; asset/customer location, MW, response, duration and contract. **Use:** relieve the remaining route throughout the outage.
- **Instruct outage-specific WDT limit.** **Data:** control-room actual outage group, setpoint delivery and remaining-route loading. **Use:** clear the live overload and show renewable output still limited.

**“An outage has diverted several areas' output onto a shared route, and it is overloaded.”**

- **Coordinate safe equipment return, work deferment or approved switching.** **Data:** network owner/work party release; control-room switching/protection and outage-state study. **Use:** decide whether a safe topology change can clear the corridor in time.
- **Instruct cross-area redispatch or outage-group WDT limit.** **Data:** control-room all-route flows, group setpoints and existing instructions; asset ramp. **Use:** choose deliverable flow relief and identify the WDT option's dispatch-down.

**“During this outage, a route serving a wide renewable group has hit its limit.”**

- **Coordinate safe return or switching; agree a helpful transfer.** **Data:** work party/network-owner clearance; other TSO agreement; control-room all-route and transfer studies. **Use:** check that a changed path or transfer creates secure headroom.
- **Instruct wide-area redispatch or outage-group renewable limit.** **Data:** control-room binding route, group, active instructions and security study; asset response. **Use:** clear the route and compare renewable energy under safe options.

**“One local route is already out; losing another would overload the last export path.”**

- **Coordinate safe return of the out-of-service route.** **Data:** network owner/work party clearance and return time; control-room restored-network study. **Use:** remove the vulnerable outage state only after safe restoration.
- **Instruct local redispatch or renewable pre-limit.** **Data:** control-room outage-state and worst further-trip flows; asset response and duration. **Use:** keep the last path within rating after another failure.

**“A shared route is out, and one more trip would overload the remaining corridor.”**

- **Coordinate safe return or approved switching.** **Data:** network owner/work party clearance, protection and switch authority; control-room present and further-trip flows. **Use:** check the new topology removes the vulnerability.
- **Instruct cross-area redispatch or group renewable pre-limit.** **Data:** control-room N-1-1 study, current instructions and group membership; asset ramp. **Use:** achieve safe worst further-trip margin before exposure starts.

**“One route is out, and another trip would overload a route affecting a wide renewable group.”**

- **Coordinate safe return/switching or agree a helpful transfer.** **Data:** work party/network-owner permission; other TSO capacity and agreement; control-room further-trip flows. **Use:** establish timely, safe relief across the wide area.
- **Instruct wide-area redispatch or outage-group WDT pre-limit.** **Data:** control-room worst N-1-1 flows, group setpoints and active instructions; asset response. **Use:** secure the surviving route and quantify remaining dispatch-down.

For every transmission action, the named line, cable or transformer margin must pass in the current topology and required credible-failure states, together with balance, reserve and other active limits. Our data cannot certify that margin for a live action. [WDT constraint-group overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf); [network safety screen](NETWORK_SAFETY_ACTIONS.md).

### High Frequency / Minimum Generation

**“The export interconnector stopped taking power, and frequency is high.”**

- **Instruct fast generator reduction or storage/pumped consumption.** **Data:** control-room high-rate Hz/trend, lost-export MW and instructions; asset response seconds, minimum output or charge room. **Use:** remove the surplus fast enough while retaining reserve.
- **Coordinate or agree emergency HVDC assistance on an available link.** **Data:** control-room/other TSO link status, direction, capacity, ramp and emergency arrangement. **Use:** confirm real assistance exists; never count the failed link.
- **Instruct controllable renewable limit.** **Data:** control-room WDT delivery, frequency recovery and reserve. **Use:** contain frequency and show resulting dispatch-down.

**“Demand just fell unexpectedly, and frequency is high.”**

- **Instruct storage charging/pumping and dispatchable generation reduction.** **Data:** control-room Hz/trend, demand step and network; asset charge room, unit minimum and response. **Use:** close the surplus without exhausting storage or required services.
- **Instruct renewable setpoint if timely alternatives are insufficient.** **Data:** control-room WDT response, Hz recovery and demand-return forecast. **Use:** restore frequency without creating a later shortfall; show dispatch-down.

**“Generation or imports rose faster than expected, and frequency is high.”**

- **Instruct source reduction or storage consumption; agree an interconnector correction if relevant.** **Data:** control-room Hz/trend, source change and balance; asset/other TSO response, transfer capacity and agreement. **Use:** reverse the actual surplus source without worsening other limits.
- **Instruct renewable limit if needed.** **Data:** control-room WDT delivery, Hz recovery and reserve margin. **Use:** restore frequency when other response is insufficient; record MWh lost.

**“We must keep the required conventional units on in Ireland, even at low demand.”**

- **Instruct eligible Irish units to technical minimum.** **Data:** control-room effective Irish rule, qualified count and instructions; asset minimum MW, inertia and services. **Use:** create renewable room without losing the required Irish units or support.
- **Instruct or coordinate a lower-minimum qualified unit swap or eligible charging/pumping.** **Data:** control-room unit-count trajectory and concurrent limits; asset start notice, minimum, charge duration and qualification. **Use:** check the transition is safe and creates usable room.
- **Instruct necessary renewable limit.** **Data:** control-room count rule, WDT delivery and co-binding limits. **Use:** preserve the rule when no safe alternative creates enough room.

**“We must keep the required conventional units on in Northern Ireland.”**

- **Instruct NI units to minimum or coordinate a qualified swap.** **Data:** control-room NI count, north-south flows and instructions; asset minima, notice and services. **Use:** preserve NI count and regional security throughout.
- **Instruct or agree charging/extra demand; otherwise instruct renewable limit.** **Data:** control-room both jurisdictions' limits, SNSP and WDT; asset/customer MW, duration and contract. **Use:** see whether absorption creates safe room, or whether output must be limited.

**“The minimum conventional-unit rules bind in both Ireland and Northern Ireland.”**

- **Instruct or coordinate reductions or swaps in both jurisdictions.** **Data:** control-room both effective counts, transfer flows and instructions; asset minima, notice and services. **Use:** meet both rules at every step.
- **Instruct or agree charging/extra demand, then necessary renewable limit.** **Data:** control-room both unit rules, SNSP, network and WDT; asset/customer location, energy and agreement. **Use:** absorb energy only when concurrent limits pass; show remaining dispatch-down.

**“We need enough upward reserve for a sudden loss of supply or rise in demand.”**

- **Instruct a qualified replacement provider to hold upward service.** **Data:** control-room effective requirement and service awards by jurisdiction; provider qualification, MW, response, sustain time and charge. **Use:** confirm replacement really covers reserve before lowering a conventional unit.
- **Instruct generator/storage output or commitment to create headroom.** **Data:** control-room required and qualified available MW, unit count and network; asset start/ramp and service capability. **Use:** restore deliverable reserve even if that uses renewable room.

**“We need downward reserve for a sudden surplus.”**

- **Instruct a qualified provider to hold downward service, if the effective rule requires it.** **Data:** control-room effective downward policy, requirement and awards; provider credited MW, response, duration and energy room. **Use:** prove qualified downward coverage before releasing an inflexible unit.
- **Instruct necessary renewable limit if balance room is still short.** **Data:** control-room downward reserve coverage, balance, SNSP and WDT response. **Use:** reduce current surplus while recognising the limit does not itself supply qualified reserve.

**“Over the next hours, demand may rise or renewables/imports may fall; we need power to ramp up.”**

- **Instruct or commit qualified generation, storage or demand reduction.** **Data:** control-room dated net-load forecast, applicable ramp requirement and instructions; asset notice, MW/minute, sustained MW and energy. **Use:** confirm power at each deadline while preserving reserve.
- **Instruct renewable limit only if needed to hold capable conventional headroom.** **Data:** control-room full forecast path, qualified ramp and concurrent limits; asset committed headroom. **Use:** retain a real future ramp option while showing current dispatch-down.

**“Over the next hours, demand may fall, renewables may rise, or an export may drop; we need power to ramp down.”**

- **Instruct conventional reduction or storage charging/pumping ahead of the fall.** **Data:** control-room dated net-load forecast and effective downward policy; asset technical minimum, downward ramp, charge energy and rebound. **Use:** confirm enough downward movement arrives when the surplus does.
- **Instruct renewable limit if downward movement is insufficient.** **Data:** control-room forecast trajectory, WDT response, reserve and SNSP. **Use:** prevent surplus while showing dispatch-down and other binding limits.

High-frequency choices need measured Hz and response in seconds; our half-hour table cannot verify them. Unit, reserve and ramp choices need the rule effective for the interval, qualified providers, service awards and time-stamped instructions. The public High Frequency / Minimum Generation label does not distinguish these causes. [LFC Block Operational Agreement](https://cms.eirgrid.ie/sites/default/files/publications/S2-LFC-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland-29.09.2022.pdf); [Operational Policy Roadmap](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf); [data guide](DATA_GUIDE.md).

### SNSP

**“The all-island non-synchronous share is at its operating limit.”** Rising renewable output, falling demand, rising imports and falling exports are four ways to reach this same situation.

- **Agree lower imports or greater exports with the other TSO.** **Data:** control-room signed transfer values, effective SNSP rule, balance, network and reserve study; other TSO capacity, ramp and acceptance. **Use:** count ratio relief only if the transfer is accepted, timely and secure.
- **Instruct eligible charging/pumping or agree extra customer demand.** **Data:** control-room full SNSP numerator/denominator and dynamic-security study; asset/customer MW, energy, duration and contract. **Use:** check whether absorption actually improves the binding ratio and remains sustainable.
- **Instruct all-island WDT renewable limit.** **Data:** control-room effective limit, signed current/forecast inputs, WDT delivery and overlapping limits. **Use:** restore ratio and dynamic-security margin; show renewable MWh still dispatched down.

The project can show historical all-island context and calculate a what-if ratio from explicitly supplied inputs. The operator still needs the effective limit, contemporaneous transfer signs, validated battery treatment, live response and security results. [Operational Policy Roadmap](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf); [data feasibility audit](NETWORK_DATA_FEASIBILITY_2026-09-28.md).


