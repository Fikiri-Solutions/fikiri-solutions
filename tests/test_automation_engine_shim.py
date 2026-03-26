#!/usr/bin/env python3
"""Regression tests for automation engine import-path convergence."""

from core import automation_engine as core_engine
from services import automation_engine as services_engine


def test_core_and_services_use_same_engine_instance():
    assert core_engine.automation_engine is services_engine.automation_engine


def test_core_exports_services_automation_types():
    assert core_engine.AutomationEngine is services_engine.AutomationEngine
    assert core_engine.ActionType is services_engine.ActionType
    assert core_engine.TriggerType is services_engine.TriggerType
    assert core_engine.AutomationStatus is services_engine.AutomationStatus


def test_core_scheduler_entrypoint_delegates_to_services():
    assert core_engine.run_due_time_based_automations is services_engine.run_due_time_based_automations
