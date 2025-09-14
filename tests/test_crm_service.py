import json
from core.crm_service import CRMService
from core.crm_storage import JSONLeadStorage


def test_ingest_and_dedupe(tmp_path):
    storage_path = tmp_path / 'leads.json'
    storage = JSONLeadStorage(str(storage_path))
    service = CRMService(storage)

    raw = [
        {"name": "A", "email": "a@example.com", "notes": "need a quote urgent"},
        {"name": "B", "email": "a@example.com", "notes": "duplicate"},
        {"name": "C", "email": "c@example.com", "notes": "schedule next week"},
    ]

    inserted = service.ingest(raw)
    assert len(inserted) == 2  # deduped by email

    leads = service.list()
    emails = {l.email for l in leads}
    assert emails == {"a@example.com", "c@example.com"}

    # Scoring: urgent/quote should be higher
    scored = {l.email: l.score for l in leads}
    assert scored["a@example.com"] >= scored["c@example.com"]
