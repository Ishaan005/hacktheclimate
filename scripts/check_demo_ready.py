"""Preflight the backend-owned golden-path demo from a fresh clone."""

from __future__ import annotations

from backend.app.demo_cases import evaluate_west_outage_demo


def _case(text: str) -> dict:
    return {
        "id": "demo-preflight",
        "originalText": text,
        "createdAt": "demo",
        "scenarios": ["local_network_constraint", "planned_outage_exposure"],
        "facts": {
            "event_window": {"value": "next 2 hours"},
            "affected_area": {"value": "West"},
        },
        "proposedAction": None,
        "comparison": None,
    }


def main() -> None:
    hero = evaluate_west_outage_demo(
        _case(
            "Planned outage in the west is causing a line overload. "
            "High wind around Ballylickey is constrained for the next 2 hours."
        ),
        ["T3"],
    )
    refusal = evaluate_west_outage_demo(
        _case(
            "Planned outage in the west near Ballylickey plus another credible circuit loss "
            "creates an N-1 overload for the next 2 hours."
        ),
        ["T4"],
    )

    checks = [
        ("synthetic demo network solved", hero["binding"] is not None),
        ("T3 modeled candidate produced", hero["action"] is not None),
        ("T3 baseline is a thermal breach", hero["binding"]["status"] == "breach"),
        ("T3 post-action screen clears", hero["postAction"]["securityResult"] == "within_modelled_limit"),
        ("T3 modeled 20 MWh capture shown", hero["postAction"]["dispatchDownWasteMwh"] == 20.0),
        ("T4 further-contingency refusal works", refusal["action"] is None),
    ]
    failed = [label for label, passed in checks if not passed]
    for label, passed in checks:
        print(("✓" if passed else "✗") + " " + label)
    if failed:
        raise SystemExit("DEMO NOT READY: " + ", ".join(failed))
    print("\nDEMO READY")


if __name__ == "__main__":
    main()
