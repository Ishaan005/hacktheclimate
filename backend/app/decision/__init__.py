"""Typed, evidence-gated services for the advisory decision demo."""

from .baseline import best_case_metrics, calculate_current_plan
from .cases import append_case, load_cases, search_cases
from .contracts import DecisionCase, EvidenceValue, ExistingInstruction, PastCase
from .evidence import evidence_from_gfs_snapshot, resolve_case_context
from .manifest import load_contract_manifest
from .policy import evaluate_policy, load_demo_policy
from .service import evaluate_case
from .sources import load_checked_constraint

__all__ = [
    "DecisionCase", "EvidenceValue", "ExistingInstruction", "PastCase",
    "append_case", "best_case_metrics", "calculate_current_plan",
    "evaluate_case", "evaluate_policy", "evidence_from_gfs_snapshot", "load_cases",
    "load_checked_constraint", "load_contract_manifest", "load_demo_policy",
    "resolve_case_context", "search_cases",
]
