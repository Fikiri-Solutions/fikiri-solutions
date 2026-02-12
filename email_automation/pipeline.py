#!/usr/bin/env python3
"""
Email automation pipeline façade.

Orchestrates the email flow; implementation lives in:
  - email_automation/actions.py   (MinimalEmailActions, send/process)
  - email_automation/parser.py    (MinimalEmailParser)
  - email_automation/service_manager.py (EmailServiceManager, providers)
  - email_automation/jobs.py      (EmailJobManager, queue processing)

Import from here for a single pipeline entry point, or import from the
submodules directly when you need a specific component.
"""

from email_automation.parser import MinimalEmailParser
from email_automation.actions import MinimalEmailActions
from email_automation.service_manager import EmailServiceManager
from email_automation.jobs import EmailJobManager, EmailJob

__all__ = [
    "MinimalEmailParser",
    "MinimalEmailActions",
    "EmailServiceManager",
    "EmailJobManager",
    "EmailJob",
    "parse_message",
    "process_incoming",
]


def parse_message(message: dict) -> dict:
    """Parse a raw message via the canonical parser."""
    parser = MinimalEmailParser()
    return parser.parse_message(message)


def process_incoming(message: dict, actions: MinimalEmailActions = None) -> dict:
    """
    Parse and optionally run actions on an incoming message.
    Caller can pass a configured MinimalEmailActions instance or None to only parse.
    """
    parsed = parse_message(message)
    if actions is None:
        return parsed
    # Optional: run classification/reply logic via actions if needed
    return parsed
