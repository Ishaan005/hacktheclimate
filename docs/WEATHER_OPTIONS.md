# Weather options for the dispatch-down demo

Checked against Microsoft documentation on 27 September 2026. No Azure Maps request, Aurora job, account, or paid resource was created for this review. The team has no weather sample yet.

## Recommendation

Use **Azure Maps Weather** as the first *live point-forecast feed* if the hackathon account permits it. Keep **Aurora 1.5** as a separate research experiment after the team has a supported initial-condition source and an approved Foundry budget. Neither feed can be used to claim a validated day-ahead dispatch-down model from the current January–August data.

| Option | Useful for this project | Main limit |
| --- | --- | --- |
| Azure Maps hourly forecast | Simple 24-hour forecasts for chosen Irish coordinates: wind speed/direction/gust, cloud cover, temperature, humidity, precipitation probability | Point forecasts; no documented forecast issue time or wind measurement height in the hourly response. Forecast history and retention rights need checking. |
| Aurora 1.5 on Microsoft Foundry | 0.25° gridded weather with hourly lead times, including 100 m wind components and radiation-related outputs | Needs a deployed Foundry endpoint, Blob Storage, and a large, correctly prepared global initial state; deployment cost and quota depend on the team's subscription. |

## Azure Maps Weather

The [hourly forecast API](https://learn.microsoft.com/en-us/rest/api/maps/weather/get-hourly-forecast?view=rest-maps-2026-01-01) uses `GET /weather/forecast/hourly/json` with a latitude/longitude, API version `1.1`, `unit=metric`, and a supported duration such as `24`. Its documented response has one `date` per forecast hour and nested weather values. Wind speed is returned in **km/h** for metric requests, so convert to m/s by dividing by 3.6. The response schema does **not document a model issue timestamp**; this is an inference from the published schema, not a claim about Microsoft's internal model cycle. Record the UTC retrieval time separately and never relabel it as the provider's issue time. The endpoint does not document hub-height wind or irradiance, so do not label those fields as such.

The [coverage table](https://learn.microsoft.com/en-us/azure/azure-maps/weather-coverage) lists Ireland under weather services, but the actual response at each selected coordinate still needs checking. Once account access and the usage budget are confirmed, one manual request would be:

```bash
curl --get 'https://atlas.microsoft.com/weather/forecast/hourly/json' \
  -H "subscription-key: $AZURE_MAPS_KEY" \
  --data-urlencode 'api-version=1.1' \
  --data-urlencode 'query=53.35,-6.26' \
  --data-urlencode 'duration=24' \
  --data-urlencode 'unit=metric'
```

Set `AZURE_MAPS_KEY` only in the local shell or a managed secret store. This example was **not run** and should not be put into a scheduled job without a budget.

Azure Maps' weather feed is sourced with [AccuWeather](https://learn.microsoft.com/en-us/azure/azure-maps/weather-services-faq). It is a hosted weather service, not an Aurora run. Microsoft says hourly forecasts update multiple times a day and may be cached for up to 30 minutes. The API documentation lists historical **daily actuals/normals/records**, not an archive of past issued hourly forecasts. Thus the repo cannot backfill a point-in-time 2026 forecast training set from this API alone. [Weather API index](https://learn.microsoft.com/en-us/rest/api/maps/weather/).

Cost guardrail: [Azure Maps pricing](https://azure.microsoft.com/en-us/pricing/details/azure-maps/) currently lists **1,000 free Weather transactions per month**, and [one Weather request counts as one transaction](https://learn.microsoft.com/en-us/azure/azure-maps/understanding-azure-maps-transactions). Four chosen coordinates queried every six hours for 30 days would be about **480 requests**; eight coordinates hourly would be about **5,760**. The free allowance can be shared with other uses, and pricing varies by subscription. Start with one coordinate and one manual call after access is granted; select later points from actual Irish wind/solar geography rather than querying only Dublin. Gen1 Azure Maps pricing retired on [15 September 2026](https://learn.microsoft.com/en-au/lifecycle/end-of-support/end-of-support-2026); check the account's current tier and price before calling.

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

For evaluation, only join forecasts that were already received before the decision time. Preserve the original provider and unit metadata. Do not train on the existing same-period measured grid state while calling the result day-ahead. The [model plan](MODEL_PLAN.md) describes the other forecast-safe inputs.

## First checks when access arrives

1. Confirm the approved subscription, account tier, Weather API usage budget, source terms, and whether forecast retention/training is allowed. Keep credentials out of the repo.
2. If Maps is allowed, make **one** manual `duration=24&unit=metric` request for one representative Irish coordinate. Inspect the real payload, HTTP `Expires` header, region coverage, and transaction meter. Then choose a small set of locations and cadence within the budget.
3. If Aurora is offered, identify its Foundry deployment cost/quota and a compatible real-time initial-condition source **before** submitting a job. Time-box one historical example only if the budget allows it.
4. Compare weather-derived features against a forecast-safe calendar/lag baseline on later labeled data. Keep the weather feed and dispatch-down model separate from the retrospective 1-hour demo until that check passes.
