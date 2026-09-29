# Documentation guide

Start with the [repository README](../README.md) to run the API. Then use the pages below for the part you are changing.

The [project status](PROJECT_STATUS.md) is a 27 September verification snapshot. For newer GFS training and inference work, use the dedicated guides below.

| If you are working on… | Read |
| --- | --- |
| Data inputs, output files, or regeneration | [Data guide](DATA_GUIDE.md), [organiser sample profile](DATA_PROFILE.md), [EirGrid sources](EIRGRID_SOURCES.md) |
| Dispatch-down targets | [Label profile](DD_LABEL_PROFILE.md) |
| January grid context | [Workbook inventory](EIRGRID_UPLOADED_WORKBOOKS.md), [January context profile](EIRGRID_JAN2026_PROFILE.md) |
| Model features and evaluation | [Model plan](MODEL_PLAN.md), [real-label baseline](REAL_BASELINE.md), [project status](PROJECT_STATUS.md) |
| Forecast-safe national constraint training | [Archived GFS model and backtest](GFS_CONSTRAINT_TRAINING.md) |
| Forward model freeze and curtailment decision | [GFS model readiness](GFS_MODEL_READINESS.md) |
| Daily national constraint inference | [Checked GFS inference and API](GFS_INFERENCE.md) |
| Team changes and event provenance | [Contribution guide](../CONTRIBUTING.md), [pre-existing work log](../PREEXISTING.md) |
| Local container and later Azure access | [Azure handoff](AZURE_HANDOFF.md) |
| Microsoft weather sources and limits | [Weather options](WEATHER_OPTIONS.md) |
| Local Aurora forecasts and Irish turbine inventory | [Aurora and turbine data audit](AURORA_TURBINE_DATA_AUDIT.md) |
| Network-aware forecast inputs and downloaded public datasets | [Network data feasibility study](NETWORK_DATA_FEASIBILITY_2026-09-28.md) |
| TYTFS case import and base DC validation | [TYTFS base case](TYTFS_BASE_CASE.md) |
| Static grid import and selected outage scenario | [Cashla–Flagford planning scenario](NETWORK_SCENARIO_DEMO.md) |
| Planned-outage reconciliation and one TYTFS scenario switch | [2026 outage audit](NETWORK_OUTAGE_RECONCILIATION_2026-09-28.md) |
| ECP project-to-bus review and scenario allocations | [Network generator crosswalk](NETWORK_GENERATOR_CROSSWALK.md) |
| 48 half-hour network forecast adapter and API | [Network forecast architecture](NETWORK_FORECAST_ARCHITECTURE.md) |
| Safety checks, controlled action scenarios and operator API | [Network safety and actions](NETWORK_SAFETY_ACTIONS.md) |
| Decision-time evidence, versioned policy, past cases and current-plan baseline | [Advisory decision backend](DECISION_BACKEND.md) |
| Combined case intake, action simulations and output inspection | [Operator case evaluation](OPERATOR_EVALUATION.md) |
| Self-contained teammate presentation | [Golden-path demo](DEMO.md) |
| Read-only case preview and pending scenario/action handoff | [Case-flow handoff](DECISION_HANDOFF.md) |
| Issue #61 operator workspace contract | [Workspace backend handoff](WORKSPACE_BRIEF_API.md) |

The [data contract](../config/data_contract.yaml) distinguishes forecast-safe inputs from same-period measurements. The [README](../README.md) lists current API paths.
