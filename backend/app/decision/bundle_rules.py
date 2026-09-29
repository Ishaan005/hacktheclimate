"""Cheap deterministic compatibility checks before a network bundle solve."""

from __future__ import annotations

from typing import Any


def bundle_conflicts(candidates: list[dict[str, Any]]) -> list[str]:
    """Return explicit contract conflicts; do not infer electrical safety here."""
    ids = [str(candidate.get("action_id", "")).strip() for candidate in candidates]
    reasons: list[str] = []
    if any(not action_id for action_id in ids):
        reasons.append("Every bundled action needs an action_id")
    if len(ids) != len(set(ids)):
        reasons.append("The same action instance cannot appear twice")

    members = set(ids)
    for candidate in candidates:
        action_id = str(candidate.get("action_id", "")).strip()
        conflicts_with = {
            str(item) for item in candidate.get("conflicts_with", [])
            if str(item).strip()
        }
        conflict = sorted((members - {action_id}).intersection(conflicts_with))
        if conflict:
            reasons.append(
                f"{action_id} explicitly conflicts with {', '.join(conflict)}"
            )

    groups: dict[str, list[str]] = {}
    for candidate in candidates:
        group = str(candidate.get("exclusive_group", "")).strip()
        if group:
            groups.setdefault(group, []).append(str(candidate.get("action_id", "")))
    for group, action_ids in sorted(groups.items()):
        if len(action_ids) > 1:
            reasons.append(
                f"Actions {', '.join(sorted(action_ids))} share exclusive_group {group}"
            )

    # Multiple redispatch instructions touching the same generator would need a
    # joint setpoint/capability calculation. Reject that interaction rather than
    # double-counting one generator's headroom in the prototype optimizer.
    redispatch_assets: dict[str, str] = {}
    for candidate in candidates:
        family = str(candidate.get("contract_action_id") or "FLEX_LOAD")
        if family != "GENERATOR_REDISPATCH":
            continue
        action_id = str(candidate.get("action_id", ""))
        for field in ("source_asset_id", "replacement_asset_id"):
            asset_id = str(candidate.get(field, "")).strip()
            if not asset_id:
                continue
            prior = redispatch_assets.get(asset_id)
            if prior is not None and prior != action_id:
                reasons.append(
                    f"Redispatch actions {prior} and {action_id} share generator asset {asset_id}"
                )
            redispatch_assets[asset_id] = action_id
    return sorted(set(reasons))
