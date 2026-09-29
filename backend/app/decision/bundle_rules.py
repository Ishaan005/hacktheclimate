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
    return sorted(set(reasons))
