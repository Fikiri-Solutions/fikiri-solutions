"""
Integration Framework
Unified integration system for Calendar, CRM, Payments, etc.
"""

from core.integrations.integration_framework import (
    IntegrationProvider,
    IntegrationManager,
    integration_manager
)

__all__ = [
    'IntegrationProvider',
    'IntegrationManager',
    'integration_manager'
]
