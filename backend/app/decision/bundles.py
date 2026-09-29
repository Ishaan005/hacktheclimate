"""Action-bundle contracts and deterministic combination generation."""

from __future__ import annotations

from itertools import combinations
from typing import Any

from pydantic import Field, model_validator

from .contracts import Contract
from .bundle_rules import bundle_conflicts

MAX_BUNDLE_SIZE = 3


class ActionBundle(Contract):
    bundle_id: str
    action_instance_ids: list[str]
    contract_action_ids: list[str]
    is_baseline: bool = False

    @model_validator(mode="after")
    def valid_bundle(self):
        if not self.bundle_id.strip():
            raise ValueError("bundle ID must be nonempty")
        if self.is_baseline:
            if self.action_instance_ids or self.contract_action_ids:
                raise ValueError("baseline bundle cannot contain actions")
        elif not self.action_instance_ids:
            raise ValueError("non-baseline bundle needs at least one action")
        if len(self.action_instance_ids) != len(set(self.action_instance_ids)):
            raise ValueError("bundle action instance IDs must be unique")
        if len(self.action_instance_ids) != len(self.contract_action_ids):
            raise ValueError("bundle instance and contract action lists must align")
        return self


class BundleGeneration(Contract):
    bundles: list[ActionBundle] = Field(min_length=1)
    rejected: list[dict[str, Any]] = Field(default_factory=list)


def _family(candidate: dict[str, Any]) -> str:
    return str(candidate.get("contract_action_id") or "FLEX_LOAD")


def generate_action_bundles(
    candidates: list[dict[str, Any]],
    *,
    max_bundle_size: int = MAX_BUNDLE_SIZE,
) -> BundleGeneration:
    """Generate deterministic compatible bundles plus the no-new-action baseline."""
    if max_bundle_size < 1:
        raise ValueError("max bundle size must be at least one")
    ids = [str(candidate.get("action_id", "")).strip() for candidate in candidates]
    if any(not action_id for action_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("candidate action IDs must be nonempty and unique")

    ordered = sorted(candidates, key=lambda item: str(item["action_id"]))
    bundles = [ActionBundle(
        bundle_id="BASELINE",
        action_instance_ids=[],
        contract_action_ids=[],
        is_baseline=True,
    )]
    rejected: list[dict[str, Any]] = []

    for size in range(1, min(max_bundle_size, len(ordered)) + 1):
        for members in combinations(ordered, size):
            conflicts = bundle_conflicts(list(members))
            instance_ids = [str(item["action_id"]) for item in members]
            if conflicts:
                rejected.append({
                    "action_instance_ids": instance_ids,
                    "reasons": conflicts,
                })
                continue
            bundles.append(ActionBundle(
                bundle_id="BUNDLE:" + "+".join(instance_ids),
                action_instance_ids=instance_ids,
                contract_action_ids=[_family(item) for item in members],
            ))
    return BundleGeneration(bundles=bundles, rejected=rejected)
