# Third-party dependencies

Versions are pinned in `requirements.txt`.

| Package | Version | License (project-reported) | Use |
|---|---:|---|---|
| pandas | 2.2.3 | BSD-3-Clause | tabular ingestion/transforms |
| numpy | 2.3.5 | BSD-3-Clause | numeric operations |
| scikit-learn | 1.8.0 | BSD-3-Clause | baseline ML |
| scipy | 1.17.0 | BSD-3-Clause | linear optimisation |
| FastAPI | 0.128.2 | MIT | API |
| Uvicorn | 0.48.0 | BSD-3-Clause | ASGI server |
| Pydantic | 2.13.4 | MIT | validation/models |
| PyYAML | 6.0.3 | MIT | config |
| pytest | 9.0.2 | MIT | tests |

Before submission, verify licences against the installed package metadata and record any frontend/cloud dependencies as well.

## Added for EirGrid enrichment

- requests 2.32.5 — Apache-2.0 — HTTP retrieval of public EirGrid feeds
- openpyxl 3.1.5 — MIT — reading public EirGrid XLSX reports through pandas
