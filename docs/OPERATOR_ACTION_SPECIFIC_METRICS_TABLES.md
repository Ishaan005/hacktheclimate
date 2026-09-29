# Action-specific safety metrics for MVP actions

These are the additional safety checks for actions in [What the operator sees, and what we could suggest](OPERATOR_ACTIONS_AND_METRICS.md). The **first bold measure** in each row is the go/no-go result to show first. Apply the [general family safety metrics](OPERATOR_GENERAL_SAFETY_METRICS.md) to the full action combination as well.

## Transmission Constraint

| Action | Specific safety metrics to show |
| --- | --- |
| Paired cross-area generator redispatch | **Matched MW delivered over time:** reduction and replacement MW at each step; each unit’s available range and ramp; any interim supply–demand or reserve gap. [Balancing principles, §§3.2, 4.4](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf). |
| Switching or sectionalising | **Switching clearance for the exact configuration:** breaker state, authorised sequence, protection and fault-current suitability, and unintended islanding check. [Operating Security Standards, §5](https://cms.eirgrid.ie/sites/default/files/publications/Operating-Security-Standards-Version-3.0-April-2025.pdf). |
| Early return of out-of-service equipment or deferment of work | **Released-to-energise status:** fault/work clearance, required fitness and switching permissions, and earliest approved return time. [EirGrid outage process](https://www.eirgrid.ie/industry/customer-information/outage-information). |
| Local storage charging or contracted extra demand | **Relief that persists:** metered MW at the relevant connection, usable charging energy or agreed load duration, connection after the studied trip, and rebound time. [Balancing principles, battery dispatch](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [DSU description](https://www.eirgrid.ie/grid/grid-codes-and-compliance-overview/grid-code-compliance-testing/dsu-setup-and-testing). |
| Local, shared, wide or outage-specific WDT limit, including a pre-limit | **Incremental MW actually delivered:** selected group and members, existing setpoints, new unit setpoints, measured output and response time. WDT allocation accounts for group selection and frequency response. [WDT method, Appendix 1](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf). |
| Interconnector transfer change | **Accepted, deliverable transfer:** link status, signed MW direction, remaining capacity, permitted ramp, delivery time and other TSO agreement. [Balancing principles, §3.4.6](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf). |

## High Frequency / Minimum Generation

| Action | Specific safety metrics to show |
| --- | --- |
| Fast generator reduction, storage charging or pumping during high frequency | **Available MW within the required seconds:** activation delay, actual ramp, generator minimum output or storage charge headroom; then observed MW response. [2024 frequency-control agreement, Art. 5](https://cms.eirgrid.ie/sites/default/files/publications/LFCBOA%20-Load-Frequency-Control-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland.pdf). |
| Emergency HVDC assistance after lost export | **An available, approved response in the high-frequency/export direction:** identify the failed link, verify another link’s headroom and armed mode, agreed MW, response time and return-to-schedule. The cited agreement’s described low-frequency response does not itself establish this direction. [2024 agreement, Art. 17](https://cms.eirgrid.ie/sites/default/files/publications/LFCBOA%20-Load-Frequency-Control-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland.pdf). |
| Lower-minimum conventional-unit swap | **Qualified coverage throughout the swap:** incoming unit synchronisation and service-ready time versus outgoing unit departure; minimum qualified count and inertia at every intermediate step. [Operational Policy Roadmap](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf). |
| Replace upward or downward reserve with another provider | **Credited response for the exact service:** qualification and declared/awarded MW by direction and response tranche, activation speed, sustain time, energy or state of charge, and MW already committed elsewhere. [Balancing principles, §3.2.1](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf); [2024 agreement, Art. 4](https://cms.eirgrid.ie/sites/default/files/publications/LFCBOA%20-Load-Frequency-Control-Block-Operational-Agreement-for-Ireland-and-Northern-Ireland.pdf). |
| Commit an offline unit, storage or demand reduction for an upward ramp | **Named resource’s deliverable trajectory:** start after notice, MW reached by each applicable one-, three- or eight-hour deadline, and MW sustained for that product’s hold period. [Ramping-margin requirements](https://www.sem-o.com/sites/semo/files/documents/general-publications/Ramping_Margin_Requirements_in_Scheduling.pdf). |
| Charge a battery while retaining its frequency service | **Remaining response capability after charging:** state of charge, MWh to full, charging MW, upward/downward response headroom and energy reserved for existing service commitments. [Balancing principles, §4.4.5](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf). |

## SNSP

| Action | Specific safety metrics to show |
| --- | --- |
| Lower imports or increase exports | **Accepted signed transfer and delivery time**, as above, followed by SNSP recalculated at delivery and return-to-schedule. [Balancing principles, §3.4.6](https://cms.eirgrid.ie/sites/default/files/publications/Balancing_Market_Principles_Statement_Version_9.0.pdf). |
| Charge storage, pump or add contracted demand while allowing more renewable output | **Paired change in the SNSP numerator and denominator:** added demand, renewable MW released, signed transfer changes, charge duration and rebound. Recalculate the *whole* ratio; added load MW alone does not establish relief. [Operational Policy Roadmap, SNSP definition](https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-SONI-Operational-Policy-Roadmap-2025-2035.pdf). |
| All-island WDT renewable limit | **Correct all-island set and delivered incremental MW**, accounting for existing local limits; then recalculate SNSP from measured output. [WDT method, Appendix 1](https://cms.eirgrid.ie/sites/default/files/publications/Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf). |

Every listed action also needs the relevant general family safety checks to pass for the **whole combination**, using the current operating plan and instructions already in force as the baseline.
