# Weather options for the dispatch-down demo

Checked against Microsoft documentation and live Azure Maps responses on 27 September 2026. A Gen2 Maps account was created in the current Azure CLI subscription for this manual check. No app was deployed, no Aurora job was run, and the team has no retained forecast dataset yet.

## Recommendation

Use **Azure Maps Weather** as the first *live point-forecast feed* if the hackathon account permits it. Keep **Aurora 1.5** as a separate research experiment after the team has a supported initial-condition source and an approved Foundry budget. Neither feed can be used to claim a validated day-ahead dispatch-down model from the current January–August data.

| Option | Useful for this project | Main limit |
| --- | --- | --- |
| Azure Maps hourly forecast | Simple 24-hour forecasts for chosen Irish coordinates: wind speed/direction/gust, cloud cover, temperature, humidity, precipitation probability | Point forecasts; no documented forecast issue time or wind measurement height in the hourly response. Forecast history and retention rights need checking. |
| Aurora 1.5 on Microsoft Foundry | 0.25° gridded weather with hourly lead times, including 100 m wind components and radiation-related outputs | Needs a deployed Foundry endpoint, Blob Storage, and a large, correctly prepared global initial state; deployment cost and quota depend on the team's subscription. |

## Azure Maps Weather

The [hourly forecast API](https://learn.microsoft.com/en-us/rest/api/maps/weather/get-hourly-forecast?view=rest-maps-2026-01-01) uses `GET /weather/forecast/hourly/json` with a latitude/longitude, API version `1.1`, `unit=metric`, and a supported duration such as `24`. Its documented response has one `date` per forecast hour and nested weather values. Wind speed is returned in **km/h** for metric requests, so convert to m/s by dividing by 3.6. The response schema does **not document a model issue timestamp**; this is an inference from the published schema, not a claim about Microsoft's internal model cycle. Record the UTC retrieval time separately and never relabel it as the provider's issue time. The endpoint does not document hub-height wind or irradiance, so do not label those fields as such.

The [coverage table](https://learn.microsoft.com/en-us/azure/azure-maps/weather-coverage) lists Ireland under weather services. The one-request probe below prints a field-coverage summary without saving or printing the forecast body:

```bash
python scripts/probe_azure_maps_weather.py --lat 53.2707 --lon -9.0568 --duration 24
```

First set `AZURE_MAPS_KEY` using your shell's secret input or a managed secret store; never commit or paste the real key into a command or chat. Each run makes exactly **one** Weather request and has no retries. Do not put it into a scheduled job without a budget and usage tracking.

### Live check on 27 September 2026

Five successful requests were made in the current Azure CLI subscription: `duration=24` for Galway, Donegal, and Cork, `duration=120` for Galway, and one Galway `duration=24` smoke test of the probe script. Each returned exactly the requested number of hourly records. For every record, wind speed, direction, gust, cloud cover, temperature, relative humidity, and precipitation probability were present. Metric wind speed was `km/h`. The `date` values included the Irish `+01:00` offset. The responses had `Cache-Control: public` with an initial `max-age=1200` and `Expires` about 20 minutes after first retrieval; the repeated Galway request showed a lower remaining `max-age` from cache. The response had no provider issue-time field. This is schema and coverage evidence at these points, **not** a weather-accuracy or dispatch-down validation result.

The direct request count is **5 Weather requests** for this check, far below the published monthly allowance. Azure Monitor later reported `Usage` with `Count=5` for `ApiCategory=Weather` and `ApiName=Weather.GetHourlyForecast`. Use the metric's supported **Count** aggregation; its `Total` output is not the call count. Cost Analysis and the final bill have not been checked. No raw response was stored in the repository.

### Using weather in model training

The [weather training script](../scripts/train_weather_forecast.py) accepts a **separately approved, historical point-in-time forecast archive**. The five manual Maps responses were inspected in memory and are not that archive. They were retrieved in September 2026, while the included official dispatch-down labels end in August 2026, so there are **zero overlapping labeled rows**. Azure Maps' historical daily actuals are not past issued hourly forecasts and cannot repair this gap.

The training input is a CSV with one row per forecast version, valid hour, and location. Required columns are `provider`, `location_id`, `retrieved_at_utc`, `valid_time_utc`, and `wind_speed_mps`. Optional numeric columns are `wind_gust_mps`, `wind_direction_deg`, `cloud_cover_pct`, `temperature_c`, `relative_humidity_pct`, and `precipitation_probability_pct`. Times must be parseable as UTC or with an explicit offset. For Azure Maps, convert metric wind speed and gust from km/h to m/s by dividing by 3.6 and keep `retrieved_at_utc` distinct from the forecast's valid time. Do not invent a provider issue time.

For a 24-hour target, the script selects the latest weather row retrieved **at or before** each decision time (`target_time - 24h`), within a six-hour freshness limit. It maps both half-hour labels within one UTC hour to that hour's weather value. It trains a weather-and-calendar model only after at least 500 labeled rows align, with a chronological day-boundary holdout, and reports a calendar-only comparison on the same rows. It does not use same-period measured grid features. This is an initial experiment, not a claim that a single point predicts national curtailment.

After source rights and overlapping historical coverage are confirmed, run:

```bash
python scripts/train_weather_forecast.py \
  --weather-input data/raw/weather_forecasts_approved.csv \
  --location-id galway \
  --output-dir .cache/weather-model
```

The command does not call Azure or collect data. Keep any licensed archive in `data/raw/`, which is ignored by Git. Do not build a long-running Azure Maps forecast archive or train on Maps results until the team's agreement explicitly permits that use. [Microsoft's Azure Maps Product Terms](https://www.microsoft.com/licensing/terms/en-US/productoffering/MicrosoftAzureServices/MCA) restrict derived databases, combinations with other databases, and storage of API results; they do not clearly grant this training workflow.

Azure Maps' weather feed is sourced with [AccuWeather](https://learn.microsoft.com/en-us/azure/azure-maps/weather-services-faq). It is a hosted weather service, not an Aurora run. Microsoft says hourly forecasts update multiple times a day and may be cached for up to 30 minutes. The API documentation lists historical **daily actuals/normals/records**, not an archive of past issued hourly forecasts. Thus the repo cannot backfill a point-in-time 2026 forecast training set from this API alone. [Weather API index](https://learn.microsoft.com/en-us/rest/api/maps/weather/).

Cost guardrail: [Azure Maps pricing](https://azure.microsoft.com/en-us/pricing/details/azure-maps/) currently lists **1,000 free Weather transactions per month**, and [one Weather request counts as one transaction](https://learn.microsoft.com/en-us/azure/azure-maps/understanding-azure-maps-transactions). Four chosen coordinates queried every six hours for 30 days would be about **480 requests**; eight coordinates hourly would be about **5,760**. The free allowance can be shared with other uses, and pricing varies by subscription. Select future points from actual Irish wind/solar geography and confirm the team's subscription and usage before increasing cadence. The test account is **Gen2/G2**; check the tier and price again if the team uses another account.

**Storage/rights gate:** Microsoft's current [Azure Maps Product Terms](https://www.microsoft.com/licensing/terms/productoffering/MicrosoftAzure/MCA) restrict caching/storage of API results, derived databases, and some derivative uses. Those terms do not give us a clear right to retain a long-running forecast archive or use the results to train a new model. Confirm the team's agreement or obtain explicit permission before making Azure Maps data part of a training dataset. A temporary operational display and a training archive are different uses; do not assume one authorizes the other.

## Aurora weather models

Microsoft's [Aurora 1.5 model documentation](https://microsoft.github.io/aurora/models.html) describes a deterministic 0.25° forecast and an ensemble variant. It supports hourly lead-time outputs and includes 100 m wind components, which are more relevant to wind generation than an unspecified-height point wind. That does not establish accuracy for Ireland's local network constraints or for this dispatch-down target.

The [Foundry workflow](https://microsoft.github.io/aurora/foundry/submission.html) requires an Aurora endpoint plus a Blob Storage channel with a read/write SAS token. Aurora 1.5 needs **18 surface inputs plus insolation, 36 static fields, and five atmospheric fields at 13 pressure levels**. Microsoft's [worked example](https://microsoft.github.io/aurora/foundry/demo_v1p5.html) builds a historical state from ERA5, and explicitly says ERA5 is illustrative because the model is fine-tuned on IFS data. The catalog lists [Aurora as Preview](https://ai.azure.com/catalog/models/Aurora?publisher=microsoft); region, quota, deployment type, price, and permitted use must be checked in the team's actual Foundry project. Do not create an endpoint just to discover whether the data pipeline is feasible.

## Provider-neutral handoff

When a source and its retention rights are confirmed, normalize the permitted output into a table with these fields before joining to the dispatch-down model:

| Field | Meaning |
| --- | --- |
| `provider`, `location_id`, `latitude`, `longitude` | Source and point/grid-cell identity |
| `retrieved_at_utc` | When our system received this forecast |
| `provider_issue_time_utc` | Actual provider cycle/issue time, **null if unavailable** |
| `valid_time_utc` | Hour represented by the forecast |
| `wind_speed_mps`, `wind_direction_deg`, `wind_height_m` | Wind values and documented height; height null for Azure Maps hourly |
| `wind_gust_mps`, `cloud_cover_pct`, `temperature_c`, `precipitation_probability_pct` | Optional provider values with explicit units |

For evaluation, only join forecasts that were already received before the decision time. Preserve the original provider and unit metadata. Both sources can produce hourly weather while the dispatch-down target is half-hourly; define and record a mapping to each target interval without implying that the weather source has 30-minute precision. Do not train on the existing same-period measured grid state while calling the result day-ahead. The [model plan](MODEL_PLAN.md) describes the other forecast-safe inputs.

## Next checks when team access arrives

1. Confirm the team's subscription, account tier, Weather API usage budget, and whether forecast retention/training is allowed. Keep credentials out of the repo. Monitor `Usage` with the `Count` aggregation and Weather dimensions in the team's account.
2. Select a small set of representative wind and solar locations, then set a request cadence within the free allowance. Use the probe script for a manual schema check in the team's account. Keep any operational use separate from a forecast training archive until retention rights are settled.
3. If Aurora is offered, identify its Foundry deployment cost/quota and a compatible real-time initial-condition source **before** submitting a job. Time-box one historical example only if the budget allows it.
4. Compare weather-derived features against a forecast-safe calendar/lag baseline on later labeled data. Keep the weather feed and dispatch-down model separate from the retrospective 1-hour demo until that check passes.
