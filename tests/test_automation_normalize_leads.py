"""Pure lead normalization tests (Windmill-independent)."""

from core.automation_normalize_leads import MAX_BATCH_SIZE, normalize_leads


def test_valid_input_normalized_and_ordered():
    result = normalize_leads(
        [
            {"email": " zoe@Example.com ", "name": "  Zoe  Z "},
            {"email": "ada@example.com", "name": "Ada"},
        ]
    )
    assert result.duplicate_count == 0
    assert [r["email"] for r in result.accepted] == ["ada@example.com", "zoe@example.com"]
    assert result.accepted[1]["name"] == "Zoe Z"


def test_missing_required_fields():
    result = normalize_leads([{"email": "a@b.co"}, {"name": "Only Name"}])
    assert result.accepted == []
    reasons = {r["reason"] for r in result.rejected}
    assert "missing_name" in reasons
    assert "missing_email" in reasons


def test_duplicates_counted():
    result = normalize_leads(
        [
            {"email": "Ada@Example.com", "name": "Ada"},
            {"email": " ada@example.com ", "name": "Ada Two"},
        ]
    )
    assert len(result.accepted) == 1
    assert result.duplicate_count == 1
    assert any(r["reason"] == "duplicate_email" for r in result.rejected)


def test_empty_input():
    result = normalize_leads([])
    assert result.accepted == []
    assert result.rejected == []
    assert result.duplicate_count == 0


def test_batch_too_large():
    rows = [{"email": f"u{i}@ex.com", "name": f"U{i}"} for i in range(MAX_BATCH_SIZE + 1)]
    result = normalize_leads(rows)
    assert result.accepted == []
    assert any(r["reason"] == "batch_too_large" for r in result.rejected)


def test_malformed_email():
    result = normalize_leads([{"email": "not-an-email", "name": "X"}])
    assert result.accepted == []
    assert result.rejected[0]["reason"] == "malformed_email"


def test_deterministic_ordering_stable():
    a = normalize_leads(
        [
            {"email": "b@ex.com", "name": "B"},
            {"email": "a@ex.com", "name": "A"},
        ]
    ).as_dict()
    b = normalize_leads(
        [
            {"email": "b@ex.com", "name": "B"},
            {"email": "a@ex.com", "name": "A"},
        ]
    ).as_dict()
    assert a == b
    assert [r["email"] for r in a["accepted"]] == ["a@ex.com", "b@ex.com"]
