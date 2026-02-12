"""
Email Automation Module
"""
from .parser import MinimalEmailParser
from .ai_assistant import MinimalAIEmailAssistant
from .actions import MinimalEmailActions
from .followup_system import get_follow_up_system, AutomatedFollowUpSystem

__all__ = [
    "MinimalEmailParser",
    "MinimalAIEmailAssistant",
    "MinimalEmailActions",
    "get_follow_up_system",
    "AutomatedFollowUpSystem"
]

