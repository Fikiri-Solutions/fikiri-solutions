"""Unit tests for core/ai_document_processor.py."""

import os
import sys
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_document_processor import (
    AIDocumentProcessor,
    ProcessingResult,
)


class TestAIDocumentProcessor:
    @patch("core.ai_document_processor.get_config")
    def test_supported_formats_structure(self, mock_config):
        mock_config.return_value = {}
        proc = AIDocumentProcessor()
        assert "pdf" in proc.supported_formats
        assert ".pdf" in proc.supported_formats["pdf"]

    @patch("core.ai_document_processor.get_config")
    def test_get_file_type_pdf(self, mock_config):
        mock_config.return_value = {}
        proc = AIDocumentProcessor()
        assert proc._get_file_type("/path/to/doc.pdf") == "pdf"

    @patch("core.ai_document_processor.get_config")
    def test_get_file_type_unknown(self, mock_config):
        mock_config.return_value = {}
        proc = AIDocumentProcessor()
        assert proc._get_file_type("/path/to/file.xyz") == "unknown"

    @patch("core.ai_document_processor.get_config")
    def test_process_document_unsupported_returns_failure(self, mock_config):
        mock_config.return_value = {}
        proc = AIDocumentProcessor()
        result = proc.process_document("/path/to/file.xyz")
        assert result.success is False
        assert result.content is None
        assert result.error


class TestProcessingResult:
    def test_structure(self):
        r = ProcessingResult(success=False, content=None, error="fail", processing_time=0.5)
        assert r.success is False
        assert r.error == "fail"
