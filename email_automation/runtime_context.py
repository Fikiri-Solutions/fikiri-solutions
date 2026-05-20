"""
Per-sync-job runtime context for mailbox automation.

Created once per Gmail/Outlook sync job, reused for each message in that job,
and discarded when the job ends. Not a global singleton — never shared across
users or jobs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmailAutomationRuntimeContext:
    """
    Immutable job metadata + reusable mailbox automation stack.

    Safe to reuse across messages in one sync job:
      - MinimalEmailActions / MinimalAIEmailAssistant (no per-message mutable state)
      - MinimalEmailParser (stateless)

    Must NOT store per-message bodies, classifications, or workflow state.
    """

    job_id: str
    user_id: int
    provider: str = "gmail"
    correlation_id: Optional[str] = None

    actions: Any = field(default=None, repr=False)
    parser: Any = field(default=None, repr=False)

    messages_processed: int = 0
    messages_failed: int = 0
    automations_run: int = 0

    _initialized: bool = field(default=False, repr=False)
    _poisoned: bool = field(default=False, repr=False)
    _init_error: Optional[str] = field(default=None, repr=False)

    @property
    def context_reused(self) -> bool:
        return self._initialized and not self._poisoned

    @property
    def mailbox_stack_ready(self) -> bool:
        return (
            self._initialized
            and not self._poisoned
            and self.actions is not None
            and self.parser is not None
        )

    @property
    def ai_assistant(self) -> Any:
        """Shared MinimalAIEmailAssistant when mailbox stack is initialized."""
        if self.actions is None:
            return None
        services = getattr(self.actions, "services", None)
        if isinstance(services, dict):
            return services.get("ai_assistant")
        return None

    def assert_user_scope(self, user_id: int) -> bool:
        """Return False when caller user_id does not match this job context."""
        return int(self.user_id) == int(user_id)

    def initialize_mailbox_stack(
        self,
        *,
        gmail_service: Any = None,
    ) -> bool:
        """
        Build actions + assistant + parser once for this job.
        Returns False on failure (caller may disable mailbox AI for the job).
        """
        if self._poisoned:
            return False
        if self._initialized and self.actions is not None and self.parser is not None:
            if gmail_service is not None and self.actions is not None:
                self.actions.services["gmail"] = gmail_service
                if getattr(self.actions, "gmail_service", None) is None:
                    self.actions.gmail_service = gmail_service
            return True

        try:
            from email_automation.actions import MinimalEmailActions
            from email_automation.ai_assistant import MinimalAIEmailAssistant
            from email_automation.parser import MinimalEmailParser

            services: Dict[str, Any] = {"ai_assistant": MinimalAIEmailAssistant()}
            if gmail_service is not None:
                services["gmail"] = gmail_service
            self.actions = MinimalEmailActions(services=services)
            self.parser = MinimalEmailParser()
            self._initialized = True
            self._init_error = None

            logger.info(
                "email.sync.runtime_context.initialized",
                extra={
                    "event": "email.sync.runtime_context.initialized",
                    "service": "email",
                    "job_id": self.job_id,
                    "user_id": self.user_id,
                    "provider": self.provider,
                    "context_reused": True,
                },
            )
            return True
        except Exception as exc:
            self._poisoned = True
            self._init_error = str(exc)[:500]
            self.actions = None
            self.parser = None
            self._initialized = False
            logger.warning(
                "email.sync.runtime_context.init_failed job_id=%s user_id=%s error=%s",
                self.job_id,
                self.user_id,
                self._init_error,
                extra={
                    "event": "email.sync.runtime_context.init_failed",
                    "service": "email",
                    "job_id": self.job_id,
                    "user_id": self.user_id,
                    "provider": self.provider,
                },
            )
            return False

    def invalidate(self, reason: str = "") -> None:
        """Drop reusable stack after an unrecoverable error (fresh init on next ensure)."""
        self._poisoned = True
        self.actions = None
        self.parser = None
        self._initialized = False
        if reason:
            self._init_error = reason[:500]

    def record_message_processed(self, *, automation_ran: bool = False) -> None:
        self.messages_processed += 1
        if automation_ran:
            self.automations_run += 1

    def record_message_failed(self) -> None:
        self.messages_failed += 1

    def log_job_summary(self) -> None:
        logger.info(
            "email.sync.runtime_context.summary",
            extra={
                "event": "email.sync.runtime_context.summary",
                "service": "email",
                "job_id": self.job_id,
                "user_id": self.user_id,
                "provider": self.provider,
                "messages_processed": self.messages_processed,
                "messages_failed": self.messages_failed,
                "automations_run": self.automations_run,
                "context_reused": self.context_reused,
            },
        )

    @classmethod
    def for_gmail_sync(
        cls,
        job_id: str,
        user_id: int,
        *,
        gmail_service: Any = None,
        correlation_id: Optional[str] = None,
    ) -> EmailAutomationRuntimeContext:
        ctx = cls(
            job_id=job_id,
            user_id=user_id,
            provider="gmail",
            correlation_id=correlation_id,
        )
        ctx.initialize_mailbox_stack(gmail_service=gmail_service)
        return ctx


def try_create_gmail_sync_runtime(
    job_id: str,
    user_id: int,
    *,
    gmail_service: Any = None,
    mailbox_automation_enabled: bool,
) -> Optional[EmailAutomationRuntimeContext]:
    """Create runtime context when mailbox automation is enabled; else None."""
    if not mailbox_automation_enabled:
        return None
    ctx = EmailAutomationRuntimeContext.for_gmail_sync(
        job_id,
        user_id,
        gmail_service=gmail_service,
    )
    if not ctx.mailbox_stack_ready:
        return None
    return ctx
