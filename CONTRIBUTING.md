# Working on Team Blue's repo

## Before changing code

1. Read the [README](README.md) and the relevant page in the [docs index](docs/README.md).
2. Run `python -m pytest -q` from the repository root in the Python 3.11 virtual environment.
3. Make a short-lived branch for a coherent change. Describe what changed, how you verified it, and any data or modelling caveat when sharing it for review.

Keep source CSVs, EirGrid workbooks, API responses, credentials, and virtual environments out of Git. `data/raw/` and `.env` are ignored. The processed datasets and baseline artifacts already tracked here are intentionally included for a working clone; if regenerating them, explain the source version and any changed row counts or metrics in the change description.

Use chronological evaluation for time-series models. Mark same-period measurements as nowcast inputs and avoid presenting the January holdout metrics as final forecast performance. The [model plan](docs/MODEL_PLAN.md) explains the feature boundary.

The [pre-existing work log](PREEXISTING.md) records the current baseline. Record the final pre-event commit and timestamp immediately before the hackathon starts; keep event-day work in later commits so the distinction is visible. No Git remote is configured yet, so this local repo is not shared until the team connects a private remote.
