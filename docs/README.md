# Documentation guide

Start with the [repository README](../README.md) to run the API. Then use the pages below for the part you are changing.

The [project status](PROJECT_STATUS.md) records what was verified on 27 September and what remains before a judged demo.

| If you are working on… | Read |
| --- | --- |
| Data inputs, output files, or regeneration | [Data guide](DATA_GUIDE.md), [organiser sample profile](DATA_PROFILE.md), [EirGrid sources](EIRGRID_SOURCES.md) |
| Dispatch-down targets | [Label profile](DD_LABEL_PROFILE.md) |
| January grid context | [Workbook inventory](EIRGRID_UPLOADED_WORKBOOKS.md), [January context profile](EIRGRID_JAN2026_PROFILE.md) |
| Model features and evaluation | [Model plan](MODEL_PLAN.md), [real-label baseline](REAL_BASELINE.md), [project status](PROJECT_STATUS.md) |
| Team changes and event provenance | [Contribution guide](../CONTRIBUTING.md), [pre-existing work log](../PREEXISTING.md) |
| Local container and later Azure access | [Azure handoff](AZURE_HANDOFF.md) |
| Microsoft weather sources and limits | [Weather options](WEATHER_OPTIONS.md) |

The [data contract](../config/data_contract.yaml) lists field names and distinguishes forecast-safe inputs from same-period measurements. The API exposes historical samples and one retrospective model-to-optimiser scenario; see the [README](../README.md) for a request example.
