# Operator scenario scope — hackathon MVP

**Status:** Locked scenario catalogue, 29 September 2026. This is the complete set of scenario **types we are tracking**. The team will define actions separately.

## The three families

- **Transmission Constraint (T1–T4):** A line, cable or transformer is carrying too much power now, or would carry too much if another piece of equipment failed.
- **High Frequency / Minimum Generation (H1–H4):** There is a measured high-frequency event, or an operating requirement keeps conventional generation or response capability available.
- **SNSP:** The all-island limit on the share of non-synchronous power is reached or would be reached. This remains **one case**.

The T and H codes are **our labels**, not separate EirGrid dispatch-down reason codes. EirGrid publishes a single High Frequency / Minimum Generation reason, and its public totals do not break either family down into the rows below. This matrix defines what our product recognises; it does not claim a historical count for each row. [EirGrid's 2025 dispatch-down reason codes](https://cms.eirgrid.ie/sites/default/files/publications/Annual-Renewable-Constraint-and-Curtailment-Report-2025-V1.0.pdf).

## 1. Transmission Constraint: complete tracked matrix

**First determine the network condition.** “Normal flow” means the flow with equipment in its *current* state. “After another failure” means the calculated flow if one more line, cable or transformer trips. The four combinations are:

| Case | Equipment already out? | Normal flow on remaining equipment | Flow after one more credible failure | Scenario |
| --- | --- | --- | --- | --- |
| **T1 — Intact overload** | No | At or beyond the allowed limit | A further failure is not needed to explain the problem | The full network is available, but a line or transformer cannot carry the present or expected flow. |
| **T2 — Intact single-failure risk** | No | Within limits | Beyond an allowed limit | The full network works now, but one credible trip would overload what remains. |
| **T3 — Outage overload** | Yes, planned or forced | At or beyond the allowed limit | A further failure is not needed to explain the problem | With one item already out, the remaining network cannot carry the present or expected flow. |
| **T4 — Outage plus failure risk** | Yes, planned or forced | Within limits | Beyond an allowed limit | With one item already out, one further credible trip would overload what remains. |

**Then record the reach of the bottleneck.** Each T case can take any of the three forms below. This makes **12 tracked T situations** without inventing 12 different safety rules.

| Case | One local generating area | Several areas sharing a route | Wide affected renewable group |
| --- | --- | --- | --- |
| **T1** | The area's working export line or transformer reaches its limit. | A shared working corridor reaches its limit as output from several areas combines. | A transmission route with a wide affected group reaches its limit while all equipment is available. |
| **T2** | The area is safe now; losing one working route would overload its backup. | Several areas depend on a shared route that would overload after one trip. | One trip would overload a route whose constraint group reaches across a wide area. |
| **T3** | An outage leaves the area's remaining route at its limit now. | An outage diverts several areas' power onto a shared route that reaches its limit. | An outage makes a route serving a wide affected group reach its limit now. |
| **T4** | One local route is out; losing another would overload what remains. | One shared route is out; a further trip would overload the remaining corridor. | One item is out; a further trip would overload a route with a wide affected group. |

For **every** cell above, record these additional facts; they describe the situation without creating another case:

- **What is limited:** line or cable flow, or transformer flow.
- **What changed:** renewable output, demand, interconnector transfer, network switching, or an equipment outage.
- **If equipment is out:** planned work or an unexpected fault, plus the expected return time.
- **When it matters:** happening now or forecast for a stated time window.
- **Where it matters:** the named limiting equipment and the renewable units or groups whose output affects it.

A wide *affected group* is still a transmission case if a particular network route is the bottleneck. EirGrid documents local and wide constraint groups, and tests intact flow, one failure, and both normal flow and one more failure during an outage. We are tracking **power-flow overloads only**; transmission-line voltage is outside this scope. [EirGrid's Wind Dispatch Tool constraint-group overview](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf).

## 2. High Frequency / Minimum Generation: complete tracked matrix

This family has **four causes**. The rows under each cause show every situation type we are tracking. All four concern the power system as a whole; a named unit or interconnector can be the source of the problem without making it a local transmission constraint.

| Case | Tracked situation | What makes this the case |
| --- | --- | --- |
| **H1 — Active high frequency** | An interconnector that was exporting power stops taking it. | Supply exceeds use after the lost export, and measured frequency rises beyond the permitted high range. |
| **H1** | Demand drops unexpectedly while supply stays high. | The sudden surplus produces measured high frequency. |
| **H1** | Generation or imports rise faster than expected while demand and exports do not keep up. | The resulting surplus produces measured high frequency. |
| **H2 — Minimum conventional generation** | Required conventional units must remain online in Ireland. | Their lowest permitted output uses room that could otherwise take renewable power. |
| **H2** | Required conventional units must remain online in Northern Ireland. | The same minimum-unit rule binds in that jurisdiction. |
| **H2** | Minimum-unit requirements bind in both jurisdictions at once. | Both requirements have to be met, even during low demand and high renewable output. |
| **H3 — Reserve requirement** | Upward reserve is needed for a sudden loss of supply or increase in demand. | Qualified capacity must be ready to increase output or reduce consumption; retaining a conventional unit is the confirmed limiting reason. |
| **H3** | Downward reserve is needed for a sudden surplus. | Qualified capacity must be ready to reduce output or increase consumption; count this row only if the policy effective for the event requires it and it is the confirmed limiting reason. |
| **H4 — Ramping requirement** | Power needs to rise over the coming hours. | Demand may increase, wind or solar may fall, or an import may drop; enough qualified capability must be able to increase supply in time. |
| **H4** | Power needs to fall over the coming hours. | Demand may decrease, wind or solar may rise, or an export may drop; enough qualified capability must be able to reduce supply in time. |

**Case boundaries and fields:**

- **H1 requires measured high frequency.** A forecast surplus or low demand with normal frequency belongs in intake until its actual limiting requirement is known.
- **H2 is about the minimum number of qualified units and the output they cannot reduce below.** Record the rule in force, the count and location of online units, and their minimum outputs.
- **H3 is about capacity held ready for a sudden event.** Record the reserve direction, requirement, qualified available capacity, and the event it covers.
- **H4 is about the speed and size of a coming change.** Record whether power must rise or fall, the forecast, and the required capability over the relevant one-, three- or eight-hour window.
- **H2–H4 can coincide.** Record each confirmed limiting requirement. The mere presence of an online conventional unit does not prove which one caused dispatch-down.

EirGrid groups emergency high frequency and minimum conventional generation for reserve, priority dispatch and ramping under one published reason. Its policy roadmap describes minimum-unit, reserve and ramping requirements separately. The applicable limits and eligible resources must come from the policy effective for the event, rather than a fixed number copied from an older report. [EirGrid's 2025 dispatch-down report](https://cms.eirgrid.ie/sites/default/files/publications/Annual-Renewable-Constraint-and-Curtailment-Report-2025-V1.0.pdf) · [EirGrid and SONI's Operational Policy Roadmap](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf).

## 3. SNSP: one case, all tracked ways it can arise

**SNSP** is an all-island percentage based on non-synchronous generation, including wind and solar, and net interconnector transfers, relative to demand and net exports. We track **one SNSP-limit case**. Any of these changes can move the percentage toward its effective limit:

| Change to track | Why it can bring SNSP to the limit |
| --- | --- |
| Wind or solar output rises | More non-synchronous power is counted. |
| Demand falls | The same non-synchronous output becomes a larger share of the power the island is using. |
| Net interconnector imports rise | More imported power is counted in the SNSP calculation. |
| Net interconnector exports fall | The ratio can rise as the transfer pattern changes. |

- Record the current or forecast ratio, the limit effective at that time, and the generation, demand and interconnector values used to calculate it.
- “At the limit now” and “forecast to reach it” describe **timing**, not separate SNSP cases.
- If a transmission or H-family requirement also binds, record it alongside SNSP. [EirGrid and SONI's SNSP definition](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf).

## Rules for using the matrix

- Assign **all applicable labels** when limits overlap. A local outage overload can be **T3** while the all-island SNSP limit also applies.
- If the limiting cause is missing, use **“cause unknown”** and ask for the missing facts. It is an intake state, not another scenario.
- A change in location, affected group, asset name, or forecast time changes the **details of a case**. It does not create a new T, H or SNSP label.

## Terms in plain English

- **Conventional unit:** A qualified generator, commonly a large synchronous machine, that may have to stay connected under an operating rule.
- **Frequency:** A live measure of the balance between electricity supply and use. Its normal target is **50 Hz**.
- **N-1 / N-1-1:** Check the grid after **one failure**, or after **one existing outage plus one further failure**.
- **Outage:** A line, cable or transformer is unavailable for planned work or because it has failed.
- **Reserve:** Capacity ready to respond to a sudden change.
- **Ramping:** The ability to change power output or consumption over a stated time.
- **SNSP:** *System Non-Synchronous Penetration*. An all-island percentage; it is not simply the percentage of wind power.
