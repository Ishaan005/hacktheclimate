# Checked national constraint inference

The saved [GFS constraint model](GFS_CONSTRAINT_TRAINING.md) has a batch inference path and a read-only API route. The model combines an event classifier, positive-event MWh regressor, and probability calibration. It emits national `constraint_mwh` probability, expected MWh and historical-residual ranges for each half-hour from 06:30 UTC to 06:00 the next day. This is an **experimental forecast**: August expected-MWh error was 17.39 MWh versus 15.01 MWh for a zero forecast. It is not connected to the safety or action optimiser.

The [model readiness report](GFS_MODEL_READINESS.md) freezes this as the canonical forward path. The separately evaluated GFS curtailment artifact does not pass its volume gate, so this route does not serve curtailment or total dispatch-down.

## Daily run

From the repository root in the Python 3.11 environment:

```bash
python -m scripts.run_gfs_constraint_inference
```

Run after **06:00 UTC**, preferably near **06:15 UTC**. The command selects that day's 00Z GFS issue, or the preceding day before 06:00. It fetches the five pinned Irish points from the [dynamical.org NOAA GFS point API](https://dynamical.org/api/), checks all 25 NOAA S3 GRIB forecast-hour objects used by the model, verifies the point grid cells and units against training, and scores the saved model. It refuses a source file recorded after the 06:00 decision, incomplete leads, changed features, expired issue, or malformed output. It preserves the exact source and model hashes in the result.

Set `GFS_FORECAST_DIR` to a directory shared by the scheduled job and API process. The default is ignored `data/inference/gfs_constraint/`. Each successful run writes an immutable `runs/*.json` record and atomically replaces `latest.json`. A failure exits nonzero and leaves the previous result intact; the API stops serving that result when its forecast window ends. Keep the output directory on persistent storage if job and API run in separate containers.

The job can be called by a UTC scheduler at 06:15. Retry a failed run before 06:30 if the source API is late; do not treat a missing result as a zero forecast. Both the job exit status and API 503 response should alert the operator. The historical minimum NOAA source margin was only 4 minutes 50 seconds, and the point API has its own ingestion timing. The pipeline does not establish a live feed SLA.

For a pinned issue or separate output directory:

```bash
python -m scripts.run_gfs_constraint_inference \
  --issue-date 2026-09-28 --output-dir /path/to/shared/forecast-output
```

`--issue-date` must be the current 06:00-to-next-06:00 forecast window. The raw API response and HEAD checks are cached under ignored `data/raw/` for reproducibility and retries; no global GRIB files or credentials are needed.

## Read the forecast

With the API running, `GET /v1/forecast/constraint` reads the latest checked result without making external requests or loading the model. It returns only target half-hours strictly after the request time, along with source snapshot, source timestamps, model hash, generation time, calendar-reference predictions, and the experimental limitations. It returns **503** when no valid current result exists. It does not fabricate demand, generation, regional constraints, curtailment, or a network action.

```bash
curl -sS http://127.0.0.1:8000/v1/forecast/constraint
```

The separate `/v1/network/forecast` route still requires forecast demand, regional renewable generation, a reviewed generator crosswalk and a planning case. National constraint probability and MWh alone cannot satisfy that network input contract. The January demo and older grid-lag artifacts remain retrospective or availability-uncertain and are not served as live models.

## Evidence and maintenance

- `source.noaa_last_required_object_at_utc` is the latest S3 `Last-Modified` of all 25 used leads. The API response has a distinct `api_retrieved_at_utc` and `api_response_sha256`.
- `model.artifact_sha256` and `training_source_versions` identify the exact saved fit; the job checks those versions against the training report.
- `forecasts` always has 48 contiguous half-hours in the stored run. The API filters elapsed intervals at request time and returns `remaining_intervals`.
- Recalibration or promotion requires a later chronological holdout and live shadow measurements. The current August failure remains visible in every response.

The source route follows the point API's documented distinction between pinned `initTime`, forecast `validTimes`, and immutable `snapshotId`. [NOAA GFS data processed by dynamical.org](https://dynamical.org/catalog/noaa-gfs-forecast/) is credited under CC BY 4.0.
