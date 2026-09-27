"""Make one manual Azure Maps Weather request and print a schema summary.

No response body or credential is written to disk. Requires AZURE_MAPS_KEY.
"""

import argparse
from datetime import datetime, timezone
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def nested(record, *keys):
    value = record
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lat", type=float, required=True, help="Latitude in degrees")
    parser.add_argument("--lon", type=float, required=True, help="Longitude in degrees")
    parser.add_argument("--duration", type=int, choices=(24, 72, 120, 240), default=24)
    args = parser.parse_args()
    if not -90 <= args.lat <= 90 or not -180 <= args.lon <= 180:
        parser.error("latitude or longitude is out of range")

    key = os.environ.get("AZURE_MAPS_KEY")
    if not key:
        parser.error("set AZURE_MAPS_KEY in your local shell before running")

    query = urlencode(
        {
            "api-version": "1.1",
            "query": f"{args.lat},{args.lon}",
            "duration": args.duration,
            "unit": "metric",
        }
    )
    request = Request(
        f"https://atlas.microsoft.com/weather/forecast/hourly/json?{query}",
        headers={"subscription-key": key},
    )
    try:
        with urlopen(request, timeout=30) as response:
            forecasts = json.load(response).get("forecasts", [])
            retrieved_at = datetime.now(timezone.utc).isoformat()
            headers = response.headers
    except HTTPError as exc:
        print(f"Azure Maps returned HTTP {exc.code}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, ValueError) as exc:
        print(f"Azure Maps request failed: {exc}", file=sys.stderr)
        return 1

    fields = {
        "wind_speed": ("wind", "speed", "value"),
        "wind_direction": ("wind", "direction", "degrees"),
        "wind_gust": ("windGust", "speed", "value"),
        "cloud_cover": ("cloudCover",),
        "temperature": ("temperature", "value"),
        "relative_humidity": ("relativeHumidity",),
        "precipitation_probability": ("precipitationProbability",),
    }
    summary = {
        "retrieved_at_utc": retrieved_at,
        "location": {"latitude": args.lat, "longitude": args.lon},
        "requested_hours": args.duration,
        "forecast_count": len(forecasts),
        "first_valid_time": nested(forecasts[0], "date") if forecasts else None,
        "last_valid_time": nested(forecasts[-1], "date") if forecasts else None,
        "field_counts": {
            name: sum(nested(forecast, *path) is not None for forecast in forecasts)
            for name, path in fields.items()
        },
        "wind_speed_units": sorted(
            {nested(forecast, "wind", "speed", "unit") for forecast in forecasts}
            - {None}
        ),
        "expires": headers.get("Expires"),
        "cache_control": headers.get("Cache-Control"),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
