"""
Webhook API Endpoints for Fikiri Solutions
Handles incoming webhook requests from form services
"""

import re
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from core.webhook_intake_service import get_webhook_service
from core.config import get_config
from core.appointments_service import AppointmentsService
from core.database_optimization import db_optimizer
from core.request_correlation import get_or_create_correlation_id

logger = logging.getLogger(__name__)

# Safety: prevent DB writes from exploding due to abusive payload sizes.
MAX_STORED_PAYLOAD_CHARS = 200_000


def _stringify_payload(payload: object, max_chars: int = MAX_STORED_PAYLOAD_CHARS) -> tuple[str, bool]:
    """Convert incoming payload to JSON string (best-effort) with an upper bound."""
    try:
        payload_json = json.dumps(payload, ensure_ascii=False)
    except Exception:
        payload_json = str(payload)

    if len(payload_json) > max_chars:
        return payload_json[:max_chars] + "...", True
    return payload_json, False


_FORM_INTAKE_INSERT_COLS = (
    "user_id, api_key_id, form_id, source, email, name, phone, company, subject, "
    "payload_json, payload_truncated, status, error, lead_id, request_ip, user_agent, "
    "client_submission_id, supersedes_intake_id"
)


def _insert_customer_form_intake(
    *,
    user_id,
    api_key_id,
    form_id,
    source,
    email,
    name,
    phone,
    company,
    subject,
    payload_json: str,
    payload_truncated: bool,
    status: str,
    error,
    lead_id,
    request_ip,
    user_agent,
    client_submission_id=None,
    supersedes_intake_id=None,
) -> int | None:
    """Append-only form intake row. Returns new row id or None on failure.

    Uses `db_optimizer.execute_insert_returning_id()` so the insert id is
    returned via INSERT ... RETURNING on Postgres and via the SQLite
    cursor's native lastrow attribute on SQLite — all in the same connection
    so there's no cross-connection race (the previous helper ran a separate
    SELECT on a fresh connection).
    """
    try:
        return db_optimizer.execute_insert_returning_id(
            f"""
            INSERT INTO customer_form_intake_submissions (
                {_FORM_INTAKE_INSERT_COLS}
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                api_key_id,
                form_id,
                source,
                email,
                name,
                phone,
                company,
                subject,
                payload_json,
                payload_truncated,
                status,
                error,
                lead_id,
                request_ip,
                user_agent,
                client_submission_id,
                supersedes_intake_id,
            ),
        )
    except Exception:
        return None


def _forms_webhook_auth(endpoint_path: str):
    """
    Shared auth for forms submit/update/cancel.
    Returns (key_info, None) or (None, (jsonify(...), status_code)).
    """
    from core.api_key_manager import api_key_manager

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "API key required (X-API-Key header)",
                    "error_code": "MISSING_API_KEY",
                }
            ),
            401,
        )

    key_info = api_key_manager.validate_api_key(api_key)
    if not key_info:
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid API key",
                    "error_code": "INVALID_API_KEY",
                }
            ),
            401,
        )

    allowed_scopes = set(key_info.get("scopes", []))
    required_scopes = ["webhooks:forms", "webhooks:*", "leads:create", "leads:*"]
    if not any(s in allowed_scopes for s in required_scopes):
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": "Insufficient permissions. Required scope: webhooks:forms or leads:create",
                    "error_code": "INSUFFICIENT_SCOPE",
                }
            ),
            403,
        )

    allowed_origins = key_info.get("allowed_origins")
    if allowed_origins:
        origin_str = request.headers.get("Origin", "")
        if origin_str and origin_str not in allowed_origins:
            logger.warning(
                "⚠️ Origin not allowed: %s (allowed: %s)", origin_str, allowed_origins
            )
            return None, (
                jsonify(
                    {
                        "success": False,
                        "error": "Origin not allowed",
                        "error_code": "ORIGIN_NOT_ALLOWED",
                    }
                ),
                403,
            )

    key_prefix = (key_info.get("key_prefix") or "")[:12] or "unknown"
    logger.info(
        "webhook request endpoint=%s api_key_prefix=%s origin=%s",
        endpoint_path,
        key_prefix,
        request.headers.get("Origin") or request.headers.get("Referer") or "-",
    )
    err_resp, err_status = _check_webhook_rate_limit(key_info, endpoint_path)
    if err_resp is not None:
        resp = jsonify(err_resp)
        resp.headers["Retry-After"] = str(err_resp.get("retry_after_seconds", 60))
        return None, (resp, err_status)

    try:
        api_key_manager.record_usage(
            key_info["api_key_id"],
            endpoint_path,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
    except Exception:
        pass

    return key_info, None


def _persist_appointment_intake_submission(
    user_id: int,
    api_key_id: str,
    *,
    source: str,
    appointment_id: int | None,
    customer_name: str | None,
    customer_email: str | None,
    customer_phone: str | None,
    service_type: str | None,
    requested_date: str | None,
    requested_time: str | None,
    timezone: str | None,
    status: str,
    error_message: str | None,
    payload_json: str,
    payload_truncated: bool,
    request_ip: str | None,
    user_agent: str | None,
) -> None:
    """Best-effort persistence for appointment intake requests."""
    try:
        db_optimizer.execute_query(
            """
            INSERT INTO customer_appointment_intake_submissions (
                user_id, source, appointment_id,
                customer_name, customer_email, customer_phone,
                service_type, requested_date, requested_time, timezone,
                status, error_message,
                payload_json, payload_truncated,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                user_id,
                source,
                appointment_id,
                customer_name,
                customer_email,
                customer_phone,
                service_type,
                requested_date,
                requested_time,
                timezone,
                status,
                error_message,
                payload_json,
                payload_truncated,
            ),
            fetch=False,
        )
    except Exception:
        # Never let persistence failures break public webhook flows.
        return

# Payload limits (abuse prevention)
EMAIL_MAX_LENGTH = 255
NAME_MAX_LENGTH = 500
# Simple email validation: local@domain.tld
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
# Honeypot field names: if present and non-empty, reject (bot trap)
HONEYPOT_NAMES = ("honeypot", "honeypot_field", "_hp", "website", "url")


def _check_webhook_rate_limit(key_info: dict, endpoint: str):
    """Return (None, None) if allowed, else (response_dict, status_code) for 429."""
    from core.api_key_manager import api_key_manager
    api_key_id = key_info.get("api_key_id")
    if not api_key_id:
        return None, None
    result = api_key_manager.check_rate_limit(api_key_id, "minute")
    if result.get("allowed", True):
        return None, None
    retry_after = 60
    return {
        "success": False,
        "error": "Rate limit exceeded. Retry after 1 minute.",
        "error_code": "RATE_LIMIT_EXCEEDED",
        "retry_after_seconds": retry_after,
    }, 429


def _validate_webhook_email_and_name(email: str, name: str = None) -> tuple:
    """Validate email and name. Returns (None, None) if valid else (error_message, error_code)."""
    if not email or not email.strip():
        return "Email is required", "MISSING_EMAIL"
    email = email.strip()
    if len(email) > EMAIL_MAX_LENGTH:
        return f"Email must be at most {EMAIL_MAX_LENGTH} characters", "INVALID_EMAIL"
    if not EMAIL_RE.match(email):
        return "Invalid email format", "INVALID_EMAIL"
    if name is not None and len(name) > NAME_MAX_LENGTH:
        return f"Name must be at most {NAME_MAX_LENGTH} characters", "INVALID_PAYLOAD"
    return None, None


def _check_honeypot(data: dict, fields: dict = None) -> bool:
    """Return True if honeypot was filled (reject request)."""
    for key in HONEYPOT_NAMES:
        val = data.get(key) if isinstance(data, dict) else None
        if val is not None and str(val).strip() != "":
            return True
        if fields and isinstance(fields, dict):
            val = fields.get(key)
            if val is not None and str(val).strip() != "":
                return True
    return False

# Import trace context
try:
    from core.trace_context import set_trace_id, get_trace_id
    TRACE_CONTEXT_AVAILABLE = True
except ImportError:
    TRACE_CONTEXT_AVAILABLE = False
    logger.warning("Trace context not available")

# Create blueprint
webhook_bp = Blueprint('webhook', __name__, url_prefix='/api/webhooks')

@webhook_bp.route('/tally', methods=['POST'])
def handle_tally_webhook():
    """Handle webhook from Tally forms"""
    try:
        # Set trace ID from header or generate new one
        if TRACE_CONTEXT_AVAILABLE:
            trace_id = request.headers.get('X-Trace-ID')
            set_trace_id(trace_id)
            logger.info(f"Webhook trace ID: {get_trace_id()}", extra={
                'event': 'webhook_received',
                'service': 'webhook',
                'severity': 'INFO',
                'trace_id': get_trace_id(),
                'webhook_type': 'tally'
            })
        
        # Get webhook service
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({
                "success": False,
                "error": "Webhook service not available"
            }), 500
        
        # Verify webhook signature if enabled
        if webhook_service.config.enable_verification:
            signature = request.headers.get('X-Tally-Signature', '')
            if not webhook_service.verify_webhook_signature(
                request.get_data(as_text=True),
                signature,
                webhook_service.config.secret_key
            ):
                logger.warning("⚠️ Invalid Tally webhook signature")
                return jsonify({
                    "success": False,
                    "error": "Invalid signature"
                }), 401
        
        # Process webhook data (silent=True so invalid/empty body yields None, not 400 raise)
        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                "success": False,
                "error": "No data received"
            }), 400
        
        result = webhook_service.process_tally_webhook(data)
        
        if result['success']:
            logger.info(f"✅ Tally webhook processed: {result.get('lead_id')}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Tally webhook failed: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"❌ Tally webhook error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@webhook_bp.route('/typeform', methods=['POST'])
def handle_typeform_webhook():
    """Handle webhook from Typeform"""
    try:
        # Set trace ID from header or generate new one
        if TRACE_CONTEXT_AVAILABLE:
            trace_id = request.headers.get('X-Trace-ID')
            set_trace_id(trace_id)
            logger.info(f"Webhook trace ID: {get_trace_id()}", extra={
                'event': 'webhook_received',
                'service': 'webhook',
                'severity': 'INFO',
                'trace_id': get_trace_id(),
                'webhook_type': 'typeform'
            })
        
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({
                "success": False,
                "error": "Webhook service not available"
            }), 500
        
        # Verify webhook signature if enabled
        if webhook_service.config.enable_verification:
            signature = request.headers.get('X-Typeform-Signature', '')
            if not webhook_service.verify_webhook_signature(
                request.get_data(as_text=True),
                signature,
                webhook_service.config.secret_key
            ):
                logger.warning("⚠️ Invalid Typeform webhook signature")
                return jsonify({
                    "success": False,
                    "error": "Invalid signature"
                }), 401
        
        # Process webhook data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data received"
            }), 400
        
        result = webhook_service.process_typeform_webhook(data)
        
        if result['success']:
            logger.info(f"✅ Typeform webhook processed: {result.get('lead_id')}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Typeform webhook failed: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"❌ Typeform webhook error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@webhook_bp.route('/jotform', methods=['POST'])
def handle_jotform_webhook():
    """Handle webhook from Jotform"""
    try:
        # Set trace ID from header or generate new one
        if TRACE_CONTEXT_AVAILABLE:
            trace_id = request.headers.get('X-Trace-ID')
            set_trace_id(trace_id)
            logger.info(f"Webhook trace ID: {get_trace_id()}", extra={
                'event': 'webhook_received',
                'service': 'webhook',
                'severity': 'INFO',
                'trace_id': get_trace_id(),
                'webhook_type': 'jotform'
            })
    except Exception:
        pass  # Continue even if trace context fails
    
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({
                "success": False,
                "error": "Webhook service not available"
            }), 500
        
        # Verify webhook signature if enabled
        if webhook_service.config.enable_verification:
            signature = request.headers.get('X-Jotform-Signature', '')
            if not webhook_service.verify_webhook_signature(
                request.get_data(as_text=True),
                signature,
                webhook_service.config.secret_key
            ):
                logger.warning("⚠️ Invalid Jotform webhook signature")
                return jsonify({
                    "success": False,
                    "error": "Invalid signature"
                }), 401
        
        # Process webhook data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data received"
            }), 400
        
        result = webhook_service.process_jotform_webhook(data)
        
        if result['success']:
            logger.info(f"✅ Jotform webhook processed: {result.get('lead_id')}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Jotform webhook failed: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"❌ Jotform webhook error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@webhook_bp.route('/generic', methods=['POST'])
def handle_generic_webhook():
    """Handle generic webhook data"""
    try:
        # Set trace ID from header or generate new one
        if TRACE_CONTEXT_AVAILABLE:
            trace_id = request.headers.get('X-Trace-ID')
            set_trace_id(trace_id)
            logger.info(f"Webhook trace ID: {get_trace_id()}", extra={
                'event': 'webhook_received',
                'service': 'webhook',
                'severity': 'INFO',
                'trace_id': get_trace_id(),
                'webhook_type': 'generic'
            })
    except Exception:
        pass  # Continue even if trace context fails
    
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({
                "success": False,
                "error": "Webhook service not available"
            }), 500
        
        # Process webhook data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data received"
            }), 400
        
        result = webhook_service.process_generic_webhook(data)
        
        if result['success']:
            logger.info(f"✅ Generic webhook processed: {result.get('lead_id')}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Generic webhook failed: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"❌ Generic webhook error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@webhook_bp.route('/test', methods=['POST'])
def test_webhook():
    """Test webhook endpoint for development"""
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({
                "success": False,
                "error": "Webhook service not available"
            }), 500
        
        # Process test data
        data = request.get_json()
        if not data:
            # Provide sample data
            data = {
                "name": "Test Lead",
                "email": "test@example.com",
                "phone": "+1-555-123-4567",
                "company": "Test Company",
                "message": "This is a test webhook submission"
            }
        
        result = webhook_service.process_generic_webhook(data)
        
        if result['success']:
            logger.info(f"✅ Test webhook processed: {result.get('lead_id')}")
            return jsonify({
                **result,
                "message": "Test webhook processed successfully"
            }), 200
        else:
            logger.error(f"❌ Test webhook failed: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"❌ Test webhook error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@webhook_bp.route('/status', methods=['GET'])
def webhook_status():
    """Get webhook service status"""
    try:
        webhook_service = get_webhook_service()
        if not webhook_service:
            return jsonify({
                "success": False,
                "error": "Webhook service not available"
            }), 500
        
        status = {
            "success": True,
            "service": "Webhook Intake Service",
            "status": "active",
            "integrations": {
                "google_sheets": webhook_service.sheets_connector is not None,
                "notion": webhook_service.notion_connector is not None
            },
            "endpoints": [
                "/api/webhooks/tally",
                "/api/webhooks/typeform",
                "/api/webhooks/jotform",
                "/api/webhooks/generic",
                "/api/webhooks/test",
                "/api/webhooks/twilio/sms",
                "/api/webhooks/twilio/voice",
                "/api/webhooks/forms/submit",
                "/api/webhooks/forms/update",
                "/api/webhooks/forms/cancel",
                "/api/webhooks/leads/capture"
            ]
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook status error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

def _validate_twilio_signature():
    """Return True if request is from Twilio (or validation disabled)."""
    import os
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not auth_token:
        return True
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(auth_token)
        url = request.url
        signature = request.headers.get("X-Twilio-Signature", "")
        return validator.validate(url, request.form, signature)
    except Exception as e:
        logger.warning("Twilio signature validation failed: %s", e)
        return False


@webhook_bp.route('/twilio/sms', methods=['POST'])
def handle_twilio_sms():
    """
    Inbound SMS webhook for Twilio.
    Twilio sends form-urlencoded: From, To, Body, MessageSid, etc.
    Configure in Twilio: Messaging > A message comes in.
    """
    if not _validate_twilio_signature():
        return "", 403
    from_ = request.form.get("From", "")
    to_ = request.form.get("To", "")
    body = (request.form.get("Body") or "").strip()
    message_sid = request.form.get("MessageSid", "")
    logger.info(
        "Twilio inbound SMS from=%s to=%s sid=%s body=%s",
        from_, to_, message_sid, (body[:80] + "..." if len(body) > 80 else body),
    )
    return "", 200


@webhook_bp.route('/twilio/voice', methods=['POST', 'GET'])
def handle_twilio_voice():
    """
    Inbound voice webhook for Twilio.
    Returns TwiML to acknowledge and hang up. Configure in Twilio: Voice > A call comes in.
    """
    if not _validate_twilio_signature():
        return "", 403
    from_ = request.values.get("From", "")
    to_ = request.values.get("To", "")
    logger.info("Twilio inbound voice from=%s to=%s", from_, to_)
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Say voice=\"alice\">Thanks for calling Fikiri. Please contact us by email or the website.</Say><Hangup/></Response>"
    )
    from flask import Response
    return Response(twiml, mimetype="application/xml")


@webhook_bp.route('/forms/submit', methods=['POST'])
def handle_form_submission():
    """
    Generic form submission webhook
    Accepts form data from any website/platform and creates leads/contacts
    
    Security features:
    - API key authentication with scope checking
    - Origin validation (if configured)
    - Idempotency to prevent duplicate submissions
    - Deduplication detection
    """
    try:
        if TRACE_CONTEXT_AVAILABLE:
            trace_id = request.headers.get('X-Trace-ID')
            if trace_id:
                set_trace_id(trace_id)

        key_info, auth_err = _forms_webhook_auth('/api/webhooks/forms/submit')
        if auth_err is not None:
            return auth_err

        user_id = key_info.get('user_id')
        tenant_id = key_info.get('tenant_id')
        
        # Get form data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data received",
                "error_code": "MISSING_DATA"
            }), 400

        payload_json, payload_truncated = _stringify_payload(data)
        correlation_id = get_or_create_correlation_id(request, data)

        form_id = data.get('form_id', 'custom-form')
        fields = data.get('fields', {})
        source = data.get('source', 'website')
        metadata = data.get('metadata', {})
        raw_csid = data.get('client_submission_id')
        client_submission_id = (
            str(raw_csid).strip() if raw_csid is not None and str(raw_csid).strip() != '' else None
        )

        # Extract contact information
        email = fields.get('email') or fields.get('Email') or fields.get('email_address')
        name = fields.get('name') or fields.get('Name') or fields.get('full_name')
        phone = fields.get('phone') or fields.get('Phone') or fields.get('phone_number')

        if not email:
            return jsonify({
                "success": False,
                "error": "Email is required",
                "error_code": "MISSING_EMAIL",
                "correlation_id": correlation_id,
            }), 400

        company = fields.get('company') or fields.get('Company') or fields.get('organization')
        subject = fields.get('subject') or fields.get('Subject') or fields.get('title')

        # Honeypot: reject if bot filled hidden field
        if _check_honeypot(data, fields):
            logger.info("Form submission rejected: honeypot filled")
            hid = _insert_customer_form_intake(
                user_id=user_id,
                api_key_id=key_info.get('api_key_id'),
                form_id=form_id,
                source=source,
                email=email,
                name=name,
                phone=phone,
                company=company,
                subject=subject,
                payload_json=payload_json,
                payload_truncated=payload_truncated,
                status='honeypot_filled',
                error='honeypot_filled',
                lead_id=None,
                request_ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                client_submission_id=client_submission_id,
                supersedes_intake_id=None,
            )
            body = {
                "success": True,
                "message": "Form submitted successfully",
                "deduplicated": False,
                "data": {"intake_id": hid, "message": "Form submitted successfully"},
                "correlation_id": correlation_id,
            }
            return jsonify(body), 200

        # Payload validation
        err_msg, err_code = _validate_webhook_email_and_name(email, name)
        if err_msg:
            return jsonify({"success": False, "error": err_msg, "error_code": err_code}), 400

        from core.idempotency_manager import idempotency_manager, generate_deterministic_key
        idempotency_payload = {
            'operation': 'form_submit',
            'user_id': user_id,
            'form_id': form_id,
            'email': email.lower(),
            'source': source,
            'client_submission_id': client_submission_id,
        }
        idempotency_key = generate_deterministic_key('webhook_form', user_id, idempotency_payload)

        cached_result = idempotency_manager.check_key(idempotency_key)
        if cached_result and cached_result.get('status') == 'completed':
            logger.info("⚠️ Duplicate form submission detected: form_id=%s, email=%s", form_id, email)
            rd = cached_result.get('response_data', {}) or {}
            lead_id = rd.get('lead_id')
            prev_intake_id = rd.get('intake_id')
            dup_intake_id = _insert_customer_form_intake(
                user_id=user_id,
                api_key_id=key_info.get('api_key_id'),
                form_id=form_id,
                source=source,
                email=email,
                name=name,
                phone=phone,
                company=company,
                subject=subject,
                payload_json=payload_json,
                payload_truncated=payload_truncated,
                status='deduplicated',
                error=None,
                lead_id=lead_id,
                request_ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                client_submission_id=client_submission_id,
                supersedes_intake_id=None,
            )
            return jsonify({
                "success": True,
                "lead_id": lead_id,
                "message": "Form submitted successfully",
                "deduplicated": True,
                "idempotency_key": idempotency_key[:16] + "...",
                "correlation_id": rd.get("correlation_id") or correlation_id,
                "data": {
                    "lead_id": lead_id,
                    "intake_id": dup_intake_id or prev_intake_id,
                    "message": "Form submitted successfully",
                },
            }), 200
        
        # Store idempotency key
        idempotency_manager.store_key(
            idempotency_key,
            'webhook_form',
            user_id,
            idempotency_payload,
            ttl=24 * 60 * 60  # 24 hours
        )
        
        try:
            # Create lead in CRM
            from crm.service import enhanced_crm_service
            lead_data = {
                'email': email,
                'name': name or email.split('@')[0],
                'phone': phone,
                'source': source,
                'stage': 'new',
                'correlation_id': correlation_id,
                'metadata': {
                    'form_id': form_id,
                    'submission_data': fields,
                    'idempotency_key': idempotency_key,
                    **metadata
                }
            }
            
            # Add tenant_id if available
            if tenant_id:
                lead_data['tenant_id'] = tenant_id
            
            result = enhanced_crm_service.create_lead(user_id, lead_data)
            if not result.get('success'):
                _insert_customer_form_intake(
                    user_id=user_id,
                    api_key_id=key_info.get('api_key_id'),
                    form_id=form_id,
                    source=source,
                    email=email,
                    name=name,
                    phone=phone,
                    company=company,
                    subject=subject,
                    payload_json=payload_json,
                    payload_truncated=payload_truncated,
                    status='failed',
                    error=result.get('error') or 'lead_create_failed',
                    lead_id=None,
                    request_ip=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    client_submission_id=client_submission_id,
                    supersedes_intake_id=None,
                )
                try:
                    idempotency_manager.update_key_result(
                        idempotency_key,
                        'failed',
                        {'error': result.get('error') or 'lead_create_failed', 'success': False}
                    )
                except Exception:
                    pass
                return jsonify({
                    "success": False,
                    "error": result.get('error', 'Failed to create lead'),
                    "error_code": result.get('error_code', 'LEAD_CREATE_FAILED'),
                    "correlation_id": correlation_id,
                }), 400
            lead_id = (result.get('data') or {}).get('lead_id')

            intake_id = _insert_customer_form_intake(
                user_id=user_id,
                api_key_id=key_info.get('api_key_id'),
                form_id=form_id,
                source=source,
                email=email,
                name=name,
                phone=phone,
                company=company,
                subject=subject,
                payload_json=payload_json,
                payload_truncated=payload_truncated,
                status='completed',
                error=None,
                lead_id=lead_id,
                request_ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                client_submission_id=client_submission_id,
                supersedes_intake_id=None,
            )

            idempotency_manager.update_key_result(
                idempotency_key,
                'completed',
                {
                    'lead_id': lead_id,
                    'intake_id': intake_id,
                    'success': True,
                    'correlation_id': correlation_id,
                },
            )

            logger.info("✅ Form submission processed: form_id=%s, lead_id=%s intake_id=%s", form_id, lead_id, intake_id)

            return jsonify({
                "success": True,
                "lead_id": lead_id,
                "message": "Form submitted successfully",
                "deduplicated": False,
                "idempotency_key": idempotency_key[:16] + "...",
                "correlation_id": correlation_id,
                "data": {
                    "lead_id": lead_id,
                    "intake_id": intake_id,
                    "message": "Lead created",
                },
            }), 200

        except Exception as e:
            idempotency_manager.update_key_result(
                idempotency_key,
                'failed',
                {'error': str(e), 'success': False}
            )

            _insert_customer_form_intake(
                user_id=user_id,
                api_key_id=key_info.get('api_key_id'),
                form_id=form_id,
                source=source,
                email=email,
                name=name,
                phone=phone,
                company=company,
                subject=subject,
                payload_json=payload_json,
                payload_truncated=payload_truncated,
                status='failed',
                error=str(e)[:5000],
                lead_id=None,
                request_ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                client_submission_id=client_submission_id,
                supersedes_intake_id=None,
            )
            raise
        
    except Exception as e:
        logger.error(f"❌ Form submission error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }), 500


@webhook_bp.route('/forms/update', methods=['POST'])
def handle_form_update():
    """Append-only form update: new intake row + CRM merge (no overwrite of prior intake rows)."""
    try:
        if TRACE_CONTEXT_AVAILABLE:
            trace_id = request.headers.get('X-Trace-ID')
            if trace_id:
                set_trace_id(trace_id)

        key_info, auth_err = _forms_webhook_auth('/api/webhooks/forms/update')
        if auth_err is not None:
            return auth_err

        user_id = key_info.get('user_id')
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data received",
                "error_code": "MISSING_DATA",
            }), 400

        payload_json, payload_truncated = _stringify_payload(data)
        correlation_id = get_or_create_correlation_id(request, data)
        form_id = (data.get('form_id') or '').strip()
        raw_csid = data.get('client_submission_id')
        client_submission_id = (
            str(raw_csid).strip() if raw_csid is not None and str(raw_csid).strip() != '' else None
        )
        fields = data.get('fields') or {}
        email = fields.get('email') or fields.get('Email') or fields.get('email_address')
        source = data.get('source')
        metadata = data.get('metadata')
        reason = data.get('reason')

        if not form_id or not client_submission_id:
            return jsonify({
                "success": False,
                "error": "form_id and client_submission_id are required",
                "error_code": "MISSING_FIELDS",
            }), 400
        if not email:
            return jsonify({
                "success": False,
                "error": "fields.email is required",
                "error_code": "MISSING_EMAIL",
            }), 400

        err_msg, err_code = _validate_webhook_email_and_name(email, fields.get('name'))
        if err_msg:
            return jsonify({"success": False, "error": err_msg, "error_code": err_code}), 400

        from core.idempotency_manager import idempotency_manager, generate_deterministic_key
        from core.form_intake_domain import (
            apply_form_update_to_lead,
            find_original_form_intake_row,
            parse_lead_id_from_intake,
        )

        idempotency_payload = {
            'operation': 'form_update',
            'form_id': form_id,
            'client_submission_id': client_submission_id,
            'email': email.lower(),
            'payload_json': payload_json,
        }
        idempotency_key = generate_deterministic_key('webhook_form', user_id, idempotency_payload)
        cached = idempotency_manager.check_key(idempotency_key)
        if cached and cached.get('status') == 'completed' and cached.get('response_data'):
            rd = dict(cached['response_data'])
            rd.setdefault('correlation_id', correlation_id)
            return jsonify(rd), 200
        if cached and cached.get('status') == 'pending':
            return jsonify({
                "success": False,
                "error": "Duplicate request in progress for this idempotency key",
                "error_code": "IDEMPOTENCY_CONFLICT",
                "correlation_id": correlation_id,
            }), 409

        original = find_original_form_intake_row(user_id, form_id, client_submission_id)
        if not original:
            return jsonify({
                "success": False,
                "error": "Original submission not found",
                "error_code": "INTAKE_NOT_FOUND",
                "correlation_id": correlation_id,
            }), 404

        orig_email = (original.get('email') or '').strip().lower()
        if orig_email and email.strip().lower() != orig_email:
            return jsonify({
                "success": False,
                "error": "Email does not match original submission",
                "error_code": "EMAIL_MISMATCH",
                "correlation_id": correlation_id,
            }), 400

        idempotency_manager.store_key(
            idempotency_key,
            'webhook_form_update',
            user_id,
            idempotency_payload,
            ttl=24 * 60 * 60,
        )

        name = fields.get('name') or fields.get('Name') or fields.get('full_name')
        phone = fields.get('phone') or fields.get('Phone') or fields.get('phone_number')
        company = fields.get('company') or fields.get('Company') or fields.get('organization')

        new_intake_id = _insert_customer_form_intake(
            user_id=user_id,
            api_key_id=key_info.get('api_key_id'),
            form_id=form_id,
            source=source or original.get('source') or 'website',
            email=email,
            name=name or original.get('name'),
            phone=phone or original.get('phone'),
            company=company or original.get('company'),
            subject=original.get('subject'),
            payload_json=payload_json,
            payload_truncated=payload_truncated,
            status='updated',
            error=None,
            lead_id=original.get('lead_id'),
            request_ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            client_submission_id=client_submission_id,
            supersedes_intake_id=original.get('id'),
        )

        lead_id = parse_lead_id_from_intake(original.get('lead_id'))
        if lead_id is not None:
            upd = apply_form_update_to_lead(
                user_id,
                lead_id,
                name=name,
                phone=phone,
                company=company,
                source=source,
                metadata=metadata if isinstance(metadata, dict) else None,
                reason=reason,
                correlation_id=correlation_id,
            )
            if not upd.get('success'):
                idempotency_manager.update_key_result(
                    idempotency_key,
                    'failed',
                    {'success': False, 'error': upd.get('error')},
                )
                return jsonify({
                    "success": False,
                    "error": upd.get('error', 'CRM update failed'),
                    "error_code": upd.get('error_code', 'CRM_UPDATE_FAILED'),
                    "correlation_id": correlation_id,
                }), 400

        body = {
            "success": True,
            "correlation_id": correlation_id,
            "data": {
                "intake_id": new_intake_id,
                "lead_id": lead_id,
                "status": "updated",
            },
        }
        idempotency_manager.update_key_result(idempotency_key, 'completed', body)
        return jsonify(body), 200

    except Exception as e:
        logger.error("❌ Form update error: %s", e, exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        }), 500


@webhook_bp.route('/forms/cancel', methods=['POST'])
def handle_form_cancel():
    """Append-only cancel: new intake row, close lead, cancel scheduled work (no deletes)."""
    try:
        if TRACE_CONTEXT_AVAILABLE:
            trace_id = request.headers.get('X-Trace-ID')
            if trace_id:
                set_trace_id(trace_id)

        key_info, auth_err = _forms_webhook_auth('/api/webhooks/forms/cancel')
        if auth_err is not None:
            return auth_err

        user_id = key_info.get('user_id')
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data received",
                "error_code": "MISSING_DATA",
            }), 400

        payload_json, payload_truncated = _stringify_payload(data)
        correlation_id = get_or_create_correlation_id(request, data)
        form_id = (data.get('form_id') or '').strip()
        raw_csid = data.get('client_submission_id')
        client_submission_id = (
            str(raw_csid).strip() if raw_csid is not None and str(raw_csid).strip() != '' else None
        )
        fields = data.get('fields') or {}
        email = (
            data.get('email')
            or fields.get('email')
            or fields.get('Email')
            or fields.get('email_address')
        )
        reason = data.get('reason')
        metadata = data.get('metadata')

        if not form_id or not client_submission_id:
            return jsonify({
                "success": False,
                "error": "form_id and client_submission_id are required",
                "error_code": "MISSING_FIELDS",
                "correlation_id": correlation_id,
            }), 400

        from core.idempotency_manager import idempotency_manager, generate_deterministic_key
        from core.form_intake_domain import (
            apply_form_cancel_to_lead,
            find_original_form_intake_row,
            parse_lead_id_from_intake,
        )

        idempotency_payload = {
            'operation': 'form_cancel',
            'form_id': form_id,
            'client_submission_id': client_submission_id,
            'email': (email or '').strip().lower() if email else '',
            'payload_json': payload_json,
        }
        idempotency_key = generate_deterministic_key('webhook_form', user_id, idempotency_payload)
        cached = idempotency_manager.check_key(idempotency_key)
        if cached and cached.get('status') == 'completed' and cached.get('response_data'):
            rd = dict(cached['response_data'])
            rd.setdefault('correlation_id', correlation_id)
            return jsonify(rd), 200
        if cached and cached.get('status') == 'pending':
            return jsonify({
                "success": False,
                "error": "Duplicate request in progress for this idempotency key",
                "error_code": "IDEMPOTENCY_CONFLICT",
                "correlation_id": correlation_id,
            }), 409

        original = find_original_form_intake_row(user_id, form_id, client_submission_id)
        if not original:
            return jsonify({
                "success": False,
                "error": "Original submission not found",
                "error_code": "INTAKE_NOT_FOUND",
                "correlation_id": correlation_id,
            }), 404

        if email and str(email).strip():
            err_msg, err_code = _validate_webhook_email_and_name(str(email).strip(), None)
            if err_msg:
                return jsonify(
                    {
                        "success": False,
                        "error": err_msg,
                        "error_code": err_code,
                        "correlation_id": correlation_id,
                    }
                ), 400
            orig_email = (original.get('email') or '').strip().lower()
            if orig_email and str(email).strip().lower() != orig_email:
                return jsonify({
                    "success": False,
                    "error": "Email does not match original submission",
                    "error_code": "EMAIL_MISMATCH",
                    "correlation_id": correlation_id,
                }), 400

        idempotency_manager.store_key(
            idempotency_key,
            'webhook_form_cancel',
            user_id,
            idempotency_payload,
            ttl=24 * 60 * 60,
        )

        new_intake_id = _insert_customer_form_intake(
            user_id=user_id,
            api_key_id=key_info.get('api_key_id'),
            form_id=form_id,
            source=original.get('source') or 'website',
            email=original.get('email'),
            name=original.get('name'),
            phone=original.get('phone'),
            company=original.get('company'),
            subject=original.get('subject'),
            payload_json=payload_json,
            payload_truncated=payload_truncated,
            status='cancelled',
            error=None,
            lead_id=original.get('lead_id'),
            request_ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            client_submission_id=client_submission_id,
            supersedes_intake_id=original.get('id'),
        )

        lead_id = parse_lead_id_from_intake(original.get('lead_id'))
        crm_stage = None
        followups_cancelled = False

        if lead_id is not None:
            cancel_meta = metadata if isinstance(metadata, dict) else {}
            result = apply_form_cancel_to_lead(
                user_id,
                lead_id,
                reason=reason,
                metadata=cancel_meta,
                correlation_id=correlation_id,
            )
            if not result.get('success'):
                idempotency_manager.update_key_result(
                    idempotency_key,
                    'failed',
                    {'success': False, 'error': result.get('error')},
                )
                return jsonify({
                    "success": False,
                    "error": result.get('error', 'CRM cancel failed'),
                    "error_code": result.get('error_code', 'CRM_CANCEL_FAILED'),
                    "correlation_id": correlation_id,
                }), 400
            crm_stage = 'closed'
            followups_cancelled = True
        else:
            followups_cancelled = True

        body = {
            "success": True,
            "correlation_id": correlation_id,
            "data": {
                "intake_id": new_intake_id,
                "lead_id": lead_id,
                "status": "cancelled",
                "crm_stage": crm_stage,
                "followups_cancelled": followups_cancelled,
            },
        }
        idempotency_manager.update_key_result(idempotency_key, 'completed', body)
        return jsonify(body), 200

    except Exception as e:
        logger.error("❌ Form cancel error: %s", e, exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        }), 500


@webhook_bp.route('/leads/capture', methods=['POST'])
def handle_lead_capture():
    """
    Lead capture webhook
    Simplified endpoint for capturing leads from websites
    
    Security features:
    - API key authentication with scope checking
    - Origin validation (if configured)
    - Idempotency to prevent duplicate submissions
    - Deduplication detection
    """
    try:
        # Set trace ID
        if TRACE_CONTEXT_AVAILABLE:
            trace_id = request.headers.get('X-Trace-ID')
            if trace_id:
                set_trace_id(trace_id)
        
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API key required (X-API-Key header)",
                "error_code": "MISSING_API_KEY"
            }), 401
        
        # Validate API key
        from core.api_key_manager import api_key_manager
        key_info = api_key_manager.validate_api_key(api_key)
        if not key_info:
            return jsonify({
                "success": False,
                "error": "Invalid API key",
                "error_code": "INVALID_API_KEY"
            }), 401
        
        # Check scope permissions
        allowed_scopes = set(key_info.get('scopes', []))
        required_scopes = ['webhooks:leads', 'webhooks:*', 'leads:create', 'leads:*']
        has_scope = any(scope in allowed_scopes for scope in required_scopes)
        if not has_scope:
            return jsonify({
                "success": False,
                "error": "Insufficient permissions. Required scope: webhooks:leads or leads:create",
                "error_code": "INSUFFICIENT_SCOPE"
            }), 403
        
        # Check origin allowlist (if configured)
        allowed_origins = key_info.get('allowed_origins')
        if allowed_origins:
            origin = request.headers.get('Origin') or request.headers.get('Referer', '').split('/')[0:3]
            origin_str = request.headers.get('Origin', '')
            if origin_str and origin_str not in allowed_origins:
                logger.warning(f"⚠️ Origin not allowed: {origin_str} (allowed: {allowed_origins})")
                return jsonify({
                    "success": False,
                    "error": "Origin not allowed",
                    "error_code": "ORIGIN_NOT_ALLOWED"
                }), 403
        
        # Request logging
        key_prefix = (key_info.get('key_prefix') or '')[:12] or 'unknown'
        logger.info(
            "webhook request endpoint=%s api_key_prefix=%s origin=%s",
            "/api/webhooks/leads/capture",
            key_prefix,
            request.headers.get('Origin') or request.headers.get('Referer') or '-',
        )
        # Rate limit per API key
        err_resp, err_status = _check_webhook_rate_limit(key_info, '/api/webhooks/leads/capture')
        if err_resp is not None:
            resp = jsonify(err_resp)
            resp.headers['Retry-After'] = str(err_resp.get('retry_after_seconds', 60))
            return resp, err_status
        try:
            api_key_manager.record_usage(
                key_info['api_key_id'], '/api/webhooks/leads/capture',
                ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent')
            )
        except Exception:
            pass
        
        user_id = key_info.get('user_id')
        tenant_id = key_info.get('tenant_id')
        
        # Get lead data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data received",
                "error_code": "MISSING_DATA"
            }), 400

        payload_json, payload_truncated = _stringify_payload(data)
        correlation_id = get_or_create_correlation_id(request, data)
        
        email = data.get('email')
        if not email:
            return jsonify({
                "success": False,
                "error": "Email is required",
                "error_code": "MISSING_EMAIL",
                "correlation_id": correlation_id,
            }), 400
        
        # Honeypot
        if _check_honeypot(data, data.get('fields')):
            logger.info("Lead capture rejected: honeypot filled")
            try:
                company = data.get('company') or data.get('Company') or data.get('organization')
                name = data.get('name') or email.split('@')[0]
                db_optimizer.execute_query(
                    """
                    INSERT INTO customer_lead_capture_intake_submissions (
                        user_id, api_key_id, source, email, name, phone, company,
                        payload_json, payload_truncated, status, error, lead_id,
                        request_ip, user_agent
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        key_info.get('api_key_id'),
                        data.get('source', 'website'),
                        email,
                        name,
                        data.get('phone'),
                        company,
                        payload_json,
                        payload_truncated,
                        'failed',
                        'honeypot_filled',
                        None,
                        request.remote_addr,
                        request.headers.get('User-Agent'),
                    ),
                    fetch=False
                )
            except Exception:
                pass
            return jsonify({
                "success": True,
                "message": "Lead captured successfully",
                "deduplicated": False,
                "correlation_id": correlation_id,
            }), 200
        
        # Payload validation
        name = data.get('name') or email.split('@')[0]
        err_msg, err_code = _validate_webhook_email_and_name(email, name)
        if err_msg:
            return jsonify(
                {
                    "success": False,
                    "error": err_msg,
                    "error_code": err_code,
                    "correlation_id": correlation_id,
                }
            ), 400
        
        # Generate idempotency key
        from core.idempotency_manager import idempotency_manager, generate_deterministic_key
        idempotency_payload = {
            'operation': 'lead_capture',
            'user_id': user_id,
            'email': email.lower(),
            'source': data.get('source', 'website')
        }
        idempotency_key = generate_deterministic_key('webhook_lead', user_id, idempotency_payload)
        
        # Check for duplicate submission
        cached_result = idempotency_manager.check_key(idempotency_key)
        if cached_result:
            logger.info(f"⚠️ Duplicate lead capture detected: email={email}")
            try:
                company = data.get('company') or data.get('Company') or data.get('organization')
                name = data.get('name') or email.split('@')[0]
                lead_id = (cached_result.get('response_data', {}) or {}).get('lead_id')
                db_optimizer.execute_query(
                    """
                    INSERT INTO customer_lead_capture_intake_submissions (
                        user_id, api_key_id, source, email, name, phone, company,
                        payload_json, payload_truncated, status, error, lead_id,
                        request_ip, user_agent
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        key_info.get('api_key_id'),
                        data.get('source', 'website'),
                        email,
                        name,
                        data.get('phone'),
                        company,
                        payload_json,
                        payload_truncated,
                        'deduplicated',
                        None,
                        lead_id,
                        request.remote_addr,
                        request.headers.get('User-Agent'),
                    ),
                    fetch=False
                )
            except Exception:
                pass
            rd = cached_result.get('response_data', {}) or {}
            return jsonify({
                "success": True,
                "lead_id": rd.get('lead_id'),
                "message": "Lead captured successfully",
                "deduplicated": True,
                "idempotency_key": idempotency_key[:16] + "...",
                "correlation_id": rd.get('correlation_id') or correlation_id,
            }), 200
        
        # Store idempotency key
        idempotency_manager.store_key(
            idempotency_key,
            'webhook_lead',
            user_id,
            idempotency_payload,
            ttl=24 * 60 * 60  # 24 hours
        )
        
        try:
            # Create lead
            from crm.service import enhanced_crm_service
            lead_data = {
                'email': email,
                'name': data.get('name') or email.split('@')[0],
                'phone': data.get('phone'),
                'source': data.get('source', 'website'),
                'stage': 'new',
                'correlation_id': correlation_id,
                'metadata': {
                    'idempotency_key': idempotency_key,
                    **(data.get('metadata', {}))
                }
            }
            
            if tenant_id:
                lead_data['tenant_id'] = tenant_id
            
            result = enhanced_crm_service.create_lead(user_id, lead_data)
            if not result.get('success'):
                # Persist intake submission (failed create_lead result without exception)
                try:
                    company = data.get('company') or data.get('Company') or data.get('organization')
                    name_failed = data.get('name') or email.split('@')[0]
                    db_optimizer.execute_query(
                        """
                        INSERT INTO customer_lead_capture_intake_submissions (
                            user_id, api_key_id, source, email, name, phone, company,
                            payload_json, payload_truncated, status, error, lead_id,
                            request_ip, user_agent
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            key_info.get('api_key_id'),
                            data.get('source', 'website'),
                            email,
                            name_failed,
                            data.get('phone'),
                            company,
                            payload_json,
                            payload_truncated,
                            'failed',
                            result.get('error') or 'lead_create_failed',
                            None,
                            request.remote_addr,
                            request.headers.get('User-Agent'),
                        ),
                        fetch=False
                    )
                except Exception:
                    pass

                try:
                    idempotency_manager.update_key_result(
                        idempotency_key,
                        'failed',
                        {'error': result.get('error') or 'lead_create_failed', 'success': False}
                    )
                except Exception:
                    pass
                return jsonify({
                    "success": False,
                    "error": result.get('error', 'Failed to create lead'),
                    "error_code": result.get('error_code', 'LEAD_CREATE_FAILED'),
                    "correlation_id": correlation_id,
                }), 400
            lead_id = (result.get('data') or {}).get('lead_id')
            
            # Update idempotency key with result
            idempotency_manager.update_key_result(
                idempotency_key,
                'completed',
                {'lead_id': lead_id, 'success': True, 'correlation_id': correlation_id}
            )

            # Persist intake submission (successful / completed)
            try:
                company = data.get('company') or data.get('Company') or data.get('organization')
                db_optimizer.execute_query(
                    """
                    INSERT INTO customer_lead_capture_intake_submissions (
                        user_id, api_key_id, source, email, name, phone, company,
                        payload_json, payload_truncated, status, error, lead_id,
                        request_ip, user_agent
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        key_info.get('api_key_id'),
                        data.get('source', 'website'),
                        email,
                        name,
                        data.get('phone'),
                        company,
                        payload_json,
                        payload_truncated,
                        'completed',
                        None,
                        lead_id,
                        request.remote_addr,
                        request.headers.get('User-Agent'),
                    ),
                    fetch=False
                )
            except Exception:
                pass
            
            logger.info(f"✅ Lead captured: email={email}, lead_id={lead_id}")
            
            return jsonify({
                "success": True,
                "lead_id": lead_id,
                "message": "Lead captured successfully",
                "deduplicated": False,
                "idempotency_key": idempotency_key[:16] + "...",
                "correlation_id": correlation_id,
            }), 200
            
        except Exception as e:
            # Update idempotency key with error
            idempotency_manager.update_key_result(
                idempotency_key,
                'failed',
                {'error': str(e), 'success': False}
            )

            # Persist intake submission (failed)
            try:
                company = data.get('company') or data.get('Company') or data.get('organization')
                db_optimizer.execute_query(
                    """
                    INSERT INTO customer_lead_capture_intake_submissions (
                        user_id, api_key_id, source, email, name, phone, company,
                        payload_json, payload_truncated, status, error, lead_id,
                        request_ip, user_agent
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        key_info.get('api_key_id'),
                        data.get('source', 'website'),
                        email,
                        data.get('name') or email.split('@')[0],
                        data.get('phone'),
                        company,
                        payload_json,
                        payload_truncated,
                        'failed',
                        str(e)[:5000],
                        None,
                        request.remote_addr,
                        request.headers.get('User-Agent'),
                    ),
                    fetch=False
                )
            except Exception:
                pass
            raise
        
    except Exception as e:
        logger.error(f"❌ Lead capture error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }), 500


@webhook_bp.route('/appointments/submit', methods=['POST'])
def handle_appointment_submit():
    """
    Public/embedded appointment intake endpoint.

    Stores the raw request as ground truth, then performs normalized appointment domain action:
    - action=book -> create appointment
    - action=cancel -> cancel appointment_id
    - action=reschedule -> update appointment_id times/fields
    """
    try:
        # Set trace ID
        if TRACE_CONTEXT_AVAILABLE:
            trace_id = request.headers.get('X-Trace-ID')
            if trace_id:
                set_trace_id(trace_id)

        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({
                "success": False,
                "error": "API key required (X-API-Key header)",
                "error_code": "MISSING_API_KEY"
            }), 401

        from core.api_key_manager import api_key_manager
        key_info = api_key_manager.validate_api_key(api_key)
        if not key_info:
            return jsonify({
                "success": False,
                "error": "Invalid API key",
                "error_code": "INVALID_API_KEY"
            }), 401

        allowed_scopes = set(key_info.get('scopes', []))
        required_scopes = ['webhooks:appointments', 'webhooks:*', 'appointments:create', 'appointments:*']
        has_scope = any(scope in allowed_scopes for scope in required_scopes)
        if not has_scope:
            return jsonify({
                "success": False,
                "error": "Insufficient permissions. Required scope: webhooks:appointments or webhooks:*",
                "error_code": "INSUFFICIENT_SCOPE"
            }), 403

        allowed_origins = key_info.get('allowed_origins')
        if allowed_origins:
            origin_str = request.headers.get('Origin', '')
            if origin_str and origin_str not in allowed_origins:
                return jsonify({
                    "success": False,
                    "error": "Origin not allowed",
                    "error_code": "ORIGIN_NOT_ALLOWED"
                }), 403

        # Rate limit per API key
        err_resp, err_status = _check_webhook_rate_limit(key_info, '/api/webhooks/appointments/submit')
        if err_resp is not None:
            resp = jsonify(err_resp)
            resp.headers['Retry-After'] = str(err_resp.get('retry_after_seconds', 60))
            return resp, err_status

        try:
            api_key_manager.record_usage(
                key_info['api_key_id'],
                '/api/webhooks/appointments/submit',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
        except Exception:
            pass

        user_id = key_info.get('user_id')
        api_key_id = key_info.get('api_key_id')

        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data received",
                "error_code": "MISSING_DATA"
            }), 400

        payload_json, payload_truncated = _stringify_payload(data)

        action = (data.get('action') or '').strip().lower()
        if action not in ('book', 'cancel', 'reschedule'):
            return jsonify({
                "success": False,
                "error": "action must be one of: book, cancel, reschedule",
                "error_code": "INVALID_ACTION"
            }), 400

        appointment_id = data.get('appointment_id') or data.get('id')
        customer_name = data.get('customer_name') or data.get('contact_name')
        customer_email = data.get('customer_email') or data.get('contact_email')
        customer_phone = data.get('customer_phone') or data.get('contact_phone')
        service_type = data.get('service_type') or data.get('title')
        source = data.get('source', 'booking')
        timezone = data.get('timezone')
        requested_date = data.get('requested_date')
        requested_time = data.get('requested_time')

        # Generate idempotency key
        from core.idempotency_manager import idempotency_manager, generate_deterministic_key
        idempotency_payload = {
            'operation': 'webhook_appointment',
            'action': action,
            'appointment_id': appointment_id,
            'email': customer_email.lower() if isinstance(customer_email, str) and customer_email else None,
            'service_type': service_type,
        }
        idempotency_key = generate_deterministic_key('webhook_appointment', user_id, idempotency_payload)

        cached_result = idempotency_manager.check_key(idempotency_key)
        if cached_result:
            appointment_id_cached = (cached_result.get('response_data', {}) or {}).get('appointment_id')
            try:
                _persist_appointment_intake_submission(
                    user_id,
                    api_key_id,
                    source=source,
                    appointment_id=appointment_id_cached,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    service_type=service_type,
                    requested_date=requested_date,
                    requested_time=requested_time,
                    timezone=timezone,
                    status='deduplicated',
                    error_message=None,
                    payload_json=payload_json,
                    payload_truncated=payload_truncated,
                    request_ip=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                )
            except Exception:
                pass
            return jsonify({
                "success": True,
                "appointment_id": appointment_id_cached,
                "message": "Appointment processed successfully",
                "deduplicated": True,
                "idempotency_key": idempotency_key[:16] + "..."
            }), 200

        idempotency_manager.store_key(idempotency_key, 'webhook_appointment', user_id, idempotency_payload, ttl=24 * 60 * 60)

        if action == 'book':
            start_time_str = data.get('start_time') or data.get('requested_datetime') or data.get('start')
            end_time_str = data.get('end_time') or data.get('end')
            duration_minutes = data.get('duration_minutes')

            if not start_time_str:
                return jsonify({
                    "success": False,
                    "error": "start_time is required for action=book",
                    "error_code": "MISSING_START_TIME"
                }), 400

            # Parse timestamps (expect ISO-8601)
            try:
                start_time = datetime.fromisoformat(str(start_time_str).replace('Z', '+00:00'))
            except Exception:
                return jsonify({
                    "success": False,
                    "error": "Invalid start_time format",
                    "error_code": "INVALID_DATE"
                }), 400

            end_time: datetime | None = None
            if end_time_str:
                try:
                    end_time = datetime.fromisoformat(str(end_time_str).replace('Z', '+00:00'))
                except Exception:
                    return jsonify({
                        "success": False,
                        "error": "Invalid end_time format",
                        "error_code": "INVALID_DATE"
                    }), 400
            elif duration_minutes is not None:
                try:
                    dur = int(duration_minutes)
                    end_time = start_time + timedelta(minutes=dur)
                except Exception:
                    return jsonify({
                        "success": False,
                        "error": "duration_minutes must be an integer",
                        "error_code": "INVALID_DURATION"
                    }), 400
            else:
                # Default to 30 minutes if client didn't provide end_time/duration.
                end_time = start_time + timedelta(minutes=30)

            if not requested_date:
                requested_date = start_time.date().isoformat()
            if not requested_time:
                requested_time = start_time.time().isoformat()
            if not timezone:
                timezone = 'UTC' if str(start_time_str).endswith('Z') else None

            try:
                service = AppointmentsService(user_id)
                appointment = service.create_appointment(
                    title=service_type or 'Appointment',
                    start_time=start_time,
                    end_time=end_time,
                    description=data.get('description'),
                    contact_name=customer_name,
                    contact_email=customer_email,
                    contact_phone=customer_phone,
                    location=data.get('location'),
                    notes=data.get('notes'),
                    sync_to_calendar=bool(data.get('sync_to_calendar', False)),
                )

                appointment_id_created = appointment.get('id')
                idempotency_manager.update_key_result(
                    idempotency_key,
                    'completed',
                    {'appointment_id': appointment_id_created, 'success': True},
                )

                _persist_appointment_intake_submission(
                    user_id,
                    api_key_id,
                    source=source,
                    appointment_id=appointment_id_created,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    service_type=service_type,
                    requested_date=requested_date,
                    requested_time=requested_time,
                    timezone=timezone,
                    status='completed',
                    error_message=None,
                    payload_json=payload_json,
                    payload_truncated=payload_truncated,
                    request_ip=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                )

                return jsonify({
                    "success": True,
                    "appointment_id": appointment_id_created,
                    "message": "Appointment processed successfully",
                    "deduplicated": False,
                    "idempotency_key": idempotency_key[:16] + "..."
                }), 200
            except ValueError as e:
                idempotency_manager.update_key_result(
                    idempotency_key,
                    'failed',
                    {'error': str(e), 'success': False},
                )
                _persist_appointment_intake_submission(
                    user_id,
                    api_key_id,
                    source=source,
                    appointment_id=None,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    service_type=service_type,
                    requested_date=requested_date,
                    requested_time=requested_time,
                    timezone=timezone,
                    status='failed',
                    error_message=str(e)[:5000],
                    payload_json=payload_json,
                    payload_truncated=payload_truncated,
                    request_ip=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                )
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "error_code": "VALIDATION_ERROR"
                }), 400
            except Exception as e:
                idempotency_manager.update_key_result(
                    idempotency_key,
                    'failed',
                    {'error': str(e), 'success': False},
                )
                _persist_appointment_intake_submission(
                    user_id,
                    api_key_id,
                    source=source,
                    appointment_id=None,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    service_type=service_type,
                    requested_date=requested_date,
                    requested_time=requested_time,
                    timezone=timezone,
                    status='failed',
                    error_message=str(e)[:5000],
                    payload_json=payload_json,
                    payload_truncated=payload_truncated,
                    request_ip=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                )
                return jsonify({
                    "success": False,
                    "error": "Internal server error",
                    "error_code": "INTERNAL_ERROR"
                }), 500

        if action == 'cancel':
            if not appointment_id:
                return jsonify({
                    "success": False,
                    "error": "appointment_id is required for action=cancel",
                    "error_code": "MISSING_APPOINTMENT_ID"
                }), 400
            try:
                appointment_id_int = int(appointment_id)
            except Exception:
                return jsonify({
                    "success": False,
                    "error": "appointment_id must be an integer",
                    "error_code": "INVALID_APPOINTMENT_ID"
                }), 400

            try:
                service = AppointmentsService(user_id)
                appointment = service.cancel_appointment(appointment_id_int)

                idempotency_manager.update_key_result(
                    idempotency_key,
                    'completed',
                    {'appointment_id': appointment_id_int, 'success': True},
                )

                _persist_appointment_intake_submission(
                    user_id,
                    api_key_id,
                    source=source,
                    appointment_id=appointment_id_int,
                    customer_name=appointment.get('contact_name') if isinstance(appointment, dict) else customer_name,
                    customer_email=appointment.get('contact_email') if isinstance(appointment, dict) else customer_email,
                    customer_phone=appointment.get('contact_phone') if isinstance(appointment, dict) else customer_phone,
                    service_type=service_type or appointment.get('title') if isinstance(appointment, dict) else None,
                    requested_date=requested_date,
                    requested_time=requested_time,
                    timezone=timezone,
                    status='cancelled',
                    error_message=None,
                    payload_json=payload_json,
                    payload_truncated=payload_truncated,
                    request_ip=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                )

                return jsonify({
                    "success": True,
                    "appointment_id": appointment_id_int,
                    "message": "Appointment processed successfully",
                    "deduplicated": False,
                    "idempotency_key": idempotency_key[:16] + "..."
                }), 200
            except ValueError as e:
                idempotency_manager.update_key_result(
                    idempotency_key,
                    'failed',
                    {'error': str(e), 'success': False},
                )
                _persist_appointment_intake_submission(
                    user_id,
                    api_key_id,
                    source=source,
                    appointment_id=appointment_id_int,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    service_type=service_type,
                    requested_date=requested_date,
                    requested_time=requested_time,
                    timezone=timezone,
                    status='failed',
                    error_message=str(e)[:5000],
                    payload_json=payload_json,
                    payload_truncated=payload_truncated,
                    request_ip=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                )
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "error_code": "VALIDATION_ERROR"
                }), 400

            except Exception as e:
                idempotency_manager.update_key_result(
                    idempotency_key,
                    'failed',
                    {'error': str(e), 'success': False},
                )
                _persist_appointment_intake_submission(
                    user_id,
                    api_key_id,
                    source=source,
                    appointment_id=appointment_id_int,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    service_type=service_type,
                    requested_date=requested_date,
                    requested_time=requested_time,
                    timezone=timezone,
                    status='failed',
                    error_message=str(e)[:5000],
                    payload_json=payload_json,
                    payload_truncated=payload_truncated,
                    request_ip=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                )
                return jsonify({
                    "success": False,
                    "error": "Internal server error",
                    "error_code": "INTERNAL_ERROR"
                }), 500

        # action == reschedule
        if not appointment_id:
            return jsonify({
                "success": False,
                "error": "appointment_id is required for action=reschedule",
                "error_code": "MISSING_APPOINTMENT_ID"
            }), 400
        try:
            appointment_id_int = int(appointment_id)
        except Exception:
            return jsonify({
                "success": False,
                "error": "appointment_id must be an integer",
                "error_code": "INVALID_APPOINTMENT_ID"
            }), 400

        start_time_str = data.get('start_time') or data.get('start')
        end_time_str = data.get('end_time') or data.get('end')
        if not start_time_str and not end_time_str:
            return jsonify({
                "success": False,
                "error": "start_time and/or end_time are required for action=reschedule",
                "error_code": "MISSING_TIMES"
            }), 400

        updates: dict[str, object] = {}
        if start_time_str:
            try:
                updates['start_time'] = datetime.fromisoformat(str(start_time_str).replace('Z', '+00:00')).isoformat()
            except Exception:
                return jsonify({
                    "success": False,
                    "error": "Invalid start_time format",
                    "error_code": "INVALID_DATE"
                }), 400
        if end_time_str:
            try:
                updates['end_time'] = datetime.fromisoformat(str(end_time_str).replace('Z', '+00:00')).isoformat()
            except Exception:
                return jsonify({
                    "success": False,
                    "error": "Invalid end_time format",
                    "error_code": "INVALID_DATE"
                }), 400

        # Optional fields
        if 'title' in data:
            updates['title'] = data.get('title')
        if 'description' in data:
            updates['description'] = data.get('description')
        if 'location' in data:
            updates['location'] = data.get('location')
        if 'notes' in data:
            updates['notes'] = data.get('notes')
        if customer_name:
            updates['contact_name'] = customer_name
        if customer_email:
            updates['contact_email'] = customer_email
        if customer_phone:
            updates['contact_phone'] = customer_phone
        if 'sync_to_calendar' in data:
            updates['sync_to_calendar'] = bool(data.get('sync_to_calendar'))

        # For reschedule, store requested date/time if derivable.
        if not requested_date and updates.get('start_time'):
            try:
                requested_date = datetime.fromisoformat(str(updates['start_time'])).date().isoformat()
            except Exception:
                pass
        if not requested_time and updates.get('start_time'):
            try:
                requested_time = datetime.fromisoformat(str(updates['start_time'])).time().isoformat()
            except Exception:
                pass
        if not timezone and isinstance(start_time_str, str) and start_time_str.endswith('Z'):
            timezone = 'UTC'

        try:
            service = AppointmentsService(user_id)
            appointment = service.update_appointment(appointment_id_int, updates)

            idempotency_manager.update_key_result(
                idempotency_key,
                'completed',
                {'appointment_id': appointment_id_int, 'success': True},
            )

            _persist_appointment_intake_submission(
                user_id,
                api_key_id,
                source=source,
                appointment_id=appointment_id_int,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                service_type=service_type or updates.get('title'),
                requested_date=requested_date,
                requested_time=requested_time,
                timezone=timezone,
                status='rescheduled',
                error_message=None,
                payload_json=payload_json,
                payload_truncated=payload_truncated,
                request_ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
            )

            return jsonify({
                "success": True,
                "appointment_id": appointment_id_int,
                "message": "Appointment processed successfully",
                "deduplicated": False,
                "idempotency_key": idempotency_key[:16] + "..."
            }), 200
        except ValueError as e:
            idempotency_manager.update_key_result(
                idempotency_key,
                'failed',
                {'error': str(e), 'success': False},
            )
            _persist_appointment_intake_submission(
                user_id,
                api_key_id,
                source=source,
                appointment_id=appointment_id_int,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                service_type=service_type,
                requested_date=requested_date,
                requested_time=requested_time,
                timezone=timezone,
                status='failed',
                error_message=str(e)[:5000],
                payload_json=payload_json,
                payload_truncated=payload_truncated,
                request_ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
            )
            return jsonify({
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR"
            }), 400
        except Exception as e:
            idempotency_manager.update_key_result(
                idempotency_key,
                'failed',
                {'error': str(e), 'success': False},
            )
            _persist_appointment_intake_submission(
                user_id,
                api_key_id,
                source=source,
                appointment_id=appointment_id_int,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                service_type=service_type,
                requested_date=requested_date,
                requested_time=requested_time,
                timezone=timezone,
                status='failed',
                error_message=str(e)[:5000],
                payload_json=payload_json,
                payload_truncated=payload_truncated,
                request_ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
            )
            return jsonify({
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }), 500

    except Exception as e:
        logger.error(f"❌ Appointment submit error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }), 500


@webhook_bp.route('/appointments/cancel', methods=['POST'])
def handle_appointment_cancel():
    """
    Public/embedded appointment intake for cancellations.

    Thin wrapper around `POST /api/webhooks/appointments/submit` to keep:
    - idempotency
    - persistence into `customer_appointment_intake_submissions`
    - normalized appointment cancel execution
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False,
            "error": "No data received",
            "error_code": "MISSING_DATA"
        }), 400
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid payload format",
            "error_code": "INVALID_DATA"
        }), 400

    # Flask caches parsed JSON per request; mutating `data` should affect the
    # subsequent `request.get_json()` call inside handle_appointment_submit().
    data["action"] = "cancel"
    return handle_appointment_submit()


@webhook_bp.route('/appointments/reschedule', methods=['POST'])
def handle_appointment_reschedule():
    """
    Public/embedded appointment intake for reschedules.

    Thin wrapper around `POST /api/webhooks/appointments/submit` to keep:
    - idempotency
    - persistence into `customer_appointment_intake_submissions`
    - normalized appointment reschedule execution
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False,
            "error": "No data received",
            "error_code": "MISSING_DATA"
        }), 400
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid payload format",
            "error_code": "INVALID_DATA"
        }), 400

    # See note in handle_appointment_cancel.
    data["action"] = "reschedule"
    return handle_appointment_submit()
