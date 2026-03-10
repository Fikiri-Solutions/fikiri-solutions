"""
Unit tests for core/document_analytics_system.py (DocumentAnalyticsSystem, metrics, export).
"""

import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAnalyticsEventTypeAndDataclasses:
    """Test enums and data structures."""

    def test_analytics_event_type_values(self):
        from core.document_analytics_system import AnalyticsEventType
        assert AnalyticsEventType.DOCUMENT_PROCESSED.value == "document_processed"
        assert AnalyticsEventType.FORM_SUBMITTED.value == "form_submitted"
        assert AnalyticsEventType.TEMPLATE_USED.value == "template_used"

    def test_processing_metrics_dataclass(self):
        from core.document_analytics_system import ProcessingMetrics
        m = ProcessingMetrics(
            total_documents=10,
            successful_processes=8,
            failed_processes=2,
            avg_processing_time=1.5,
            total_processing_time=15.0,
            success_rate=80.0,
            most_common_format="pdf",
            formats_processed={"pdf": 6, "docx": 4},
        )
        assert m.total_documents == 10
        assert m.success_rate == 80.0
        assert m.most_common_format == "pdf"


class TestDocumentAnalyticsSystem:
    """Test DocumentAnalyticsSystem tracking and metrics."""

    def setup_method(self):
        with patch("core.document_analytics_system.get_config", return_value={}):
            from core.document_analytics_system import DocumentAnalyticsSystem
            self.system = DocumentAnalyticsSystem()

    def test_track_event_returns_event_id(self):
        from core.document_analytics_system import AnalyticsEventType
        event_id = self.system.track_event(
            AnalyticsEventType.DOCUMENT_PROCESSED,
            user_id=1,
            metadata={"file_type": "pdf"},
        )
        assert event_id != ""
        assert event_id in self.system.events

    def test_track_event_with_session_updates_sessions(self):
        from core.document_analytics_system import AnalyticsEventType
        event_id = self.system.track_event(
            AnalyticsEventType.FORM_SUBMITTED,
            user_id=2,
            metadata={},
            session_id="sess-1",
        )
        assert event_id != ""
        assert "sess-1" in self.system.sessions
        assert event_id in self.system.sessions["sess-1"]["events"]

    def test_track_document_processing_returns_id(self):
        event_id = self.system.track_document_processing(
            user_id=1,
            file_type="pdf",
            processing_time=2.5,
            success=True,
        )
        assert event_id != ""
        event = self.system.events[event_id]
        assert event.metadata["file_type"] == "pdf"
        assert event.metadata["success"] is True

    def test_track_form_submission_success(self):
        event_id = self.system.track_form_submission(
            user_id=1,
            form_id="form-1",
            completion_time=30.0,
            success=True,
        )
        assert event_id != ""
        event = self.system.events[event_id]
        assert event.event_type.value == "form_submitted"
        assert event.metadata["form_id"] == "form-1"

    def test_track_form_submission_validation_failed(self):
        event_id = self.system.track_form_submission(
            user_id=1,
            form_id="form-1",
            completion_time=10.0,
            success=False,
            validation_errors=["email required"],
        )
        assert event_id != ""
        event = self.system.events[event_id]
        assert event.event_type.value == "validation_failed"

    def test_track_template_usage(self):
        event_id = self.system.track_template_usage(
            user_id=1,
            template_id="tpl-1",
            document_type="invoice",
            generation_time=1.0,
        )
        assert event_id != ""
        event = self.system.events[event_id]
        assert event.metadata["template_id"] == "tpl-1"
        assert event.metadata["document_type"] == "invoice"

    def test_track_ocr_processing(self):
        event_id = self.system.track_ocr_processing(
            user_id=1,
            image_format="png",
            confidence_score=0.95,
            text_length=500,
            processing_time=0.5,
        )
        assert event_id != ""
        event = self.system.events[event_id]
        assert event.metadata["image_format"] == "png"
        assert event.metadata["confidence_score"] == 0.95

    def test_get_processing_metrics_empty(self):
        metrics = self.system.get_processing_metrics(days=30)
        assert metrics.total_documents == 0
        assert metrics.successful_processes == 0
        assert metrics.success_rate == 0
        assert metrics.most_common_format == ""

    def test_get_processing_metrics_with_events(self):
        self.system.track_document_processing(1, "pdf", 1.0, True)
        self.system.track_document_processing(1, "pdf", 2.0, True)
        self.system.track_document_processing(1, "docx", 0.5, False)
        metrics = self.system.get_processing_metrics(days=30)
        assert metrics.total_documents == 3
        assert metrics.successful_processes == 2
        assert metrics.failed_processes == 1
        assert metrics.most_common_format == "pdf"
        assert metrics.formats_processed.get("pdf") == 2
        assert metrics.formats_processed.get("docx") == 1

    def test_get_form_metrics_empty(self):
        metrics = self.system.get_form_metrics(days=30)
        assert metrics.total_submissions == 0
        assert metrics.completion_rate == 0

    def test_get_form_metrics_with_events(self):
        self.system.track_form_submission(1, "f1", 20.0, True)
        self.system.track_form_submission(1, "f1", 10.0, False)
        metrics = self.system.get_form_metrics(days=30)
        assert metrics.total_submissions == 2
        assert metrics.successful_submissions == 1
        assert metrics.validation_failures == 1
        assert metrics.most_popular_form == "f1"

    def test_get_template_metrics_with_events(self):
        self.system.track_template_usage(1, "t1", "invoice", 2.0)
        self.system.track_template_usage(1, "t1", "invoice", 1.0)
        self.system.track_template_usage(1, "t2", "quote", 1.5)
        metrics = self.system.get_template_metrics(days=30)
        assert metrics.total_generations == 3
        assert metrics.most_used_template == "t1"
        assert metrics.templates_by_usage.get("t1") == 2
        assert metrics.documents_by_type.get("invoice") == 2

    def test_get_user_engagement_metrics(self):
        self.system.track_document_processing(1, "pdf", 1.0, True)
        self.system.track_document_processing(1, "pdf", 1.0, True)
        self.system.track_document_processing(2, "docx", 1.0, True)
        metrics = self.system.get_user_engagement_metrics(days=30)
        assert metrics.active_users == 2
        assert metrics.documents_per_user == 1.5  # 3 docs / 2 users
        assert metrics.most_active_user == 1  # user 1 has 2 docs

    def test_get_comprehensive_report_structure(self):
        self.system.track_document_processing(1, "pdf", 1.0, True)
        report = self.system.get_comprehensive_report(days=30)
        assert "report_period" in report
        assert "processing_metrics" in report
        assert "form_metrics" in report
        assert "template_metrics" in report
        assert "engagement_metrics" in report
        assert "trends" in report
        assert "insights" in report
        assert "summary" in report
        assert report["summary"]["total_events"] >= 1
        assert "active_users" in report["summary"]

    def test_export_analytics_data_json(self):
        from core.document_analytics_system import AnalyticsEventType
        self.system.track_event(AnalyticsEventType.DOCUMENT_PROCESSED, 1, {})
        out = self.system.export_analytics_data(days=30, format="json")
        data = json.loads(out)
        assert "report_period" in data
        assert "processing_metrics" in data

    def test_export_analytics_data_csv(self):
        from core.document_analytics_system import AnalyticsEventType
        self.system.track_event(AnalyticsEventType.DOCUMENT_PROCESSED, 1, {"file_type": "pdf"})
        out = self.system.export_analytics_data(days=30, format="csv")
        assert "event_id,event_type,user_id,timestamp,metadata" in out
        assert "document_processed" in out

    def test_get_real_time_stats_structure(self):
        stats = self.system.get_real_time_stats()
        assert "events_today" in stats
        assert "active_sessions" in stats
        assert "total_events" in stats
        assert "total_users" in stats
        assert "last_event_time" in stats
        assert "system_uptime" in stats
        assert stats["total_events"] == 0

    def test_get_real_time_stats_after_events(self):
        from core.document_analytics_system import AnalyticsEventType
        self.system.track_event(AnalyticsEventType.DOCUMENT_PROCESSED, 1, {})
        stats = self.system.get_real_time_stats()
        assert stats["total_events"] == 1
        assert stats["total_users"] == 1


class TestGetDocumentAnalytics:
    """Test global getter."""

    def test_get_document_analytics_returns_system(self):
        from core.document_analytics_system import get_document_analytics, DocumentAnalyticsSystem
        instance = get_document_analytics()
        assert isinstance(instance, DocumentAnalyticsSystem)
