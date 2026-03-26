"""
Compatibility shim for legacy imports.

Runtime automation engine ownership is in `services/automation_engine.py`.
This module intentionally re-exports the services implementation to avoid
behavior drift across two automation engines.
"""

from services.automation_engine import (
    ActionType,
    AutomationEngine,
    AutomationExecution,
    AutomationRule,
    AutomationStatus,
    TriggerType,
    automation_engine,
    run_due_time_based_automations,
)

__all__ = [
    "AutomationEngine",
    "automation_engine",
    "AutomationRule",
    "AutomationExecution",
    "TriggerType",
    "ActionType",
    "AutomationStatus",
    "run_due_time_based_automations",
]
