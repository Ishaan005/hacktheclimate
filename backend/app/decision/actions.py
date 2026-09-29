"""Versioned operator-action catalogue derived from issue #51."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .contracts import Contract
from .scenarios import SCENARIO_IDS

ACTIONS_PATH = Path(__file__).resolve().parents[3] / "config" / "decision_actions_v1.json"
ExecutionStatus = Literal["planning_supported", "evidence_only", "not_supported"]


class ActionDefinition(Contract):
    action_id: str
    name: str
    description: str
    applicable_scenarios: list[str] = Field(min_length=1)
    execution_status: ExecutionStatus
    required_parameters: list[str] = Field(default_factory=list)
    required_evidence_fields: list[str] = Field(default_factory=list)
    required_safety_rules: list[str] = Field(min_length=1)
    additional_safety_rules_by_scenario: dict[str, list[str]] = Field(default_factory=dict)
    source_reference: str

    @model_validator(mode="after")
    def valid_definition(self):
        if not self.action_id.strip() or not self.name.strip() or not self.source_reference.strip():
            raise ValueError("action definition needs an ID, name and source")
        if not set(self.applicable_scenarios) <= SCENARIO_IDS:
            raise ValueError(f"{self.action_id} references an unknown scenario")
        if not set(self.additional_safety_rules_by_scenario) <= set(self.applicable_scenarios):
            raise ValueError(f"{self.action_id} has safety overrides for an inapplicable scenario")
        for values in (
            self.applicable_scenarios,
            self.required_parameters,
            self.required_evidence_fields,
            self.required_safety_rules,
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{self.action_id} contains duplicate contract entries")
        return self

    def safety_rules_for(self, scenario_ids: list[str]) -> list[str]:
        rules = set(self.required_safety_rules)
        for scenario_id in scenario_ids:
            rules.update(self.additional_safety_rules_by_scenario.get(scenario_id, []))
        return sorted(rules)


class ActionCatalogue(Contract):
    schema_version: Literal[1] = 1
    status: Literal["working_draft", "approved"]
    source: str
    actions: list[ActionDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_catalogue(self):
        ids = [action.action_id for action in self.actions]
        if len(ids) != len(set(ids)):
            raise ValueError("action catalogue action IDs must be unique")
        covered = {scenario for action in self.actions for scenario in action.applicable_scenarios}
        if covered != SCENARIO_IDS:
            missing = sorted(SCENARIO_IDS - covered)
            raise ValueError(f"action catalogue does not cover locked scenarios: {missing}")
        if not self.source.strip():
            raise ValueError("action catalogue needs a source")
        return self


def load_action_catalogue(path: Path = ACTIONS_PATH) -> ActionCatalogue:
    catalogue = ActionCatalogue.model_validate_json(path.read_text())

    # Safety rule names are code-level contracts too: reject a typo rather than
    # silently dropping a required check.
    from .policy import load_demo_policy

    known_rules = {rule.rule_id for rule in load_demo_policy().rules}
    for action in catalogue.actions:
        referenced = set(action.required_safety_rules)
        referenced.update(
            rule
            for rules in action.additional_safety_rules_by_scenario.values()
            for rule in rules
        )
        unknown = sorted(referenced - known_rules)
        if unknown:
            raise ValueError(f"{action.action_id} references unknown safety rules: {unknown}")
    return catalogue
