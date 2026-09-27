from __future__ import annotations

import argparse

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Check a locally or remotely hosted Hack the Climate API.")
    parser.add_argument("base_url", help="For example http://127.0.0.1:8000 or https://your-app.example")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    health = requests.get(f"{base_url}/health", timeout=20)
    health.raise_for_status()
    if health.json().get("canonical_data_exists") is not True:
        raise SystemExit("Health route is up, but canonical data is missing")

    payload = {
        "start_target": "2026-01-24T00:00:00Z",
        "intervals": 4,
        "assets": [
            {
                "name": "flexible_load",
                "max_power_mw": 10,
                "energy_required_mwh": 8,
                "available": [True, False, True, True],
            }
        ],
    }
    response = requests.post(f"{base_url}/v1/demo/absorption", json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    if result.get("scenario") != "retrospective_1h_operational" or len(result.get("intervals", [])) != 4:
        raise SystemExit("Demo response does not match the expected retrospective contract")
    print(f"API ready: {base_url}")
    print(f"Demo scheduled {result['schedule']['absorbed_mwh']:.2f} MWh in the historical scenario")


if __name__ == "__main__":
    main()
