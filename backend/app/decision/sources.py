"""Read checked server-side sources without filling unavailable values."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Literal

from backend.app.gfs_forecast import DEFAULT_OUTPUT_DIR

from .contracts import Contract, EvidenceValue
from .evidence import evidence_from_gfs_snapshot

DEFAULT_GFS_SNAPSHOT = DEFAULT_OUTPUT_DIR / "latest.json"


class EvidenceSourceResult(Contract):
    source: str
    status: Literal["available", "unavailable", "inapplicable"]
    reason: str | None = None
    values: list[EvidenceValue]


def load_checked_constraint(as_of: datetime, path: Path = DEFAULT_GFS_SNAPSHOT) -> EvidenceSourceResult:
    """A failed/missing read is explicit; no old snapshot or zero fills are used."""
    try:
        snapshot = json.loads(path.read_text())
        values = evidence_from_gfs_snapshot(snapshot, as_of=as_of)
    except FileNotFoundError:
        return EvidenceSourceResult(
            source="checked GFS national constraint", status="unavailable",
            reason="Checked constraint snapshot unavailable: no current snapshot file", values=[],
        )
    except (ValueError, KeyError, TypeError) as exc:
        return EvidenceSourceResult(
            source="checked GFS national constraint", status="unavailable",
            reason=f"Checked constraint snapshot unavailable: {exc}", values=[],
        )
    return EvidenceSourceResult(source="checked GFS national constraint", status="available", values=values)
