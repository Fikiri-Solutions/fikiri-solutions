#!/usr/bin/env python3
"""
Business and CRM Routes
Extracted from app.py for better maintainability
"""

from flask import Blueprint, request, jsonify, send_file, Response
from functools import wraps
import logging
import os
import io
import csv
import json
import re
from datetime import datetime

# Import business logic modules
from crm.service import (
    enhanced_crm_service,
    lead_row_to_public_dict,
    lead_dataclass_to_public_dict,
)
from core.database_optimization import db_optimizer
try:
    from core.ai_budget_guardrails import ai_budget_guardrails
except ModuleNotFoundError:
    # Stub when module not present (e.g. CI branch before guardrails commit)
    class _StubBudgetDecision:
        allowed = True
        reason = "stub_no_module"
    class _StubBudgetGuardrails:
        def evaluate(self, user_id, projected_increment=1):
            return _StubBudgetDecision()
        def record_ai_usage(self, user_id, quantity=1):
            pass
    ai_budget_guardrails = _StubBudgetGuardrails()
from core.api_validation import handle_api_errors, create_success_response, create_error_response
from core.request_correlation import get_or_create_correlation_id
from core.correlation_trace import fetch_correlation_trace
from services.automation_engine import AutomationEngine, TriggerType
# Create automation_engine instance for backward compatibility
automation_engine = AutomationEngine()
from core.automation_safety import automation_safety_manager
from core.oauth_token_manager import oauth_token_manager
from core.secure_sessions import get_current_user_id
from core.activity_logger import log_activity_event
from core.rate_limiter import enhanced_rate_limiter
from core.idempotency_manager import idempotency_manager
from core.domain.schemas import normalize_lead_payload
from email_automation.service_manager import IMAPProvider
from core.user_auth import user_auth_manager
from core.workflow_followups import schedule_follow_up, execute_due_follow_ups
from core.workflow_documents import generate_document
from core.tier_usage_caps import check_tier_usage_cap, record_monthly_usage
from core.request_user_id import resolve_request_user_id
from core.privacy_manager import privacy_manager, PrivacySettings, PrivacyConsent

logger = logging.getLogger(__name__)


def _plain_email_snippet(text, max_len: int = 160):
    """Strip HTML for API list snippets so clients do not show raw <!DOCTYPE in previews."""
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", str(text))
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > max_len:
        return t[:max_len].rstrip() + "…"
    return t


def _serialize_privacy_settings(ps: PrivacySettings | None) -> dict | None:
    if ps is None:
        return None
    return {
        "id": ps.id,
        "user_id": ps.user_id,
        "data_retention_days": ps.data_retention_days,
        "email_scanning_enabled": ps.email_scanning_enabled,
        "personal_email_exclusion": ps.personal_email_exclusion,
        "auto_labeling_enabled": ps.auto_labeling_enabled,
        "lead_detection_enabled": ps.lead_detection_enabled,
        "analytics_tracking_enabled": ps.analytics_tracking_enabled,
        "created_at": ps.created_at.isoformat() if ps.created_at else None,
        "updated_at": ps.updated_at.isoformat() if ps.updated_at else None,
    }


def _serialize_privacy_consent(c: PrivacyConsent) -> dict:
    return {
        "id": c.id,
        "user_id": c.user_id,
        "consent_type": c.consent_type,
        "granted": c.granted,
        "consent_text": c.consent_text,
        "granted_at": c.granted_at.isoformat() if c.granted_at else None,
        "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
    }


def _ensure_privacy_settings_row(user_id: int) -> PrivacySettings | None:
    ps = privacy_manager.get_privacy_settings(user_id)
    if ps is not None:
        return ps
    privacy_manager.create_default_privacy_settings(user_id)
    return privacy_manager.get_privacy_settings(user_id)

# Create business blueprint
business_bp = Blueprint("business_routes", __name__, url_prefix="/api")

def _require_paid_plan(user_id: int) -> bool:
    if not db_optimizer.table_exists("subscriptions"):
        return True
    try:
        sub = db_optimizer.execute_query(
            "SELECT status FROM subscriptions WHERE user_id = ? ORDER BY current_period_end DESC LIMIT 1",
            (user_id,)
        )
        if not sub:
            return False
        status = (sub[0].get("status") or "").lower()
        return status in {"active", "trialing"}
    except Exception as e:
        logger.warning("Plan check failed: %s", e)
        return True


def _check_tier_usage_cap(user_id: int, usage_type: str, projected_increment: int = 1):
    """Return a 402 response when projected usage exceeds plan cap; otherwise None."""
    allowed, msg, code = check_tier_usage_cap(
        user_id, usage_type, projected_increment=projected_increment, db=db_optimizer
    )
    if not allowed:
        return create_error_response(msg, 402, code)
    return None

# CRM Routes
@business_bp.route('/crm/leads', methods=['GET'])
@handle_api_errors
def get_leads():
    """Get all leads for authenticated user with pagination"""
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    limit = min(max(request.args.get('limit', type=int, default=100), 1), 500)
    offset = request.args.get('offset', type=int, default=0)
    
    filters = {}
    if request.args.get('stage'):
        filters['stage'] = request.args.get('stage')
    if request.args.get('time_period'):
        filters['time_period'] = request.args.get('time_period')
    if request.args.get('company'):
        filters['company'] = request.args.get('company')

    result = enhanced_crm_service.get_leads_summary(user_id, filters=filters, limit=limit, offset=offset)
    if not result.get('success'):
        return create_error_response(result.get('error', 'Failed to retrieve leads'), 500, 'CRM_ERROR')
    
    data = result['data']
    return create_success_response({
        'leads': data.get('leads', []),
        'pagination': {
            'total_count': data.get('total_count', 0),
            'returned_count': data.get('returned_count', 0),
            'limit': data.get('limit', limit),
            'offset': data.get('offset', offset),
            'has_more': data.get('has_more', False)
        },
        'analytics': data.get('analytics', {})
    }, 'Leads retrieved successfully')


@business_bp.route('/crm/leads/export', methods=['GET'])
@handle_api_errors
def export_leads_csv():
    """Export all leads for the authenticated user as CSV."""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    result = enhanced_crm_service.get_leads_summary(user_id, limit=5000, offset=0)
    if not result.get('success'):
        return create_error_response(result.get('error', 'Failed to retrieve leads'), 500, 'CRM_ERROR')

    leads = result.get('data', {}).get('leads', [])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'name', 'email', 'phone', 'company', 'source', 'stage', 'score', 'created_at'])

    for lead in leads:
        if hasattr(lead, 'id'):
            created = lead.created_at.isoformat() if hasattr(lead.created_at, 'isoformat') else str(getattr(lead, 'created_at', ''))
            writer.writerow([
                getattr(lead, 'id', ''),
                getattr(lead, 'name', '') or '',
                getattr(lead, 'email', '') or '',
                getattr(lead, 'phone', None) or '',
                getattr(lead, 'company', None) or '',
                getattr(lead, 'source', '') or '',
                getattr(lead, 'stage', '') or '',
                getattr(lead, 'score', '') or '',
                created,
            ])
        else:
            lead_dict = dict(lead) if hasattr(lead, 'keys') else lead
            created = lead_dict.get('created_at')
            if hasattr(created, 'isoformat'):
                created = created.isoformat()
            writer.writerow([
                lead_dict.get('id', ''),
                lead_dict.get('name', '') or '',
                lead_dict.get('email', '') or '',
                lead_dict.get('phone', '') or '',
                lead_dict.get('company', '') or '',
                lead_dict.get('source', '') or '',
                lead_dict.get('stage', '') or '',
                lead_dict.get('score', '') or '',
                created or '',
            ])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=leads.csv'
    return response


@business_bp.route('/crm/leads', methods=['POST'])
@handle_api_errors
def create_lead():
    """Create a new lead"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

    # Validate required fields
    required_fields = ['email', 'name']
    for field in required_fields:
        if field not in data or not data[field]:
            return create_error_response(f"{field} is required", 400, 'MISSING_FIELD')

    correlation_id = get_or_create_correlation_id(request, data)
    lead_data = {
        'name': data['name'],
        'email': data['email'],
        'company': data.get('company', ''),
        'phone': data.get('phone', ''),
        'source': data.get('source', 'website'),
        'stage': data.get('stage') or data.get('status', 'new'),
        'notes': data.get('notes', ''),
        'correlation_id': correlation_id,
    }

    result = enhanced_crm_service.create_lead(user_id, lead_data)
    if not result.get('success'):
        code = result.get('error_code', 'CRM_CREATE_ERROR')
        status = 409 if code == 'LEAD_EXISTS' else 400 if code == 'MISSING_FIELD' else 500
        return create_error_response(
            result.get('error', 'Failed to create lead'),
            status,
            code,
            correlation_id=correlation_id,
        )

    lead_id = result['data']['lead_id']
    row = enhanced_crm_service.get_lead(lead_id, user_id)
    return create_success_response(
        {'lead': lead_row_to_public_dict(row)},
        'Lead created successfully',
        correlation_id=result['data'].get('correlation_id') or correlation_id,
    )


@business_bp.route('/crm/leads/import', methods=['POST'])
@handle_api_errors
def import_leads():
    """Import/migrate leads via JSON payload"""
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    data = request.get_json()
    if not data or 'leads' not in data or not isinstance(data['leads'], list):
        return create_error_response("leads[] is required", 400, 'MISSING_FIELDS')

    normalized_leads = [normalize_lead_payload(lead) for lead in data['leads']]
    result = enhanced_crm_service.import_leads(user_id, normalized_leads)
    if not result.get('success'):
        return create_error_response(result.get('error', 'Import failed'), 500, 'CRM_IMPORT_ERROR')
    return create_success_response(result.get('data', {}), 'Leads imported successfully')


def _is_valid_email(value):
    if not value or not isinstance(value, str):
        return False
    value = value.strip()
    if not value:
        return False
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', value))


# CRM CSV import limits (documented in docs/EXPORT_IMPORT_DATA_FORMATS.md)
CRM_CSV_MAX_FILE_BYTES = 5 * 1024 * 1024   # 5 MB
CRM_CSV_MAX_ROWS = 10000


@business_bp.route('/crm/leads/import/csv', methods=['POST'])
@handle_api_errors
def import_leads_csv():
    """Import leads from an uploaded CSV file. Required columns: email, name. Optional: phone, source, company.
    Query/form: on_duplicate=skip|update|merge. Header: Idempotency-Key for safe retries. Rate limited per user."""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    rate_result = enhanced_rate_limiter.check_rate_limit(
        'crm_csv_import', f"user:{user_id}", user_id=user_id
    )
    if not rate_result.allowed:
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded',
            'error_code': 'RATE_LIMIT_EXCEEDED',
            'retry_after': rate_result.retry_after,
            'limit': rate_result.limit,
            'remaining': rate_result.remaining,
        }), 429

    idem_key = request.headers.get('Idempotency-Key') or request.form.get('idempotency_key')
    if idem_key:
        cached = idempotency_manager.check_key(idem_key)
        if cached and cached.get('status') == 'completed' and cached.get('response_data'):
            return create_success_response(cached['response_data'], 'Leads imported successfully')
        if cached and cached.get('status') == 'pending':
            return create_error_response(
                "Import with this idempotency key is already in progress",
                409,
                'IDEMPOTENCY_CONFLICT'
            )

    file = request.files.get('file')
    if not file or not file.filename:
        return create_error_response("No file uploaded", 400, 'NO_FILE')

    if not file.filename.lower().endswith('.csv'):
        return create_error_response("File must be a CSV", 400, 'INVALID_FILE_TYPE')

    try:
        content = file.read()
        if len(content) > CRM_CSV_MAX_FILE_BYTES:
            return create_error_response(
                f"File too large (max {CRM_CSV_MAX_FILE_BYTES // (1024 * 1024)} MB)",
                400,
                'FILE_TOO_LARGE'
            )
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
    except Exception as e:
        logger.warning("CSV import decode error: %s", e)
        return create_error_response("Could not read file", 400, 'INVALID_CSV')

    if not content or not content.strip():
        return create_error_response("File is empty", 400, 'INVALID_CSV')

    reader = csv.DictReader(io.StringIO(content))
    fieldnames = reader.fieldnames or []
    email_key = next((f for f in fieldnames if f.strip().lower() == 'email'), None)
    name_key = next((f for f in fieldnames if f.strip().lower() == 'name'), None)
    if not email_key or not name_key:
        return create_error_response(
            "CSV must have 'email' and 'name' columns",
            400,
            'INVALID_CSV'
        )

    leads = []
    skipped = []
    for i, row in enumerate(reader):
        email = (row.get(email_key) or '').strip()
        name = (row.get(name_key) or '').strip()
        if not email:
            skipped.append({'row': i + 2, 'reason': 'missing email'})
            continue
        if not _is_valid_email(email):
            skipped.append({'row': i + 2, 'reason': 'invalid email', 'email': email})
            continue
        if not name:
            name = email.split('@')[0]
        phone = (row.get('phone') or row.get('Phone') or '').strip()
        source = (row.get('source') or row.get('Source') or 'csv_import').strip() or 'csv_import'
        company = (row.get('company') or row.get('Company') or '').strip()
        leads.append(normalize_lead_payload({
            'email': email,
            'name': name,
            'phone': phone or None,
            'source': source,
            'company': company or None,
        }))

    if not leads:
        return create_error_response(
            "No valid rows to import (need valid email and name)",
            400,
            'INVALID_CSV'
        )

    if len(leads) + len(skipped) > CRM_CSV_MAX_ROWS:
        return create_error_response(
            f"Too many rows (max {CRM_CSV_MAX_ROWS})",
            400,
            'TOO_MANY_ROWS'
        )

    on_duplicate = (request.form.get('on_duplicate') or request.args.get('on_duplicate') or 'update').strip().lower()
    if on_duplicate not in ('skip', 'update', 'merge'):
        on_duplicate = 'update'

    if idem_key:
        idempotency_manager.store_key(
            idem_key, 'crm_csv_import', user_id=user_id,
            request_data={'filename': file.filename, 'on_duplicate': on_duplicate},
            ttl=86400,
        )

    result = enhanced_crm_service.import_leads(user_id, leads, on_duplicate=on_duplicate)
    if not result.get('success'):
        if idem_key:
            idempotency_manager.update_key_result(
                idem_key, 'failed',
                response_data={'error': result.get('error', 'Import failed')},
            )
        return create_error_response(result.get('error', 'Import failed'), 500, 'CRM_IMPORT_ERROR')

    data = result.get('data', {})
    response_body = {
        'imported': data.get('created', 0) + data.get('updated', 0),
        'created': data.get('created', 0),
        'updated': data.get('updated', 0),
        'skipped': len(skipped),
        'skipped_duplicate': data.get('skipped_duplicate', 0),
        'skipped_details': skipped[:50],
        'total_rows': len(leads) + len(skipped),
    }
    if idem_key:
        idempotency_manager.update_key_result(idem_key, 'completed', response_data=response_body)
    return create_success_response(response_body, 'Leads imported successfully')


@business_bp.route('/crm/leads/import/csv/preview', methods=['POST'])
@handle_api_errors
def import_leads_csv_preview():
    """Validate CSV and return per-row status (ok, duplicate, invalid) without importing.
    Use before import to show preview. Same file constraints as import."""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    file = request.files.get('file')
    if not file or not file.filename:
        return create_error_response("No file uploaded", 400, 'NO_FILE')
    if not file.filename.lower().endswith('.csv'):
        return create_error_response("File must be a CSV", 400, 'INVALID_FILE_TYPE')

    try:
        content = file.read()
        if len(content) > CRM_CSV_MAX_FILE_BYTES:
            return create_error_response(
                f"File too large (max {CRM_CSV_MAX_FILE_BYTES // (1024 * 1024)} MB)",
                400,
                'FILE_TOO_LARGE'
            )
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
    except Exception as e:
        logger.warning("CSV preview decode error: %s", e)
        return create_error_response("Could not read file", 400, 'INVALID_CSV')
    if not content or not content.strip():
        return create_error_response("File is empty", 400, 'INVALID_CSV')

    reader = csv.DictReader(io.StringIO(content))
    fieldnames = reader.fieldnames or []
    email_key = next((f for f in fieldnames if f.strip().lower() == 'email'), None)
    name_key = next((f for f in fieldnames if f.strip().lower() == 'name'), None)
    if not email_key or not name_key:
        return create_error_response(
            "CSV must have 'email' and 'name' columns",
            400,
            'INVALID_CSV'
        )

    existing_emails = set()
    try:
        existing = db_optimizer.execute_query(
            "SELECT email FROM leads WHERE user_id = ?",
            (user_id,)
        )
        existing_emails = {row['email'].lower().strip() for row in (existing or [])}
    except Exception:
        pass

    rows_out = []
    ok_count = duplicate_count = invalid_count = 0
    for i, row in enumerate(reader):
        csv_row = i + 2
        email = (row.get(email_key) or '').strip()
        name = (row.get(name_key) or '').strip()
        if not email:
            rows_out.append({'row': csv_row, 'email': email, 'name': name, 'status': 'invalid', 'reason': 'missing email'})
            invalid_count += 1
            continue
        if not _is_valid_email(email):
            rows_out.append({'row': csv_row, 'email': email, 'name': name or email.split('@')[0], 'status': 'invalid', 'reason': 'invalid email'})
            invalid_count += 1
            continue
        if not name:
            name = email.split('@')[0]
        if email.lower() in existing_emails:
            rows_out.append({'row': csv_row, 'email': email, 'name': name, 'status': 'duplicate'})
            duplicate_count += 1
        else:
            rows_out.append({'row': csv_row, 'email': email, 'name': name, 'status': 'ok'})
            ok_count += 1

    total = len(rows_out)
    if total > CRM_CSV_MAX_ROWS:
        return create_error_response(
            f"Too many rows (max {CRM_CSV_MAX_ROWS})",
            400,
            'TOO_MANY_ROWS'
        )

    return create_success_response({
        'preview': True,
        'total_rows': total,
        'valid_rows': ok_count + duplicate_count,
        'invalid_rows': invalid_count,
        'summary': {'ok': ok_count, 'duplicate': duplicate_count, 'invalid': invalid_count},
        'rows': rows_out[:500],
    }, 'Preview generated')


@business_bp.route('/crm/leads/<int:lead_id>', methods=['PUT'])
@handle_api_errors
def update_lead(lead_id):
    """Update an existing lead"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

    row = enhanced_crm_service.get_lead(lead_id, user_id)
    if not row:
        return create_error_response("Lead not found", 404, 'LEAD_NOT_FOUND')

    payload = dict(data)
    if 'stage' not in payload and 'status' in payload:
        payload['stage'] = payload['status']

    result = enhanced_crm_service.update_lead(lead_id, user_id, payload)
    if not result.get('success'):
        ec = result.get('error_code', 'CRM_UPDATE_ERROR')
        status = 404 if ec == 'LEAD_NOT_FOUND' else 400
        return create_error_response(result.get('error', 'Failed to update lead'), status, ec)

    lead_obj = result['data']['lead']
    return create_success_response(
        {'lead': lead_dataclass_to_public_dict(lead_obj)},
        'Lead updated successfully'
    )

@business_bp.route('/crm/contacts/<int:contact_id>', methods=['DELETE'])
@business_bp.route('/crm/leads/<int:contact_id>', methods=['DELETE'])
@handle_api_errors
def delete_contact(contact_id):
    """Delete a contact/lead"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    
    # Check if soft_delete is requested (query parameter)
    soft_delete = request.args.get('soft_delete', 'false').lower() == 'true'
    body_for_corr = request.get_json(silent=True) or {}
    correlation_id = get_or_create_correlation_id(request, body_for_corr)
    
    result = enhanced_crm_service.delete_contact(
        contact_id,
        user_id,
        soft_delete=soft_delete,
        correlation_id=correlation_id,
    )
    
    if not result.get('success'):
        error_code = result.get('error_code', 'DELETE_ERROR')
        status_code = 404 if error_code == 'CONTACT_NOT_FOUND' else 500
        return create_error_response(
            result.get('error', 'Failed to delete contact'),
            status_code,
            error_code,
            correlation_id=correlation_id,
        )
    
    return create_success_response(
        result.get('data', {}),
        result.get('data', {}).get('message') or 'Contact withdrawn successfully',
        correlation_id=correlation_id,
    )


@business_bp.route('/crm/leads/<int:lead_id>/score', methods=['POST'])
@handle_api_errors
def recalculate_lead_score(lead_id):
    """Recalculate lead score and quality"""
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    result = enhanced_crm_service.recalculate_lead_score(lead_id, user_id)
    if not result.get('success'):
        return create_error_response(result.get('error', 'Score recalculation failed'), 404, result.get('error_code', 'LEAD_NOT_FOUND'))
    return create_success_response(result.get('data', {}), 'Lead score recalculated')

@business_bp.route('/crm/leads/<int:lead_id>/activities', methods=['POST'])
@handle_api_errors
def add_lead_activity(lead_id):
    """Add an activity to a lead"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    data = request.get_json()
    if not data:
        return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

    activity_type = data.get('type', 'note')
    description = data.get('description', '')
    meta = {}
    if 'due_date' in data:
        meta['due_date'] = data['due_date']
    if 'completed' in data:
        meta['completed'] = data['completed']

    result = enhanced_crm_service.add_lead_activity(
        lead_id, user_id, activity_type, description, meta if meta else None
    )
    if not result.get('success'):
        ec = result.get('error_code', 'CRM_ACTIVITY_ERROR')
        status = 404 if ec == 'LEAD_NOT_FOUND' else 500
        return create_error_response(result.get('error', 'Failed to add activity'), status, ec)

    return create_success_response({'activity': result['data']}, 'Activity added successfully')

@business_bp.route('/crm/leads/<int:lead_id>/activities', methods=['GET'])
@handle_api_errors
def get_lead_activities(lead_id):
    """Get all activities for a lead"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    row = enhanced_crm_service.get_lead(lead_id, user_id)
    if not row:
        return create_error_response("Lead not found", 404, 'LEAD_NOT_FOUND')

    result = enhanced_crm_service.get_lead_activities(lead_id, user_id)
    if not result.get('success'):
        return create_error_response(result.get('error', 'Failed to load activities'), 500, 'CRM_ERROR')

    acts = result['data'].get('activities', [])
    serialized = [lead_dataclass_to_public_dict(a) for a in acts]
    return create_success_response({'activities': serialized}, 'Activities retrieved successfully')


@business_bp.route('/crm/leads/<int:lead_id>/events', methods=['GET'])
@handle_api_errors
def list_lead_crm_events(lead_id):
    """Append-only CRM event timeline for a lead (audit / integrations)."""
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    limit = min(max(request.args.get('limit', type=int, default=50), 1), 200)
    offset = max(request.args.get('offset', type=int, default=0), 0)
    result = enhanced_crm_service.list_crm_events(lead_id, user_id, limit=limit, offset=offset)
    if not result.get('success'):
        return create_error_response(
            result.get('error', 'Lead not found'),
            404,
            result.get('error_code', 'LEAD_NOT_FOUND'),
        )
    return create_success_response(result['data'], 'CRM events retrieved successfully')


@business_bp.route('/crm/pipeline', methods=['GET'])
@handle_api_errors
def get_pipeline():
    """Get CRM pipeline data"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

    pipeline = enhanced_crm_service.get_pipeline(user_id)
    return create_success_response({'pipeline': pipeline}, 'Pipeline retrieved successfully')

@business_bp.route('/crm/sync-gmail', methods=['POST'])
@handle_api_errors
def sync_gmail():
    """Sync Gmail emails and contacts to CRM"""
    try:
        user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_body=True)
        
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Check Gmail connection - check gmail_tokens table first (where tokens are actually stored)
        gmail_connected = False
        try:
            gmail_token_check = db_optimizer.execute_query("""
                SELECT id, user_id, access_token_enc, refresh_token_enc, is_active
                FROM gmail_tokens 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            if gmail_token_check and len(gmail_token_check) > 0:
                gmail_connected = True
        except Exception as check_error:
            logger.warning(f"Error checking gmail_tokens table: {check_error}")
        
        # Fallback: check oauth_tokens table
        if not gmail_connected:
            result = oauth_token_manager.get_token_status(user_id, "gmail")
            gmail_connected = result.get('success', False)
        
        if not gmail_connected:
            return create_error_response("Gmail connection required. Please connect your Gmail account first.", 403, 'OAUTH_REQUIRED')

        # Queue Gmail sync job using RQ (Redis Queue)
        sync_job_queued = False
        job_id = None
        try:
            from email_automation.gmail_sync_jobs import GmailSyncJobManager, should_process_gmail_sync_inline
            from core.redis_queues import get_email_queue
            
            sync_job_manager = GmailSyncJobManager()
            job_id = sync_job_manager.queue_sync_job(user_id, sync_type='manual')
            
            if job_id:
                sync_job_queued = True
                logger.info(f"Queued Gmail sync job {job_id} for user {user_id}")
                
                email_queue = get_email_queue()
                use_inline = should_process_gmail_sync_inline()
                # SQLite on Render: DB file is on the web disk only—no separate worker can run the job.
                # Redis enqueue would leave jobs pending forever unless GMAIL_SYNC_FORCE_INLINE=0 and a worker shares Postgres.
                if email_queue.is_connected() and not use_inline:
                    # Register the sync job task if not already registered
                    if 'process_gmail_sync' not in email_queue._registered_tasks:
                        email_queue.register_task('process_gmail_sync', sync_job_manager.process_sync_job)
                    
                    try:
                        from core.trace_context import get_trace_id
                        trace_id = get_trace_id()
                    except ImportError:
                        trace_id = None
                    
                    rq_job_id = email_queue.enqueue_job(
                        'process_gmail_sync',
                        {'job_id': job_id, 'trace_id': trace_id},
                        max_retries=3
                    )
                    logger.info(f"✅ Enqueued Gmail sync job {job_id} to Redis queue (job id: {rq_job_id})")
                else:
                    if use_inline:
                        logger.info(
                            "Gmail sync: processing in web process (SQLite or GMAIL_SYNC_FORCE_INLINE); "
                            "Redis queue bypassed so the job can access the database"
                        )
                    else:
                        logger.warning("⚠️ Redis not available, processing sync in background thread")
                    import threading
                    def process_in_background():
                        try:
                            result = sync_job_manager.process_sync_job(job_id)
                            if result.get('success'):
                                logger.info(f"✅ Sync job {job_id} completed")
                            else:
                                logger.error(f"❌ Sync job {job_id} failed: {result.get('error')}")
                        except Exception as e:
                            logger.error(f"❌ Sync job {job_id} error: {e}")
                    thread = threading.Thread(target=process_in_background, daemon=True)
                    thread.start()
                    logger.info(f"✅ Started background thread for sync job {job_id}")
        except Exception as job_error:
            logger.warning(f"Could not queue sync job (will try direct sync): {job_error}")
            import traceback
            logger.debug(f"Sync job queue error traceback: {traceback.format_exc()}")

        # Also trigger CRM lead sync (this syncs contacts from emails)
        sync_result = None
        try:
            sync_result = enhanced_crm_service.sync_gmail_leads(user_id)
        except Exception as sync_error:
            logger.error(f"CRM sync error for user {user_id}: {sync_error}")
            import traceback
            logger.error(f"CRM sync traceback: {traceback.format_exc()}")
            # If we queued a job, that's still success even if CRM sync fails
            if sync_job_queued:
                return create_success_response(
                    {'sync_job_queued': True, 'message': 'Gmail sync job queued successfully'},
                    'Gmail sync job queued'
                )
            return create_error_response(f"Failed to sync Gmail leads: {str(sync_error)}", 500, 'GMAIL_SYNC_ERROR')
        
        # Update user_sync_status to reflect sync was triggered
        try:
            db_optimizer.upsert_user_sync_status_pending(user_id)
        except Exception as status_error:
            logger.warning(f"Could not update sync status: {status_error}")
        
        if sync_result and sync_result.get('success'):
            data = sync_result.get('data', {})
            message = 'Gmail sync started successfully'
            if sync_job_queued:
                message += '. Email sync job queued.'
            else:
                # Direct sync completed (not queued) - update status to completed
                try:
                    # Count total synced emails for this user
                    email_count_result = db_optimizer.execute_query(
                        "SELECT COUNT(*) as total FROM synced_emails WHERE user_id = ?",
                        (user_id,)
                    )
                    total_emails = email_count_result[0]['total'] if email_count_result and email_count_result[0] else 0
                    
                    # Update user_sync_status to completed
                    db_optimizer.upsert_user_sync_status_completed(user_id, total_emails)
                    logger.info(f"✅ Updated user_sync_status to 'completed' for user {user_id} with {total_emails} emails")
                except Exception as status_update_error:
                    logger.warning(f"Could not update sync status to completed: {status_update_error}")
            
            return create_success_response(
                {
                    'contacts_synced': data.get('count', 0),
                    'sync_job_queued': sync_job_queued,
                    'message': message
                }, 
                message
            )
        else:
            # Even if CRM sync fails, if we queued a job, that's still success
            if sync_job_queued:
                return create_success_response(
                    {'sync_job_queued': True, 'message': 'Gmail sync job queued successfully'},
                    'Gmail sync job queued'
                )
            error_msg = sync_result.get('error', 'Unknown error') if sync_result else 'Sync failed'
            error_code = sync_result.get('error_code', 'GMAIL_SYNC_ERROR') if sync_result else 'GMAIL_SYNC_ERROR'
            return create_error_response(error_msg, 500, error_code)
            
    except Exception as e:
        logger.error(f"Gmail sync error: {e}")
        import traceback
        logger.error(f"Gmail sync traceback: {traceback.format_exc()}")
        return create_error_response("Failed to sync Gmail", 500, 'GMAIL_SYNC_ERROR')

@business_bp.route('/crm/sync-outlook', methods=['POST'])
@handle_api_errors
def sync_outlook():
    """Sync Outlook emails and contacts to CRM"""
    try:
        user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_body=True)
        
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Check Outlook connection
        outlook_connected = False
        try:
            outlook_token_check = db_optimizer.execute_query("""
                SELECT id FROM outlook_tokens 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            if outlook_token_check and len(outlook_token_check) > 0:
                outlook_connected = True
        except Exception as check_error:
            logger.warning(f"Error checking outlook_tokens table: {check_error}")
        
        if not outlook_connected:
            return create_error_response("Outlook connection required. Please connect your Outlook account first.", 403, 'OAUTH_REQUIRED')
        
        # Sync Outlook emails
        from integrations.outlook.outlook_sync import sync_outlook_emails
        sync_result = sync_outlook_emails(user_id, limit=50, days=30)
        
        if sync_result.get('success'):
            # Update sync status
            try:
                total_emails_result = db_optimizer.execute_query(
                    "SELECT COUNT(*) as total FROM synced_emails WHERE user_id = ? AND provider = 'outlook'",
                    (user_id,)
                )
                total_emails = total_emails_result[0]['total'] if total_emails_result and total_emails_result[0] else 0
                
                db_optimizer.upsert_user_sync_status_completed(user_id, total_emails)
            except Exception as status_error:
                logger.warning(f"Could not update sync status: {status_error}")
            
            return create_success_response({
                'emails_synced': sync_result.get('count', 0),
                'message': sync_result.get('message', 'Outlook sync completed')
            }, 'Outlook sync completed successfully')
        else:
            return create_error_response(
                sync_result.get('error', 'Outlook sync failed'), 
                500, 
                'OUTLOOK_SYNC_ERROR'
            )
            
    except Exception as e:
        logger.error(f"Outlook sync error: {e}")
        import traceback
        logger.error(f"Outlook sync traceback: {traceback.format_exc()}")
        return create_error_response("Failed to sync Outlook", 500, 'OUTLOOK_SYNC_ERROR')


def _gmail_metadata_message_to_email_dict(msg_detail):
    """Inbox list row without body (Gmail format=metadata)."""
    headers = msg_detail.get('payload', {}).get('headers', [])
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
    date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
    mid = msg_detail.get('id')
    snippet = msg_detail.get('snippet', '') or ''
    return {
        'id': mid,
        'subject': subject,
        'from': from_header,
        'from_name': from_header.split('<')[0].strip().replace('"', '') if '<' in from_header else from_header,
        'date': date,
        'snippet': snippet,
        'body': '',
        'unread': 'UNREAD' in msg_detail.get('labelIds', []),
        'has_attachments': 'attachmentId' in str(msg_detail.get('payload', {})),
        'thread_id': msg_detail.get('threadId'),
    }


def _gmail_full_message_to_email_dict(msg_detail, gmail_message_id):
    """Full parse for body + embedded-image proxy URLs (Gmail format=full)."""
    import base64

    from core.gmail_inline_images import (
        extract_embedded_image_map,
        rewrite_html_cid_to_proxy_urls,
    )

    headers = msg_detail['payload'].get('headers', [])
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
    date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
    body_html = ''
    body_text = ''

    def extract_from_part(part):
        nonlocal body_html, body_text
        mime_type = part.get('mimeType', '')
        if mime_type == 'text/html':
            data = part.get('body', {}).get('data', '')
            if data and not body_html:
                try:
                    body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.debug(f"Failed to decode HTML part: {e}")
        elif mime_type == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data and not body_text:
                try:
                    body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.debug(f"Failed to decode text part: {e}")
        if 'parts' in part:
            for subpart in part['parts']:
                extract_from_part(subpart)

    payload = msg_detail.get('payload', {})
    if 'parts' in payload:
        for part in payload['parts']:
            extract_from_part(part)
    else:
        extract_from_part(payload)
    embedded_images = extract_embedded_image_map(payload)
    body = body_html if body_html else body_text
    if body_html and embedded_images:
        body = rewrite_html_cid_to_proxy_urls(body_html, gmail_message_id, embedded_images)
    elif body_html:
        body = body_html
    return {
        'id': msg_detail.get('id', gmail_message_id),
        'subject': subject,
        'from': from_header,
        'from_name': from_header.split('<')[0].strip().replace('"', '') if '<' in from_header else from_header,
        'date': date,
        'snippet': msg_detail.get('snippet', ''),
        'body': body,
        'unread': 'UNREAD' in msg_detail.get('labelIds', []),
        'has_attachments': 'attachmentId' in str(msg_detail.get('payload', {})),
        'thread_id': msg_detail.get('threadId'),
    }


@business_bp.route('/email/messages', methods=['GET'])
@handle_api_errors
def get_emails():
    """Get emails for authenticated user"""
    try:
        user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
        
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        filter_type = request.args.get('filter', 'all')  # all, unread, read
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        use_synced = request.args.get('use_synced', 'true').lower() == 'true'  # Default to synced emails for speed
        # List views should omit full bodies (smaller JSON, faster DB). Detail: GET /email/messages/<id>
        include_body = request.args.get('include_body', 'false').lower() == 'true'

        # Enforce maximum limit to prevent unbounded queries (rulepack compliance)
        if limit > 500:
            limit = 500
        if limit < 1:
            limit = 1
        if offset < 0:
            offset = 0
        
        # Try to use synced emails first if requested and available
        if use_synced:
            try:
                # Apply unread/read in SQL so LIMIT returns that many matching rows (not fewer after Python filter).
                label_filter_sql = ""
                label_params = ()
                if filter_type == 'unread':
                    label_filter_sql = " AND labels LIKE ?"
                    label_params = ('%UNREAD%',)
                elif filter_type == 'read':
                    label_filter_sql = " AND (labels IS NULL OR labels = '' OR labels NOT LIKE ?)"
                    label_params = ('%UNREAD%',)

                # List without full body: SUBSTR only (less I/O + smaller payloads). Tests may mock `body` without body_preview.
                if include_body:
                    synced_sql = """
                        SELECT COALESCE(external_id, gmail_id) as email_id, provider, subject, sender, recipient, date, body, labels, is_read
                        FROM synced_emails
                        WHERE user_id = ?""" + label_filter_sql + """
                        ORDER BY date DESC
                        LIMIT ? OFFSET ?
                    """
                else:
                    synced_sql = """
                        SELECT COALESCE(external_id, gmail_id) as email_id, provider, subject, sender, recipient, date,
                               SUBSTR(COALESCE(body, ''), 1, 500) as body_preview, labels, is_read
                        FROM synced_emails
                        WHERE user_id = ?""" + label_filter_sql + """
                        ORDER BY date DESC
                        LIMIT ? OFFSET ?
                    """
                synced_params = (user_id,) + label_params + (limit, offset)
                synced_emails_data = db_optimizer.execute_query(synced_sql, synced_params)

                if synced_emails_data and len(synced_emails_data) > 0:
                    emails = []
                    count_sql = (
                        "SELECT COUNT(*) as total FROM synced_emails WHERE user_id = ?" + label_filter_sql
                    )
                    total_count_result = db_optimizer.execute_query(
                        count_sql, (user_id,) + label_params
                    )
                    total_count = total_count_result[0]['total'] if total_count_result else 0

                    for email_row in synced_emails_data:
                        labels: list = []
                        raw_labels = email_row.get('labels')
                        if raw_labels:
                            try:
                                labels = json.loads(raw_labels) if isinstance(raw_labels, str) else list(raw_labels)
                            except (json.JSONDecodeError, TypeError):
                                labels = []
                        if not isinstance(labels, list):
                            labels = []
                        # Prefer Gmail label list; if missing/empty, fall back to is_read (sync / mark-read)
                        if labels:
                            unread = 'UNREAD' in labels
                        else:
                            ir = email_row.get('is_read')
                            unread = not bool(ir) if ir is not None else False

                        email_id = email_row.get('email_id') or email_row.get('gmail_id')
                        provider = email_row.get('provider', 'gmail')

                        if include_body:
                            raw_body = email_row.get('body') or ''
                            snippet = _plain_email_snippet(raw_body, 160)
                            out_body = raw_body
                        else:
                            preview = email_row.get('body_preview')
                            if preview is None:
                                preview = (email_row.get('body') or '')[:500]
                            preview = preview or ''
                            snippet = _plain_email_snippet(preview, 160)
                            out_body = ''

                        emails.append({
                            'id': email_id,
                            'provider': provider,
                            'subject': email_row.get('subject', 'No Subject'),
                            'from': email_row.get('sender', 'Unknown'),
                            'from_name': email_row.get('sender', 'Unknown').split('<')[0].strip().replace('"', '') if '<' in email_row.get('sender', '') else email_row.get('sender', 'Unknown'),
                            'date': email_row.get('date', ''),
                            'snippet': snippet,
                            'body': out_body,
                            'unread': unread,
                            'has_attachments': False,  # Not stored in synced_emails
                            'thread_id': None  # Not stored in synced_emails
                        })
                    
                    if emails:
                        return create_success_response({
                            'emails': emails, 
                            'source': 'synced',
                            'pagination': {
                                'total_count': total_count,
                                'returned_count': len(emails),
                                'limit': limit,
                                'offset': offset,
                                'has_more': (offset + len(emails)) < total_count
                            }
                        }, 'Emails retrieved from sync')
            except Exception as sync_error:
                logger.warning(f"Could not use synced emails, falling back to Gmail API: {sync_error}")
        
        # Get Gmail service - this will check for tokens and handle connection
        try:
            from integrations.gmail.gmail_client import gmail_client
            
            # Try to get Gmail service - this will fail if no tokens exist
            try:
                gmail_service = gmail_client.get_gmail_service_for_user(user_id)
            except RuntimeError as e:
                # No valid credentials - Gmail not connected
                logger.info(f"Gmail not connected for user {user_id}: {e}")
                return create_success_response({'emails': [], 'message': 'Gmail not connected. Please connect your Gmail account first.'}, 'No emails available')
            
            # Match Gmail's Inbox tab: scope to in:inbox, then read/unread (same as Gmail UI)
            if filter_type == 'unread':
                query = 'in:inbox is:unread'
            elif filter_type == 'read':
                query = 'in:inbox is:read'
            else:
                query = 'in:inbox'
            
            # Get messages with pagination (rulepack compliance: Gmail API uses pageToken for pagination)
            # Note: Gmail API doesn't support offset directly, but we can use pageToken
            page_token = request.args.get('page_token', None)
            list_params = {
                'userId': 'me',
                'q': query,
                'maxResults': limit
            }
            if page_token:
                list_params['pageToken'] = page_token
            
            results = gmail_service.users().messages().list(**list_params).execute()
            
            messages = results.get('messages', [])
            emails = []

            if not include_body:

                def _fetch_metadata(mid: str):
                    try:
                        return gmail_service.users().messages().get(
                            userId='me',
                            id=mid,
                            format='metadata',
                            metadataHeaders=['Subject', 'From', 'Date'],
                        ).execute()
                    except Exception as e:
                        logger.warning("Gmail metadata fetch failed for %s: %s", mid, e)
                        return None

                # Sequential fetches: google-api-python-client / httplib2 are not reliably thread-safe;
                # parallel calls caused SSL errors and process crashes on some environments.
                by_id = {}
                if messages:
                    for m in messages:
                        md = _fetch_metadata(m["id"])
                        if md and md.get("id"):
                            by_id[md["id"]] = _gmail_metadata_message_to_email_dict(md)
                for m in messages:
                    row = by_id.get(m['id'])
                    if row:
                        emails.append(row)
            else:
                for msg in messages:
                    try:
                        msg_detail = gmail_service.users().messages().get(
                            userId='me',
                            id=msg['id'],
                            format='full',
                        ).execute()
                        emails.append(_gmail_full_message_to_email_dict(msg_detail, msg['id']))
                    except Exception as e:
                        logger.warning(f"Failed to process message {msg.get('id')}: {e}")
                        continue

            # Return with pagination metadata (Gmail API pagination)
            next_page_token = results.get('nextPageToken')
            return create_success_response({
                'emails': emails, 
                'source': 'gmail_api',
                'pagination': {
                    'returned_count': len(emails),
                    'limit': limit,
                    'has_more': bool(next_page_token),
                    'next_page_token': next_page_token
                }
            }, 'Emails retrieved successfully')
            
        except ImportError as e:
            logger.error(f"Gmail client not available: {e}")
            return create_error_response("Gmail service not available", 500, 'GMAIL_SERVICE_UNAVAILABLE')
        except RuntimeError as e:
            logger.error(f"Gmail service creation failed: {e}")
            return create_error_response(f"Gmail connection error: {str(e)}", 500, 'GMAIL_CONNECTION_ERROR')
        except Exception as e:
            logger.error(f"Error getting emails: {e}")
            return create_error_response(f"Failed to retrieve emails: {str(e)}", 500, 'EMAIL_RETRIEVAL_ERROR')
            
    except Exception as e:
        logger.error(f"Get emails error: {e}")
        return create_error_response("Failed to retrieve emails", 500, 'EMAIL_ERROR')


@business_bp.route('/email/messages/<email_id>', methods=['GET'])
@handle_api_errors
def get_email_message_detail(email_id):
    """Return one email with full body (synced DB first, then Gmail API)."""
    try:
        user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        rows = db_optimizer.execute_query(
            """
            SELECT COALESCE(external_id, gmail_id) as email_id, provider, subject, sender, recipient, date, body, labels, is_read
            FROM synced_emails
            WHERE user_id = ? AND (external_id = ? OR gmail_id = ?)
            LIMIT 1
            """,
            (user_id, email_id, email_id),
        )
        if rows:
            from core.gmail_inline_images import fix_legacy_embedded_image_api_paths

            email_row = rows[0]
            labels: list = []
            if email_row.get('labels'):
                try:
                    labels = json.loads(email_row['labels']) if isinstance(email_row['labels'], str) else list(email_row['labels'])
                except (json.JSONDecodeError, TypeError):
                    labels = []
            if not isinstance(labels, list):
                labels = []
            if labels:
                detail_unread = 'UNREAD' in labels
            else:
                ir = email_row.get('is_read')
                detail_unread = not bool(ir) if ir is not None else False
            eid = email_row.get('email_id')
            raw_body = fix_legacy_embedded_image_api_paths(email_row.get('body') or '')
            email = {
                'id': eid,
                'provider': email_row.get('provider', 'gmail'),
                'subject': email_row.get('subject', 'No Subject'),
                'from': email_row.get('sender', 'Unknown'),
                'from_name': email_row.get('sender', 'Unknown').split('<')[0].strip().replace('"', '')
                if '<' in email_row.get('sender', '')
                else email_row.get('sender', 'Unknown'),
                'date': email_row.get('date', ''),
                'snippet': _plain_email_snippet(raw_body, 200),
                'body': raw_body,
                'unread': detail_unread,
                'has_attachments': False,
                'thread_id': None,
            }
            return create_success_response({'email': email}, 'Email retrieved')

        try:
            from integrations.gmail.gmail_client import gmail_client

            gmail_service = gmail_client.get_gmail_service_for_user(user_id)
        except RuntimeError:
            return create_error_response("Email not found", 404, 'EMAIL_NOT_FOUND')

        try:
            msg_detail = gmail_service.users().messages().get(
                userId='me', id=email_id, format='full'
            ).execute()
        except Exception:
            return create_error_response("Email not found", 404, 'EMAIL_NOT_FOUND')

        email = _gmail_full_message_to_email_dict(msg_detail, email_id)
        email['provider'] = 'gmail'
        return create_success_response({'email': email}, 'Email retrieved from Gmail')
    except Exception as e:
        logger.error(f"get_email_message_detail error: {e}")
        return create_error_response("Failed to load email", 500, 'EMAIL_DETAIL_ERROR')


@business_bp.route('/ai/analyze-email', methods=['POST'])
@handle_api_errors
def analyze_email():
    """Analyze email using AI"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        data = request.get_json() or {}
        email_id = data.get('email_id')
        subject = data.get('subject', '')
        content = data.get('content', '')
        from_email = data.get('from', '')
        
        if not content:
            return create_error_response("Email content is required", 400, 'MISSING_CONTENT')

        tier_limit_error = _check_tier_usage_cap(user_id, "ai_responses", projected_increment=1)
        if tier_limit_error:
            return tier_limit_error

        budget_decision = ai_budget_guardrails.evaluate(user_id, projected_increment=1)
        if not budget_decision.allowed:
            return create_error_response(
                "AI monthly budget cap reached. Upgrade or wait until next billing period."
                if budget_decision.reason == "monthly_budget_cap_reached"
                else "AI monthly budget approval required.",
                402,
                "AI_BUDGET_SOFT_STOP"
            )
        
        try:
            from email_automation.ai_assistant import MinimalAIEmailAssistant
            ai_assistant = MinimalAIEmailAssistant()
            
            if not ai_assistant.is_enabled():
                return create_error_response("AI assistant is not available", 503, 'AI_UNAVAILABLE')
            
            analysis = ai_assistant.analyze_incoming_email(
                sender_email=from_email,
                sender_name=from_email,
                subject=subject,
                body=content,
                thread_history=data.get("thread_history") if isinstance(data.get("thread_history"), list) else [],
                crm_lead_data=data.get("crm_lead_data") if isinstance(data.get("crm_lead_data"), dict) else {},
                business_context=data.get("business_context") if isinstance(data.get("business_context"), dict) else None,
                user_id=user_id,
            )
            ai_budget_guardrails.record_ai_usage(user_id, 1)
            
            return create_success_response(analysis, 'Email analyzed successfully')
            
        except Exception as e:
            error_msg = str(e)
            # Check for specific error types
            if 'insufficient_quota' in error_msg.lower() or 'quota' in error_msg.lower() or 'billing' in error_msg.lower():
                logger.error(f"AI analysis error: OpenAI quota/billing issue - {error_msg}")
                return create_error_response(
                    "AI analysis unavailable: Your OpenAI account has insufficient credits. Please add credits to your OpenAI account to use AI features.",
                    503,
                    'AI_QUOTA_EXCEEDED'
                )
            elif '401' in error_msg or 'unauthorized' in error_msg.lower():
                logger.error(f"AI analysis error: Invalid API key - {error_msg}")
                return create_error_response(
                    "AI analysis unavailable: Invalid OpenAI API key. Please check your OPENAI_API_KEY environment variable.",
                    503,
                    'AI_AUTH_ERROR'
                )
            else:
                logger.error(f"AI analysis error: {error_msg}")
                return create_error_response(f"AI analysis failed: {error_msg}", 500, 'AI_ANALYSIS_ERROR')
            
    except Exception as e:
        logger.error(f"Analyze email error: {e}")
        return create_error_response("Failed to analyze email", 500, 'ANALYSIS_ERROR')

@business_bp.route('/ai/generate-reply', methods=['POST'])
@handle_api_errors
def generate_reply():
    """Generate AI reply for email"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        data = request.get_json() or {}
        email_id = data.get('email_id')
        subject = data.get('subject', '')
        content = data.get('content', '')
        from_email = data.get('from', '')
        
        if not content:
            return create_error_response("Email content is required", 400, 'MISSING_CONTENT')

        tier_limit_error = _check_tier_usage_cap(user_id, "ai_responses", projected_increment=1)
        if tier_limit_error:
            return tier_limit_error

        budget_decision = ai_budget_guardrails.evaluate(user_id, projected_increment=1)
        if not budget_decision.allowed:
            return create_error_response(
                "AI monthly budget cap reached. Upgrade or wait until next billing period."
                if budget_decision.reason == "monthly_budget_cap_reached"
                else "AI monthly budget approval required.",
                402,
                "AI_BUDGET_SOFT_STOP"
            )
        
        try:
            from email_automation.ai_assistant import MinimalAIEmailAssistant
            ai_assistant = MinimalAIEmailAssistant()
            
            if not ai_assistant.is_enabled():
                return create_error_response("AI assistant is not available", 503, 'AI_UNAVAILABLE')
            
            # Extract sender name from email
            sender_name = from_email.split('<')[0].strip().replace('"', '') if '<' in from_email else from_email
            
            # Classify email to get intent for better reply generation
            classification = ai_assistant.classify_email_intent(content, subject)
            intent = classification.get('intent', 'general') if classification else 'general'
            
            # Generate reply
            reply = ai_assistant.generate_response(content, sender_name, subject, intent)
            ai_budget_guardrails.record_ai_usage(user_id, 1)
            
            return create_success_response({'reply': reply}, 'Reply generated successfully')
            
        except Exception as e:
            error_msg = str(e)
            # Check for specific error types
            if 'insufficient_quota' in error_msg.lower() or 'quota' in error_msg.lower() or 'billing' in error_msg.lower():
                logger.error(f"Reply generation error: OpenAI quota/billing issue - {error_msg}")
                return create_error_response(
                    "Reply generation unavailable: Your OpenAI account has insufficient credits. Please add credits to your OpenAI account to use AI features.",
                    503,
                    'AI_QUOTA_EXCEEDED'
                )
            elif '401' in error_msg or 'unauthorized' in error_msg.lower():
                logger.error(f"Reply generation error: Invalid API key - {error_msg}")
                return create_error_response(
                    "Reply generation unavailable: Invalid OpenAI API key. Please check your OPENAI_API_KEY environment variable.",
                    503,
                    'AI_AUTH_ERROR'
                )
            else:
                logger.error(f"Reply generation error: {error_msg}")
                return create_error_response(f"Reply generation failed: {error_msg}", 500, 'REPLY_GENERATION_ERROR')
            
    except Exception as e:
        logger.error(f"Generate reply error: {e}")
        return create_error_response("Failed to generate reply", 500, 'REPLY_ERROR')

@business_bp.route('/email/send', methods=['POST'])
@handle_api_errors
def send_email():
    """Send email via Gmail API"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        # Validate required fields
        to_email = data.get('to')
        subject = data.get('subject', '')
        body = data.get('body', '')

        if not to_email:
            return create_error_response("Recipient email (to) is required", 400, 'MISSING_RECIPIENT')
        if not body:
            return create_error_response("Email body is required", 400, 'MISSING_BODY')

        tier_limit_error = _check_tier_usage_cap(user_id, "email_processing", projected_increment=1)
        if tier_limit_error:
            return tier_limit_error

        # Gmail OAuth tokens live in gmail_tokens (gmail_client). Do not gate on oauth_tokens alone.
        from integrations.gmail.gmail_client import gmail_client
        import base64

        try:
            gmail_service = gmail_client.get_gmail_service_for_user(user_id)
        except RuntimeError as e:
            logger.error(
                "Send email: cannot build Gmail service for user %s: %s",
                user_id,
                e,
                exc_info=True,
            )
            return create_error_response(
                "Gmail connection required. Please connect your Gmail account first.",
                403,
                "GMAIL_NOT_CONNECTED",
            )

        try:
            message = {
                "raw": base64.urlsafe_b64encode(
                    f"To: {to_email}\r\n"
                    f"Subject: {subject}\r\n"
                    f"Content-Type: text/plain; charset=UTF-8\r\n"
                    f"\r\n"
                    f"{body}".encode("utf-8")
                ).decode("utf-8")
            }

            sent_message = (
                gmail_service.users().messages().send(userId="me", body=message).execute()
            )
            record_monthly_usage(user_id, "email_processing", 1, db=db_optimizer)

            return create_success_response(
                {
                    "message_id": sent_message.get("id"),
                    "thread_id": sent_message.get("threadId"),
                    "to": to_email,
                    "subject": subject,
                },
                "Email sent successfully",
            )

        except Exception as e:
            logger.error("Failed to send email (user_id=%s): %s", user_id, e, exc_info=True)
            error_msg = str(e)
            if "invalid_grant" in error_msg.lower() or "token" in error_msg.lower():
                return create_error_response(
                    "Gmail authentication expired. Please reconnect your Gmail account.",
                    401,
                    "GMAIL_AUTH_EXPIRED",
                )
            # Google API often returns HttpError with .status / .reason
            status = getattr(e, "status_code", None) or getattr(
                getattr(e, "resp", None), "status", None
            )
            if status == 403:
                return create_error_response(
                    "Gmail refused to send (403). Check account permissions or reconnect Gmail.",
                    403,
                    "GMAIL_SEND_FORBIDDEN",
                )
            return create_error_response(
                f"Failed to send email: {error_msg}", 500, "EMAIL_SEND_ERROR"
            )
            
    except Exception as e:
        logger.error(f"Send email error: {e}")
        return create_error_response("Failed to send email", 500, 'EMAIL_SEND_ERROR')


@business_bp.route('/privacy/settings', methods=['GET'])
@handle_api_errors
def get_privacy_settings_route():
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    ps = _ensure_privacy_settings_row(user_id)
    if not ps:
        return create_error_response("Privacy settings unavailable", 500, 'PRIVACY_SETTINGS_ERROR')
    return create_success_response(_serialize_privacy_settings(ps), "Privacy settings retrieved")


@business_bp.route('/privacy/settings', methods=['PUT'])
@handle_api_errors
def update_privacy_settings_route():
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    data = request.get_json() or {}
    allowed = (
        'data_retention_days',
        'email_scanning_enabled',
        'personal_email_exclusion',
        'auto_labeling_enabled',
        'lead_detection_enabled',
        'analytics_tracking_enabled',
    )
    updates = {k: data[k] for k in allowed if k in data}
    if not updates:
        return create_error_response("No valid fields to update", 400, 'NO_UPDATES')
    _ensure_privacy_settings_row(user_id)
    result = privacy_manager.update_privacy_settings(user_id, **updates)
    if not result.get('success'):
        return create_error_response(
            result.get('error', 'Update failed'),
            400,
            result.get('error_code', 'UPDATE_ERROR'),
        )
    settings = result.get('settings')
    return create_success_response(
        {'settings': _serialize_privacy_settings(settings)},
        'Privacy settings updated',
    )


@business_bp.route('/privacy/data-summary', methods=['GET'])
@handle_api_errors
def get_privacy_data_summary_route():
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    _ensure_privacy_settings_row(user_id)
    summary = privacy_manager.get_data_summary(user_id)
    if not summary.get('success'):
        return create_error_response(
            summary.get('error', 'Failed to load summary'),
            500,
            summary.get('error_code', 'SUMMARY_ERROR'),
        )
    ds = summary['data_summary']
    ps = ds.get('privacy_settings')
    payload = {
        'leads_count': ds['leads_count'],
        'activities_count': ds['activities_count'],
        'sync_records_count': ds['sync_records_count'],
        'privacy_settings': _serialize_privacy_settings(ps) if isinstance(ps, PrivacySettings) else ps,
        'consents': ds.get('consents'),
    }
    return create_success_response(payload, "Data summary retrieved")


@business_bp.route('/privacy/consents', methods=['GET'])
@handle_api_errors
def get_privacy_consents_route():
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    rows = privacy_manager.get_privacy_consents(user_id)
    return create_success_response(
        {'consents': [_serialize_privacy_consent(c) for c in rows]},
        "Consents retrieved",
    )


@business_bp.route('/privacy/cleanup', methods=['POST'])
@handle_api_errors
def privacy_cleanup_route():
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    result = privacy_manager.cleanup_expired_data(user_id)
    if not result.get('success'):
        return create_error_response(
            result.get('error', 'Cleanup failed'),
            400,
            result.get('error_code', 'CLEANUP_ERROR'),
        )
    return create_success_response(
        {'total_deleted': result.get('total_deleted', 0), 'cleanup_results': result.get('cleanup_results')},
        result.get('message', 'Cleanup completed'),
    )


@business_bp.route('/privacy/export', methods=['GET'])
@handle_api_errors
def privacy_export_route():
    user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    result = privacy_manager.export_user_data(user_id)
    if not result.get('success'):
        return create_error_response(
            result.get('error', 'Export failed'),
            500,
            result.get('error_code', 'EXPORT_ERROR'),
        )
    export_data = result.get('export_data') or {}
    try:
        safe = json.loads(json.dumps(export_data, default=str))
    except (TypeError, ValueError) as e:
        logger.warning("Privacy export JSON fallback: %s", e)
        safe = export_data
    return create_success_response(safe, "Export ready")


@business_bp.route('/privacy/delete', methods=['POST'])
@handle_api_errors
def privacy_delete_route():
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    data = request.get_json() or {}
    if data.get('confirmation') != 'DELETE_ALL_MY_DATA':
        return create_error_response("Invalid confirmation phrase", 400, 'INVALID_CONFIRMATION')
    result = privacy_manager.delete_user_data(user_id)
    if not result.get('success'):
        return create_error_response(
            result.get('error', 'Deletion failed'),
            500,
            result.get('error_code', 'DELETION_ERROR'),
        )
    return create_success_response(result.get('deleted_records', {}), "User data deleted")


@business_bp.route('/email/archive', methods=['POST'])
@handle_api_errors
def archive_email():
    """Archive an email (remove from inbox)"""
    try:
        user_id = get_current_user_id()
        # Fallback: allow user_id from request body for development/testing
        if not user_id:
            data = request.get_json() or {}
            user_id_raw = data.get('user_id')
            if user_id_raw:
                try:
                    user_id = int(user_id_raw)
                except (ValueError, TypeError):
                    user_id = None
            if user_id:
                user_check = db_optimizer.execute_query(
                    "SELECT id FROM users WHERE id = ? AND is_active = 1 LIMIT 1",
                    (user_id,)
                )
                if not user_check:
                    return create_error_response("Invalid user ID", 401, 'INVALID_USER_ID')
        
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        data = request.get_json() or {}
        email_id = data.get('email_id')
        
        if not email_id:
            return create_error_response("Email ID is required", 400, 'MISSING_EMAIL_ID')
        
        # Get Gmail service
        try:
            from integrations.gmail.gmail_client import gmail_client
            gmail_service = gmail_client.get_gmail_service_for_user(user_id)
            
            # Archive by removing INBOX label
            gmail_service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            
            logger.info(f"✅ Archived email {email_id} for user {user_id}")
            return create_success_response(
                {'email_id': email_id, 'archived': True},
                'Email archived successfully'
            )
            
        except ImportError as e:
            logger.error(f"Gmail client not available: {e}")
            return create_error_response("Gmail service not available", 500, 'GMAIL_SERVICE_UNAVAILABLE')
        except RuntimeError as e:
            logger.error(f"Gmail service creation failed: {e}")
            return create_error_response(f"Gmail connection error: {str(e)}", 500, 'GMAIL_CONNECTION_ERROR')
        except Exception as e:
            logger.error(f"Failed to archive email: {e}")
            return create_error_response(f"Failed to archive email: {str(e)}", 500, 'EMAIL_ARCHIVE_ERROR')
            
    except Exception as e:
        logger.error(f"Archive email error: {e}")
        return create_error_response("Failed to archive email", 500, 'EMAIL_ARCHIVE_ERROR')


@business_bp.route('/email/mark-read', methods=['POST'])
@handle_api_errors
def mark_email_read():
    """Mark a message as read in Gmail (remove UNREAD label) and update local synced_emails if present."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            data = request.get_json() or {}
            user_id_raw = data.get('user_id')
            if user_id_raw:
                try:
                    user_id = int(user_id_raw)
                except (ValueError, TypeError):
                    user_id = None
            if user_id:
                user_check = db_optimizer.execute_query(
                    "SELECT id FROM users WHERE id = ? AND is_active = 1 LIMIT 1",
                    (user_id,),
                )
                if not user_check:
                    return create_error_response("Invalid user ID", 401, 'INVALID_USER_ID')
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json() or {}
        email_id = data.get('email_id')
        if not email_id:
            return create_error_response("Email ID is required", 400, 'MISSING_EMAIL_ID')

        try:
            from integrations.gmail.gmail_client import gmail_client

            gmail_service = gmail_client.get_gmail_service_for_user(user_id)
            gmail_service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['UNREAD']},
            ).execute()
        except ImportError as e:
            logger.error(f"Gmail client not available: {e}")
            return create_error_response("Gmail service not available", 500, 'GMAIL_SERVICE_UNAVAILABLE')
        except RuntimeError as e:
            logger.error(f"Gmail service creation failed: {e}")
            return create_error_response(f"Gmail connection error: {str(e)}", 500, 'GMAIL_CONNECTION_ERROR')
        except Exception as e:
            logger.error(f"Failed to mark email read: {e}")
            return create_error_response(f"Failed to mark email read: {str(e)}", 500, 'EMAIL_MARK_READ_ERROR')

        rows = db_optimizer.execute_query(
            """
            SELECT labels FROM synced_emails
            WHERE user_id = ? AND (external_id = ? OR gmail_id = ?) AND COALESCE(provider, 'gmail') = 'gmail'
            LIMIT 1
            """,
            (user_id, email_id, email_id),
        )
        if rows:
            raw = rows[0].get('labels') or '[]'
            try:
                labels = json.loads(raw) if isinstance(raw, str) else list(raw)
            except (json.JSONDecodeError, TypeError):
                labels = []
            if not isinstance(labels, list):
                labels = []
            labels = [x for x in labels if x != 'UNREAD']
            db_optimizer.execute_query(
                """
                UPDATE synced_emails
                SET labels = ?, is_read = 1
                WHERE user_id = ? AND (external_id = ? OR gmail_id = ?)
                """,
                (json.dumps(labels), user_id, email_id, email_id),
                fetch=False,
            )

        logger.info("Marked email %s as read for user %s", email_id, user_id)
        return create_success_response(
            {'email_id': email_id, 'read': True},
            'Email marked as read',
        )
    except Exception as e:
        logger.error(f"Mark read error: {e}")
        return create_error_response("Failed to mark email read", 500, 'EMAIL_MARK_READ_ERROR')


# Automation Routes
@business_bp.route('/automation/rules', methods=['GET'])
@handle_api_errors
def get_automation_rules():
    """Get automation rules for authenticated user"""
    try:
        user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        # Get pagination parameters (rulepack compliance: all list endpoints must be paginated)
        limit = request.args.get('limit', type=int, default=100)
        offset = request.args.get('offset', type=int, default=0)
        status = request.args.get('status', type=str)
        
        # Enforce maximum limit
        if limit > 500:
            limit = 500
        if limit < 1:
            limit = 1
        
        result = automation_engine.get_automation_rules(user_id, status=status, limit=limit, offset=offset)
        
        if result['success']:
            data = result['data']
            # Serialize AutomationRule dataclass objects to dicts
            from dataclasses import asdict
            rules_list = []
            for rule in data.get('rules', []):
                if hasattr(rule, '__dataclass_fields__'):
                    rule_dict = asdict(rule)
                    # Convert enums to strings
                    if 'trigger_type' in rule_dict and hasattr(rule_dict['trigger_type'], 'value'):
                        rule_dict['trigger_type'] = rule_dict['trigger_type'].value
                    if 'action_type' in rule_dict and hasattr(rule_dict['action_type'], 'value'):
                        rule_dict['action_type'] = rule_dict['action_type'].value
                    if 'status' in rule_dict and hasattr(rule_dict['status'], 'value'):
                        rule_dict['status'] = rule_dict['status'].value
                    # Convert datetime to ISO strings
                    for date_field in ['created_at', 'updated_at', 'last_executed']:
                        if date_field in rule_dict and rule_dict[date_field] and hasattr(rule_dict[date_field], 'isoformat'):
                            rule_dict[date_field] = rule_dict[date_field].isoformat()
                    rules_list.append(rule_dict)
                else:
                    rules_list.append(rule)
            
            return create_success_response({
                'rules': rules_list,
                'pagination': {
                    'total_count': data.get('total_count', len(rules_list)),
                    'count': data.get('count', len(rules_list)),
                    'limit': limit,
                    'offset': offset,
                    'has_more': data.get('has_more', False)
                }
            }, 'Automation rules retrieved successfully')
        else:
            return create_error_response(result.get('error', 'Failed to retrieve rules'), 500, 'AUTOMATION_ERROR')
        
    except Exception as e:
        logger.error(f"Get automation rules error: {e}")
        return create_error_response("Failed to retrieve automation rules", 500, 'AUTOMATION_ERROR')

@business_bp.route('/automation/rules', methods=['POST'])
@handle_api_errors
def create_automation_rule():
    """Create a new automation rule"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        # Validate required fields
        if 'trigger_type' not in data or 'action_type' not in data:
            return create_error_response("Trigger and action types are required", 400, 'MISSING_FIELDS')

        rule_data = {
            'name': data.get('name', 'Unnamed Rule'),
            'description': data.get('description', ''),
            'trigger_type': data['trigger_type'],
            'trigger_conditions': data.get('trigger_conditions', data.get('conditions', {})),
            'action_type': data['action_type'],
            'action_parameters': data.get('action_parameters', {}),
            'status': 'active' if data.get('status') != 'inactive' and data.get('is_active', True) else 'inactive'
        }

        result = automation_engine.create_automation_rule(user_id, rule_data)
        
        if result.get('success'):
            rule_id = result.get('data', {}).get('rule_id')
            log_activity_event(
                user_id,
                'automation_rule_created',
                message=f"Automation rule created: {rule_data.get('name')}",
                metadata={
                    'rule_id': rule_id,
                    'trigger_type': rule_data.get('trigger_type'),
                    'action_type': rule_data.get('action_type'),
                    'status': rule_data.get('status')
                },
                request=request
            )
            # Fetch the created rule to return full data
            rules_result = automation_engine.get_automation_rules(user_id)
            if rules_result.get('success'):
                created_rule = next((r for r in rules_result['data']['rules'] if r.id == rule_id), None)
                if created_rule:
                    # Convert AutomationRule dataclass to dict
                    from dataclasses import asdict
                    rule_dict = asdict(created_rule)
                    # Convert enums to strings
                    rule_dict['trigger_type'] = rule_dict['trigger_type'].value if hasattr(rule_dict['trigger_type'], 'value') else str(rule_dict['trigger_type'])
                    rule_dict['action_type'] = rule_dict['action_type'].value if hasattr(rule_dict['action_type'], 'value') else str(rule_dict['action_type'])
                    rule_dict['status'] = rule_dict['status'].value if hasattr(rule_dict['status'], 'value') else str(rule_dict['status'])
                    # Convert datetime to ISO strings
                    if rule_dict.get('created_at'):
                        rule_dict['created_at'] = rule_dict['created_at'].isoformat() if hasattr(rule_dict['created_at'], 'isoformat') else str(rule_dict['created_at'])
                    if rule_dict.get('updated_at'):
                        rule_dict['updated_at'] = rule_dict['updated_at'].isoformat() if hasattr(rule_dict['updated_at'], 'isoformat') else str(rule_dict['updated_at'])
                    if rule_dict.get('last_executed'):
                        rule_dict['last_executed'] = rule_dict['last_executed'].isoformat() if hasattr(rule_dict['last_executed'], 'isoformat') else str(rule_dict['last_executed'])
                    return create_success_response({'rule': rule_dict}, 'Automation rule created successfully')
            return create_success_response(result.get('data', {}), 'Automation rule created successfully')
        else:
            error_msg = result.get('error', 'Failed to create automation rule')
            error_code = result.get('error_code', 'AUTOMATION_CREATE_ERROR')
            http_status = 400 if error_code == 'INVALID_TRIGGER_CONDITIONS' else 500
            return create_error_response(error_msg, http_status, error_code)
            
    except Exception as e:
        logger.error(f"Create automation rule error: {e}")
        return create_error_response("Failed to create automation rule", 500, 'AUTOMATION_ERROR')

@business_bp.route('/automation/rules/<int:rule_id>', methods=['PUT'])
@handle_api_errors
def update_automation_rule(rule_id):
    """Update an existing automation rule"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        # Check if rule belongs to user
        rule_check = db_optimizer.execute_query(
            "SELECT user_id FROM automation_rules WHERE id = ?",
            (rule_id,)
        )
        if not rule_check or len(rule_check) == 0:
            return create_error_response("Automation rule not found", 404, 'RULE_NOT_FOUND')
        
        if rule_check[0]['user_id'] != user_id:
            return create_error_response("Automation rule not found", 404, 'RULE_NOT_FOUND')

        # Prepare updates - map frontend fields to backend fields
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'description' in data:
            updates['description'] = data['description']
        if 'trigger_conditions' in data:
            updates['trigger_conditions'] = data['trigger_conditions']
        if 'action_parameters' in data:
            updates['action_parameters'] = data['action_parameters']
        if 'status' in data:
            updates['status'] = data['status']

        result = automation_engine.update_automation_rule(rule_id, user_id, updates)
        
        if result.get('success'):
            data = result.get('data', {})
            rule_obj = data.get('rule')
            rule_name = updates.get('name')
            if rule_obj and not rule_name:
                try:
                    rule_name = getattr(rule_obj, 'name', None)
                except Exception:
                    rule_name = None
            log_activity_event(
                user_id,
                'automation_rule_updated',
                message=f"Automation rule updated: {rule_name or f'#{rule_id}'}",
                metadata={'rule_id': rule_id, 'updates': list(updates.keys())},
                request=request
            )
            if rule_obj:
                from dataclasses import asdict
                rule_dict = asdict(rule_obj)
                rule_dict['trigger_type'] = rule_dict['trigger_type'].value if hasattr(rule_dict['trigger_type'], 'value') else str(rule_dict['trigger_type'])
                rule_dict['action_type'] = rule_dict['action_type'].value if hasattr(rule_dict['action_type'], 'value') else str(rule_dict['action_type'])
                rule_dict['status'] = rule_dict['status'].value if hasattr(rule_dict['status'], 'value') else str(rule_dict['status'])
                if rule_dict.get('created_at'):
                    rule_dict['created_at'] = rule_dict['created_at'].isoformat() if hasattr(rule_dict['created_at'], 'isoformat') else str(rule_dict['created_at'])
                if rule_dict.get('updated_at'):
                    rule_dict['updated_at'] = rule_dict['updated_at'].isoformat() if hasattr(rule_dict['updated_at'], 'isoformat') else str(rule_dict['updated_at'])
                if rule_dict.get('last_executed'):
                    rule_dict['last_executed'] = rule_dict['last_executed'].isoformat() if hasattr(rule_dict['last_executed'], 'isoformat') else str(rule_dict['last_executed'])
                data = {**data, 'rule': rule_dict}
            return create_success_response(data, 'Automation rule updated successfully')
        else:
            error_msg = result.get('error', 'Failed to update automation rule')
            error_code = result.get('error_code', 'AUTOMATION_UPDATE_ERROR')
            http_status = 400 if error_code == 'INVALID_TRIGGER_CONDITIONS' else 500
            return create_error_response(error_msg, http_status, error_code)
            
    except Exception as e:
        logger.error(f"Update automation rule error: {e}")
        return create_error_response("Failed to update automation rule", 500, 'AUTOMATION_ERROR')

@business_bp.route('/automation/trigger-condition-metadata', methods=['GET'])
@handle_api_errors
def get_trigger_condition_metadata():
    """Fields and operators for trigger IF-groups (Automation Studio)."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        result = automation_engine.get_trigger_condition_metadata()
        if result.get('success'):
            return create_success_response(result['data'], 'Trigger condition metadata retrieved')
        return create_error_response(
            result.get('error', 'Failed to load trigger metadata'),
            500,
            'TRIGGER_METADATA_ERROR',
        )
    except Exception as e:
        logger.error(f"Get trigger condition metadata error: {e}")
        return create_error_response("Failed to retrieve trigger metadata", 500, 'TRIGGER_METADATA_ERROR')

@business_bp.route('/automation/suggestions', methods=['GET'])
@handle_api_errors
def get_automation_suggestions():
    """Get AI-powered automation suggestions"""
    try:
        user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        result = automation_engine.get_automation_suggestions(user_id)
        
        if result['success']:
            return create_success_response(result['data'], 'Automation suggestions retrieved successfully')
        else:
            return create_error_response(result.get('error', 'Failed to retrieve suggestions'), 500, 'AUTOMATION_SUGGESTIONS_ERROR')
        
    except Exception as e:
        logger.error(f"Get automation suggestions error: {e}")
        return create_error_response("Failed to retrieve automation suggestions", 500, 'AUTOMATION_SUGGESTIONS_ERROR')

@business_bp.route('/automation/capabilities', methods=['GET'])
@handle_api_errors
def get_automation_capabilities():
    """Get per-action capability flags (implemented | partial | stub) for UI. Requires auth."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        result = automation_engine.get_action_capabilities()
        if result['success']:
            return create_success_response(result['data'], 'Capabilities retrieved')
        return create_error_response(result.get('error', 'Failed to get capabilities'), 500, 'AUTOMATION_CAPABILITIES_ERROR')
    except Exception as e:
        logger.error(f"Get automation capabilities error: {e}")
        return create_error_response("Failed to retrieve capabilities", 500, 'AUTOMATION_CAPABILITIES_ERROR')

@business_bp.route('/automation/execute', methods=['POST'])
@handle_api_errors
def execute_automation():
    """Execute automation rules. Queues to Redis when available; otherwise runs synchronously."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        if not _require_paid_plan(user_id):
            return create_error_response("Plan limit exceeded", 402, 'PLAN_LIMIT_EXCEEDED')

        data = request.get_json()
        if not data:
            return create_error_response("Request body cannot be empty", 400, 'EMPTY_REQUEST_BODY')

        if 'rule_ids' not in data:
            return create_error_response("Rule IDs are required", 400, 'MISSING_RULE_IDS')

        rule_ids = data['rule_ids']
        idempotency_key = data.get('idempotency_key')
        correlation_id = get_or_create_correlation_id(request, data)

        from services.automation_queue import automation_job_manager
        job_id = automation_job_manager.queue_automation_job(
            user_id,
            rule_ids=rule_ids,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        if not job_id:
            return create_error_response(
                "Duplicate run (idempotency) or queue failed",
                409,
                'DUPLICATE_OR_QUEUE_FAILED',
                correlation_id=correlation_id,
            )

        try:
            from core.redis_queues import get_automation_queue
            aq = get_automation_queue()
            if aq.is_connected():
                if 'process_automation_run' not in aq._registered_tasks:
                    from services.automation_queue import process_automation_run
                    aq.register_task('process_automation_run', process_automation_run)
                aq.enqueue_job('process_automation_run', {'job_id': job_id}, max_retries=2)
                return create_success_response(
                    {'job_id': job_id, 'status': 'queued'},
                    'Automation job queued',
                    correlation_id=correlation_id,
                )
        except Exception as queue_err:
            logger.warning("Automation queue enqueue failed, running sync: %s", queue_err)

        result = automation_job_manager.process_automation_job(job_id)
        if result.get('error_code') == 'NOT_IMPLEMENTED':
            return create_error_response(
                result.get('error', 'Action not implemented'),
                501,
                'NOT_IMPLEMENTED',
                correlation_id=correlation_id,
            )
        if not result.get('success'):
            return create_error_response(
                result.get('error', 'Execution failed'),
                500,
                'AUTOMATION_EXECUTION_ERROR',
                correlation_id=correlation_id,
            )
        return create_success_response(
            {
                'job_id': job_id,
                'status': 'completed',
                'execution_results': result.get('execution_results', []),
            },
            'Automation rules executed successfully',
            correlation_id=correlation_id,
        )
    except Exception as e:
        logger.error(f"Execute automation error: {e}")
        return create_error_response(
            "Failed to execute automation rules",
            500,
            'AUTOMATION_EXECUTION_ERROR',
        )

@business_bp.route('/automation/jobs/<job_id>', methods=['GET'])
@handle_api_errors
def get_automation_job_status(job_id):
    """Get automation job status and result."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        from services.automation_queue import automation_job_manager
        status = automation_job_manager.get_job_status(job_id, user_id=user_id)
        if not status:
            return create_error_response("Job not found", 404, 'JOB_NOT_FOUND')
        cid = status.get("correlation_id")
        return create_success_response(status, 'Job status retrieved', correlation_id=cid)
    except Exception as e:
        logger.error(f"Get automation job status error: {e}")
        return create_error_response("Failed to get job status", 500, 'AUTOMATION_JOB_ERROR')


@business_bp.route('/debug/correlation/<string:correlation_id>', methods=['GET'])
@handle_api_errors
def debug_correlation_trace(correlation_id):
    """Stitched view of domain event rows for one correlation_id (current user only)."""
    if os.getenv("FIKIRI_CORRELATION_TRACE", "1").lower() in ("0", "false", "no"):
        return create_error_response("Correlation trace disabled", 404, "TRACE_DISABLED")
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")
    trace = fetch_correlation_trace(user_id, correlation_id)
    if trace.get("error") == "invalid_correlation_id":
        return create_error_response("Invalid correlation_id", 400, "INVALID_CORRELATION_ID")
    cid = trace.get("correlation_id")
    return create_success_response(trace, "Correlation trace", correlation_id=cid)


@business_bp.route('/automation/queue-stats', methods=['GET'])
@handle_api_errors
def get_automation_queue_stats():
    """Get automation queue depth (queued, running, success, failed, dead) for observability."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        from services.automation_queue import automation_job_manager
        depth = automation_job_manager.get_queue_depth()
        return create_success_response(depth, 'Queue stats retrieved')
    except Exception as e:
        logger.error(f"Get automation queue stats error: {e}")
        return create_error_response("Failed to get queue stats", 500, 'AUTOMATION_QUEUE_ERROR')

@business_bp.route('/automation/metrics', methods=['GET'])
@handle_api_errors
def get_automation_metrics():
    """Get automation metrics: queue depth, success rate, p95 duration (for activity/health panel)."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        hours = request.args.get('hours', 24, type=int)
        hours = max(1, min(168, hours))

        from services.automation_queue import automation_job_manager
        metrics = automation_job_manager.get_automation_metrics(user_id=user_id, hours=hours)
        return create_success_response(metrics, 'Metrics retrieved')
    except Exception as e:
        logger.error(f"Get automation metrics error: {e}")
        return create_error_response("Failed to get metrics", 500, 'AUTOMATION_METRICS_ERROR')

@business_bp.route('/automation/kill-switch', methods=['POST'])
@handle_api_errors
def automation_kill_switch():
    """Emergency automation kill switch"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        automation_safety_manager.disable_all_automations(user_id)

        log_activity_event(
            user_id,
            'automation_kill_switch',
            message="Automation kill switch activated",
            metadata={'action': 'disable_all'},
            request=request
        )
        
        return create_success_response(
            {'message': 'All automations have been disabled'}, 
            'Automation kill switch activated'
        )
        
    except Exception as e:
        logger.error(f"Automation kill switch error: {e}")
        return create_error_response("Failed to activate kill switch", 500, 'KILL_SWITCH_ERROR')

@business_bp.route('/automation/safety-status', methods=['GET'])
@handle_api_errors
def get_automation_safety_status():
    """Get automation safety status"""
    try:
        user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        result = automation_safety_manager.get_safety_status(user_id)
        
        if result['success']:
            # Extract the data from the result and format for frontend
            safety_data = result.get('data', {})
            return create_success_response({
                'automation_enabled': not safety_data.get('global_kill_switch_enabled', False),
                'safety_level': 'normal' if safety_data.get('status') == 'active' else 'paused',
                'restrictions': [],
                'last_updated': None,
                'details': safety_data
            }, 'Safety status retrieved successfully')
        else:
            # Return default safe status if there's an error
            return create_success_response({
                'automation_enabled': True,
                'safety_level': 'normal',
                'restrictions': [],
                'last_updated': None,
                'error': result.get('error', 'Unable to retrieve safety status')
            }, 'Safety status retrieved (default)')
        
    except Exception as e:
        logger.error(f"Get safety status error: {e}")
        return create_error_response("Failed to retrieve safety status", 500, 'SAFETY_STATUS_ERROR')

@business_bp.route('/automation/logs', methods=['GET'])
@handle_api_errors
def get_automation_logs():
    """Get automation execution logs"""
    try:
        user_id = resolve_request_user_id(request, current_user_id=get_current_user_id(), allow_query=True)
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        rule_id = request.args.get('rule_id', type=int)
        slug = request.args.get('slug')
        limit = request.args.get('limit', 20, type=int)
        
        logs_result = automation_engine.get_execution_logs(user_id, rule_id=rule_id, slug=slug, limit=limit)
        if not logs_result['success']:
            return create_error_response("Failed to fetch logs", 500, 'AUTOMATION_LOGS_ERROR')
        
        return create_success_response(logs_result['data'], 'Automation logs retrieved')
        
    except Exception as e:
        logger.error(f"Get automation logs error: {e}")
        return create_error_response("Failed to fetch automation logs", 500, 'AUTOMATION_LOGS_ERROR')

@business_bp.route('/automation/test', methods=['POST'])
@handle_api_errors
def test_automation():
    """Test automation rule execution"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        data = request.get_json()
        rule_id = data.get('rule_id')
        test_data = data.get('test_data', {})
        
        if not rule_id:
            return create_error_response("rule_id is required", 400, 'MISSING_RULE_ID')
        
        result = automation_engine.test_rule(rule_id, test_data, user_id)
        if result.get('error_code') == 'NOT_IMPLEMENTED':
            return create_error_response(
                result.get('error', 'Action not implemented'),
                501,
                'NOT_IMPLEMENTED'
            )
        if not result.get('success'):
            return create_error_response(result.get('error', 'Test failed'), 500, 'AUTOMATION_TEST_FAILED')
        return create_success_response(result, "Automation test completed")
    except Exception as e:
        logger.error(f"❌ Automation test failed: {e}")
        return create_error_response(str(e), 500, 'AUTOMATION_TEST_FAILED')

# Workflow Routes
@business_bp.route('/workflows/followups/schedule', methods=['POST'])
@handle_api_errors
def schedule_followup_workflow():
    """Schedule a follow-up (email or SMS)"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    if not _require_paid_plan(user_id):
        return create_error_response("Plan limit exceeded", 402, 'PLAN_LIMIT_EXCEEDED')

    data = request.get_json() or {}
    lead_id = data.get('lead_id')
    follow_up_date = data.get('follow_up_date')
    follow_up_type = data.get('follow_up_type', 'email')
    message = data.get('message', '')

    if not follow_up_date:
        return create_error_response("follow_up_date is required", 400, 'MISSING_DATE')

    result = schedule_follow_up(user_id, lead_id, follow_up_date, follow_up_type, message)
    if result.get('success') and lead_id:
        try:
            enhanced_crm_service.add_lead_activity(
                lead_id,
                user_id,
                'follow_up',
                f"Follow-up scheduled ({follow_up_type})",
                metadata={'follow_up_date': follow_up_date, 'message': message}
            )
        except Exception as e:
            logger.warning("Failed to log follow-up schedule activity: %s", e)
    if result.get('success'):
        automation_safety_manager.log_automation_action(
            user_id=user_id,
            rule_id=0,
            action_type=f"follow_up_schedule_{follow_up_type}",
            target_contact=str(lead_id or user_id),
            idempotency_key=f"followup_schedule_{result.get('follow_up_id')}",
            status='completed'
        )

    return create_success_response(result, 'Follow-up scheduled')


@business_bp.route('/workflows/followups/execute', methods=['POST'])
@handle_api_errors
def execute_followup_workflow():
    """Execute due follow-ups for the authenticated user"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    if not _require_paid_plan(user_id):
        return create_error_response("Plan limit exceeded", 402, 'PLAN_LIMIT_EXCEEDED')

    result = execute_due_follow_ups(user_id)
    return create_success_response(result, 'Follow-ups executed')


@business_bp.route('/workflows/appointments/reminders/run', methods=['POST'])
@handle_api_errors
def run_appointment_reminders():
    """Run appointment reminder job"""
    # Admin/internal use only; still require auth
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    if not _require_paid_plan(user_id):
        return create_error_response("Plan limit exceeded", 402, 'PLAN_LIMIT_EXCEEDED')

    from core.appointment_reminders import run_reminder_job
    result = run_reminder_job()
    return create_success_response(result, 'Appointment reminders executed')


@business_bp.route('/workflows/documents/generate', methods=['POST'])
@handle_api_errors
def generate_workflow_document():
    """Generate a document and return file response"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    if not _require_paid_plan(user_id):
        return create_error_response("Plan limit exceeded", 402, 'PLAN_LIMIT_EXCEEDED')

    data = request.get_json() or {}
    template_id = data.get('template_id')
    variables = data.get('variables', {})
    lead_id = data.get('lead_id')
    output_format = data.get('format', 'txt').lower()

    if not template_id:
        return create_error_response("template_id is required", 400, 'MISSING_TEMPLATE')

    safety = automation_safety_manager.check_rate_limits(
        user_id=user_id,
        action_type='workflow_document',
        target_contact=str(lead_id or user_id)
    )
    if not safety.get('allowed'):
        return create_error_response("Rate limit exceeded", 429, 'RATE_LIMIT_EXCEEDED')

    result = generate_document(template_id, variables, user_id, output_format)
    document = result['document']
    automation_safety_manager.log_automation_action(
        user_id=user_id,
        rule_id=0,
        action_type='workflow_document',
        target_contact=str(lead_id or user_id),
        idempotency_key=f"doc_{document.id}",
        status='completed'
    )

    try:
        content_to_store = result['content_bytes']
        if output_format == 'pdf':
            import base64
            content_to_store = base64.b64encode(content_to_store).decode('utf-8')
        else:
            content_to_store = content_to_store.decode('utf-8', errors='ignore')

        db_optimizer.execute_query(
            """
            INSERT INTO generated_documents (id, user_id, lead_id, template_id, format, content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (document.id, user_id, lead_id, template_id, output_format, content_to_store,
             json.dumps({'variables': variables}), datetime.utcnow().isoformat()),
            fetch=False
        )
    except Exception as e:
        logger.warning("Failed to store document metadata: %s", e)

    if lead_id:
        try:
            enhanced_crm_service.add_lead_activity(
                lead_id,
                user_id,
                'document_generated',
                f"Generated document {template_id}",
                metadata={'document_id': document.id, 'format': output_format}
            )
        except Exception as e:
            logger.warning("Failed to log document activity: %s", e)

    return send_file(
        io.BytesIO(result['content_bytes']),
        mimetype=result['content_type'],
        as_attachment=True,
        download_name=result['filename']
    )


@business_bp.route('/workflows/tables/export', methods=['POST'])
@handle_api_errors
def export_workflow_table():
    """Export a table/sheet as CSV or JSON"""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
    if not _require_paid_plan(user_id):
        return create_error_response("Plan limit exceeded", 402, 'PLAN_LIMIT_EXCEEDED')

    data = request.get_json() or {}
    name = data.get('name', 'export')
    columns = data.get('columns') or []
    rows = data.get('rows') or []
    output_format = (data.get('format') or 'csv').lower()
    lead_id = data.get('lead_id')

    if not columns or not isinstance(columns, list):
        return create_error_response("columns must be a non-empty list", 400, 'MISSING_COLUMNS')

    safety = automation_safety_manager.check_rate_limits(
        user_id=user_id,
        action_type='workflow_table',
        target_contact=str(lead_id or user_id)
    )
    if not safety.get('allowed'):
        return create_error_response("Rate limit exceeded", 429, 'RATE_LIMIT_EXCEEDED')

    if output_format not in {'csv', 'json'}:
        return create_error_response("format must be csv or json", 400, 'INVALID_FORMAT')

    if output_format == 'json':
        payload = []
        for row in rows:
            if isinstance(row, dict):
                payload.append({col: row.get(col) for col in columns})
            else:
                payload.append({col: row[idx] if idx < len(row) else None for idx, col in enumerate(columns)})
        content_bytes = json.dumps(payload, indent=2).encode('utf-8')
        content_type = 'application/json'
        filename = f"{name}.json"
        data_to_store = json.dumps({'columns': columns, 'rows': payload})
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        for row in rows:
            if isinstance(row, dict):
                writer.writerow([row.get(col, '') for col in columns])
            else:
                writer.writerow(row)
        content = output.getvalue()
        content_bytes = content.encode('utf-8')
        content_type = 'text/csv'
        filename = f"{name}.csv"
        data_to_store = content

    try:
        db_optimizer.execute_query(
            """
            INSERT INTO table_exports (user_id, lead_id, name, columns, row_count, format, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, lead_id, name, json.dumps(columns), len(rows), output_format, data_to_store, datetime.utcnow().isoformat()),
            fetch=False
        )
    except Exception as e:
        logger.warning("Failed to store table export metadata: %s", e)

    automation_safety_manager.log_automation_action(
        user_id=user_id,
        rule_id=0,
        action_type='workflow_table_export',
        target_contact=str(lead_id or user_id),
        idempotency_key=f"table_{name}_{datetime.utcnow().isoformat()}",
        status='completed'
    )

    if lead_id:
        try:
            enhanced_crm_service.add_lead_activity(
                lead_id,
                user_id,
                'note_added',
                f"Exported table {name}",
                metadata={'format': output_format, 'row_count': len(rows)}
            )
        except Exception as e:
            logger.warning("Failed to log table export activity: %s", e)

    return send_file(
        io.BytesIO(content_bytes),
        mimetype=content_type,
        as_attachment=True,
        download_name=filename
    )

# Services API Routes
@business_bp.route('/services', methods=['GET'])
@handle_api_errors
def get_services():
    """Get all services for authenticated user"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        services = db_optimizer.execute_query("""
            SELECT id, service_id, service_name, enabled, status, settings, 
                   created_at, updated_at, last_sync_at
            FROM user_services 
            WHERE user_id = ?
            ORDER BY service_name
        """, (user_id,))
        
        # Parse JSON settings
        result = []
        for service in services:
            service_dict = dict(service)
            if service_dict.get('settings'):
                try:
                    import json
                    service_dict['settings'] = json.loads(service_dict['settings'])
                except Exception as parse_error:
                    logger.debug("Failed to parse service settings JSON: %s", parse_error)
                    service_dict['settings'] = {}
            result.append(service_dict)
        
        return create_success_response(result, "Services retrieved successfully")
    except Exception as e:
        logger.error(f"❌ Get services failed: {e}")
        return create_error_response(str(e), 500, 'GET_SERVICES_FAILED')

@business_bp.route('/services', methods=['POST'])
@handle_api_errors
def create_service():
    """Create or update a service"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        data = request.get_json()
        service_id = data.get('service_id')
        service_name = data.get('service_name')
        enabled = data.get('enabled', False)
        settings = data.get('settings', {})
        
        if not service_id or not service_name:
            return create_error_response("service_id and service_name are required", 400, 'MISSING_FIELDS')
        
        import json
        settings_json = json.dumps(settings)
        
        db_optimizer.upsert_user_services_row(
            user_id,
            service_id,
            service_name,
            enabled,
            "active" if enabled else "inactive",
            settings_json,
        )

        status_label = 'enabled' if enabled else 'disabled'
        log_activity_event(
            user_id,
            'service_created',
            message=f"Service {service_name} {status_label}",
            metadata={'service_id': service_id, 'service_name': service_name, 'enabled': enabled},
            request=request
        )
        
        return create_success_response({'service_id': service_id}, "Service saved successfully")
    except Exception as e:
        logger.error(f"❌ Create service failed: {e}")
        return create_error_response(str(e), 500, 'CREATE_SERVICE_FAILED')

@business_bp.route('/services/<service_id>', methods=['PUT'])
@handle_api_errors
def update_service(service_id):
    """Update a service"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        data = request.get_json()
        enabled = data.get('enabled')
        settings = data.get('settings')
        
        updates = []
        params = []
        
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(enabled)
            updates.append("status = ?")
            params.append('active' if enabled else 'inactive')
        
        if settings is not None:
            import json
            updates.append("settings = ?")
            params.append(json.dumps(settings))
        
        if not updates:
            return create_error_response("No fields to update", 400, 'NO_UPDATES')
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([user_id, service_id])
        
        query = f"""
            UPDATE user_services 
            SET {', '.join(updates)}
            WHERE user_id = ? AND service_id = ?
        """
        
        result = db_optimizer.execute_query(query, tuple(params), fetch=False)

        service_row = db_optimizer.execute_query(
            "SELECT service_name, enabled FROM user_services WHERE user_id = ? AND service_id = ?",
            (user_id, service_id)
        )
        service_name = service_row[0].get('service_name') if service_row else service_id
        enabled_val = service_row[0].get('enabled') if service_row else enabled
        changes = []
        if enabled is not None:
            changes.append(f"enabled={bool(enabled)}")
        if settings is not None:
            changes.append("settings updated")
        changes_text = ", ".join(changes) if changes else "updated"
        log_activity_event(
            user_id,
            'service_updated',
            message=f"Service {service_name} updated ({changes_text})",
            metadata={'service_id': service_id, 'service_name': service_name, 'enabled': enabled_val},
            request=request
        )
        
        return create_success_response({'service_id': service_id}, "Service updated successfully")
    except Exception as e:
        logger.error(f"❌ Update service failed: {e}")
        return create_error_response(str(e), 500, 'UPDATE_SERVICE_FAILED')

@business_bp.route('/services/<service_id>', methods=['DELETE'])
@handle_api_errors
def delete_service(service_id):
    """Delete a service"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        service_row = db_optimizer.execute_query(
            "SELECT service_name FROM user_services WHERE user_id = ? AND service_id = ?",
            (user_id, service_id)
        )
        service_name = service_row[0].get('service_name') if service_row else service_id

        db_optimizer.execute_query("""
            DELETE FROM user_services 
            WHERE user_id = ? AND service_id = ?
        """, (user_id, service_id), fetch=False)

        log_activity_event(
            user_id,
            'service_deleted',
            message=f"Service {service_name} deleted",
            metadata={'service_id': service_id, 'service_name': service_name},
            request=request
        )
        
        return create_success_response({'service_id': service_id}, "Service deleted successfully")
    except Exception as e:
        logger.error(f"❌ Delete service failed: {e}")
        return create_error_response(str(e), 500, 'DELETE_SERVICE_FAILED')

# IMAP/SMTP configuration (legacy providers)
@business_bp.route('/email/imap-config', methods=['GET'])
@handle_api_errors
def get_imap_config():
    """Get saved IMAP/SMTP configuration (without secrets)"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        row = db_optimizer.execute_query(
            "SELECT settings, enabled, status FROM user_services WHERE user_id = ? AND service_id = ?",
            (user_id, 'imap')
        )
        if not row:
            return create_success_response({'configured': False}, "No IMAP configuration found")

        service = dict(row[0]) if hasattr(row[0], 'keys') else row[0]
        settings = {}
        if service.get('settings'):
            try:
                settings = json.loads(service.get('settings'))
            except Exception:
                settings = {}
        # Never return raw password
        if 'password' in settings:
            settings['password'] = '********'

        return create_success_response({
            'configured': True,
            'enabled': bool(service.get('enabled')),
            'status': service.get('status'),
            'settings': settings
        }, "IMAP configuration retrieved")
    except Exception as e:
        logger.error(f"❌ Get IMAP config failed: {e}")
        return create_error_response(str(e), 500, 'GET_IMAP_CONFIG_FAILED')


@business_bp.route('/email/imap-config', methods=['POST'])
@handle_api_errors
def save_imap_config():
    """Save IMAP/SMTP configuration for legacy providers"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')

        data = request.get_json() or {}
        required = ['username', 'password', 'imap_server', 'smtp_server']
        missing = [field for field in required if not data.get(field)]
        if missing:
            return create_error_response(f"Missing fields: {', '.join(missing)}", 400, 'MISSING_FIELDS')

        settings = {
            'service_name': data.get('service_name', 'IMAP/SMTP'),
            'username': data.get('username'),
            'password': data.get('password'),
            'imap_server': data.get('imap_server'),
            'imap_port': int(data.get('imap_port', 993)),
            'imap_ssl': bool(data.get('imap_ssl', True)),
            'smtp_server': data.get('smtp_server'),
            'smtp_port': int(data.get('smtp_port', 587)),
            'smtp_ssl': bool(data.get('smtp_ssl', False)),
            'smtp_tls': bool(data.get('smtp_tls', True))
        }

        # Validate credentials before saving
        provider = IMAPProvider(settings)
        if not provider.authenticate():
            return create_error_response("Failed to authenticate IMAP/SMTP credentials", 400, 'IMAP_AUTH_FAILED')

        settings_json = json.dumps(settings)
        db_optimizer.upsert_user_services_row(
            user_id,
            "imap",
            settings.get("service_name", "IMAP/SMTP"),
            True,
            "active",
            settings_json,
        )

        log_activity_event(
            user_id,
            'service_updated',
            message="IMAP/SMTP settings updated",
            metadata={'service_id': 'imap', 'service_name': settings.get('service_name', 'IMAP/SMTP')},
            request=request
        )

        return create_success_response({'configured': True}, "IMAP configuration saved")
    except Exception as e:
        logger.error(f"❌ Save IMAP config failed: {e}")
        return create_error_response(str(e), 500, 'SAVE_IMAP_CONFIG_FAILED')

# Email Attachments API Routes
@business_bp.route('/email/<email_id>/attachments', methods=['GET'])
@handle_api_errors
def get_email_attachments(email_id):
    """Get attachments for an email"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        attachments = db_optimizer.execute_query("""
            SELECT id, attachment_id, filename, mime_type, size, created_at
            FROM email_attachments 
            WHERE user_id = ? AND email_id = ?
            ORDER BY filename
        """, (user_id, email_id))
        
        result = [dict(att) for att in attachments]
        return create_success_response(result, "Attachments retrieved successfully")
    except Exception as e:
        logger.error(f"❌ Get attachments failed: {e}")
        return create_error_response(str(e), 500, 'GET_ATTACHMENTS_FAILED')

@business_bp.route('/email/<email_id>/attachments/<attachment_id>/download', methods=['GET'])
@handle_api_errors
def download_attachment(email_id, attachment_id):
    """Download an email attachment"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Get attachment info
        attachment = db_optimizer.execute_query("""
            SELECT attachment_id, filename, mime_type, size, stored_path
            FROM email_attachments 
            WHERE user_id = ? AND email_id = ? AND attachment_id = ?
            LIMIT 1
        """, (user_id, email_id, attachment_id))
        
        if not attachment:
            return create_error_response("Attachment not found", 404, 'ATTACHMENT_NOT_FOUND')
        
        att = dict(attachment[0])
        
        # If stored locally, serve from file
        if att.get('stored_path') and os.path.exists(att['stored_path']):
            from flask import send_file
            return send_file(att['stored_path'], as_attachment=True, download_name=att['filename'])
        
        # Otherwise, fetch from Gmail API
        try:
            from integrations.gmail.gmail_client import gmail_client
            attachment_data = gmail_client.get_attachment(user_id, email_id, attachment_id)
            
            if attachment_data:
                from flask import Response
                response = Response(
                    attachment_data['data'],
                    mimetype=att.get('mime_type', 'application/octet-stream'),
                    headers={
                        'Content-Disposition': f'attachment; filename="{att["filename"]}"'
                    }
                )
                return response
            
            return create_error_response("Failed to fetch attachment", 500, 'FETCH_FAILED')
        except Exception as e:
            logger.error(f"❌ Download attachment failed: {e}")
            return create_error_response(str(e), 500, 'DOWNLOAD_FAILED')
    except Exception as e:
        logger.error(f"❌ Download attachment failed: {e}")
        return create_error_response(str(e), 500, 'DOWNLOAD_FAILED')

@business_bp.route('/email/<email_id>/embedded-image/<attachment_id>', methods=['GET'])
@handle_api_errors
def get_embedded_image(email_id, attachment_id):
    """Get embedded image from email (for cid: references)"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        # Fetch embedded image from Gmail API
        try:
            from integrations.gmail.gmail_client import gmail_client
            gmail_service = gmail_client.get_gmail_service_for_user(user_id)
            
            # Get attachment from Gmail API
            attachment = gmail_service.users().messages().attachments().get(
                userId='me',
                messageId=email_id,
                id=attachment_id
            ).execute()
            
            if attachment:
                import base64
                # Decode attachment data
                attachment_data = base64.urlsafe_b64decode(attachment['data'])
                
                # Get content type from attachment or default to image
                content_type = attachment.get('mimeType', 'image/png')
                
                from flask import Response
                response = Response(
                    attachment_data,
                    mimetype=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                        'Content-Security-Policy': "default-src 'self'",
                        'Access-Control-Allow-Origin': '*'  # Allow CORS for images
                    }
                )
                return response
            
            return create_error_response("Failed to fetch embedded image", 500, 'FETCH_FAILED')
        except Exception as e:
            logger.error(f"❌ Get embedded image failed: {e}")
            return create_error_response(str(e), 500, 'DOWNLOAD_FAILED')
    except Exception as e:
        logger.error(f"❌ Get embedded image failed: {e}")
        return create_error_response(str(e), 500, 'DOWNLOAD_FAILED')

def _ensure_automation_preset_lead_id(user_id: int, min_score: int = 6) -> int:
    """Pick a lead owned by the user for preset tests, or create a disposable sample lead."""
    rows = db_optimizer.execute_query(
        """
        SELECT id, score FROM leads
        WHERE user_id = ?
          AND (withdrawn_at IS NULL OR withdrawn_at = '')
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    )
    if rows:
        lid = rows[0]['id']
        sc = rows[0].get('score') or 0
        if sc < min_score:
            db_optimizer.execute_query(
                "UPDATE leads SET score = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                (min_score + 1, lid, user_id),
                fetch=False,
            )
        return lid
    created = enhanced_crm_service.create_lead(
        user_id,
        {
            'email': f'automation-preset-{user_id}@example.test',
            'name': 'Automation preset sample',
            'source': 'automation_preset',
            'stage': 'new',
            'score': min_score + 1,
        },
    )
    if not created.get('success'):
        raise ValueError(created.get('error') or 'Could not create sample lead for preset test')
    return created['data']['lead_id']


@business_bp.route('/automation/test/preset', methods=['POST'])
@handle_api_errors
def test_automation_preset():
    """Trigger an automation preset with sample data"""
    try:
        user_id = get_current_user_id()
        
        # Fallback: allow user_id from request body for development/testing
        if not user_id:
            data = request.get_json() or {}
            user_id = data.get('user_id')
            if not user_id:
                return create_error_response("Authentication required", 401, 'AUTHENTICATION_REQUIRED')
        
        data = request.get_json() or {}
        preset = data.get('preset_id')
        if not preset:
            return create_error_response("preset_id is required", 400, 'MISSING_PRESET_ID')

        correlation_id = get_or_create_correlation_id(request, data)

        sample_lead_id = None
        if preset in ('lead_scoring', 'calendar_followups'):
            try:
                sample_lead_id = _ensure_automation_preset_lead_id(user_id)
            except ValueError as e:
                logger.warning("Automation preset sample lead: %s", e)
                return create_error_response(
                    str(e),
                    500,
                    'PRESET_SAMPLE_LEAD_FAILED',
                    correlation_id=correlation_id,
                )

        # Backward compat: API accepts preset_id gmail_crm (alias → inbound_crm_sync).
        preset_key = {'gmail_crm': 'inbound_crm_sync'}.get(preset, preset)

        preset_map = {
            'inbound_crm_sync': {
                'trigger': TriggerType.EMAIL_RECEIVED,
                'data': {'sender_email': 'lead@example.com', 'subject': 'Interested in services', 'text': 'Hi, I need help'}
            },
            'lead_scoring': {
                'trigger': TriggerType.LEAD_CREATED,
                'data': {'lead_id': sample_lead_id, 'source': 'gmail', 'score': 7}
            },
            'slack_digest': {
                'trigger': TriggerType.TIME_BASED,
                'data': {'summary_type': 'daily', 'timestamp': datetime.now().isoformat()}
            },
            'email_sheets': {
                'trigger': TriggerType.EMAIL_RECEIVED,
                'data': {'sender_email': 'form@typeform.com', 'text': 'New submission', 'payload': {'fields': []}}
            },
            'calendar_followups': {
                'trigger': TriggerType.LEAD_STAGE_CHANGED,
                'data': {'lead_id': sample_lead_id, 'old_stage': 'qualified', 'new_stage': 'booked'}
            }
        }
        
        mapping = preset_map.get(preset_key)
        if not mapping:
            return create_error_response("Unknown preset", 400, 'UNKNOWN_PRESET')
        
        trigger_data = {**mapping['data'], 'correlation_id': correlation_id}
        result = automation_engine.execute_automation_rules(
            mapping['trigger'], trigger_data, user_id, automation_source="api_preset"
        )
        failed = result.get('data', {}).get('failed_rules', [])
        not_impl = next((f for f in failed if f.get('error_code') == 'NOT_IMPLEMENTED'), None)
        if not_impl:
            return create_error_response(
                not_impl.get('error') or 'Action not implemented',
                501,
                'NOT_IMPLEMENTED',
                correlation_id=correlation_id,
            )
        if result.get('success'):
            return create_success_response(
                result.get('data', {}),
                'Preset executed',
                correlation_id=correlation_id,
            )
        return create_error_response(
            result.get('error', 'Execution failed'),
            500,
            'AUTOMATION_EXECUTION_ERROR',
            correlation_id=correlation_id,
        )
        
    except Exception as e:
        logger.error(f"Automation preset test error: {e}")
        return create_error_response("Failed to run automation preset", 500, 'AUTOMATION_TEST_ERROR')
