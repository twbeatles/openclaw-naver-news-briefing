from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class SchedulePlan:
    kind: str
    label: str
    cron: str | None = None
    interval_minutes: int | None = None
    time: str | None = None
    days_of_week: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class OperatorHints:
    recommended_runner: str
    recommended_command: str
    delivery_format: str
    storage_target: str
    cadence_summary: str
    cron_examples: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AutomationPlan:
    raw_request: str
    action: str
    query_mode: str
    queries: List[str]
    primary_query: str | None
    intent: Dict[str, Any] | None
    schedule: SchedulePlan
    name_hint: str
    template: str
    briefing_focus: str
    watch_intent: str
    group_reason: str | None
    rationale: List[str]
    suggested_commands: List[str]
    operator_hints: OperatorHints


__all__ = ["AutomationPlan", "OperatorHints", "SchedulePlan"]
