"""
Webhook API Endpoints for Fikiri Solutions
Handles incoming webhook requests from form services
"""

import json
import logging
from flask import Blueprint, request, jsonify
from core.webhook_intake_service import get_webhook_service
from core.minimal_config import get_config

logger = logging.getLogger(__name__)

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
        # Set trace ID
        if TRACE_CONTEXT_AVAILABLE:
            trace_id = request.headers.get('X-Trace-ID')
            if trace_id:
                set_trace_id(trace_id)
        
        # Get API key from header (for authentication)
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
        required_scopes = ['webhooks:forms', 'webhooks:*', 'leads:create', 'leads:*']
        has_scope = any(scope in allowed_scopes for scope in required_scopes)
        if not has_scope:
            return jsonify({
                "success": False,
                "error": "Insufficient permissions. Required scope: webhooks:forms or leads:create",
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
        
        form_id = data.get('form_id', 'custom-form')
        fields = data.get('fields', {})
        source = data.get('source', 'website')
        metadata = data.get('metadata', {})
        
        # Extract contact information
        email = fields.get('email') or fields.get('Email') or fields.get('email_address')
        name = fields.get('name') or fields.get('Name') or fields.get('full_name')
        phone = fields.get('phone') or fields.get('Phone') or fields.get('phone_number')
        
        if not email:
            return jsonify({
                "success": False,
                "error": "Email is required",
                "error_code": "MISSING_EMAIL"
            }), 400
        
        # Generate idempotency key
        from core.idempotency_manager import idempotency_manager, generate_deterministic_key
        idempotency_payload = {
            'operation': 'form_submission',
            'user_id': user_id,
            'form_id': form_id,
            'email': email.lower(),
            'source': source
        }
        idempotency_key = generate_deterministic_key('webhook_form', user_id, idempotency_payload)
        
        # Check for duplicate submission
        cached_result = idempotency_manager.check_key(idempotency_key)
        if cached_result:
            logger.info(f"⚠️ Duplicate form submission detected: form_id={form_id}, email={email}")
            return jsonify({
                "success": True,
                "lead_id": cached_result.get('response_data', {}).get('lead_id'),
                "message": "Form submitted successfully",
                "deduplicated": True,
                "idempotency_key": idempotency_key[:16] + "..."
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
            lead_id = result.get('lead_id')
            
            # Update idempotency key with result
            idempotency_manager.update_key_result(
                idempotency_key,
                'completed',
                {'lead_id': lead_id, 'success': True}
            )
            
            logger.info(f"✅ Form submission processed: form_id={form_id}, lead_id={lead_id}")
            
            return jsonify({
                "success": True,
                "lead_id": lead_id,
                "message": "Form submitted successfully",
                "deduplicated": False,
                "idempotency_key": idempotency_key[:16] + "..."
            }), 200
            
        except Exception as e:
            # Update idempotency key with error
            idempotency_manager.update_key_result(
                idempotency_key,
                'failed',
                {'error': str(e), 'success': False}
            )
            raise
        
    except Exception as e:
        logger.error(f"❌ Form submission error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR"
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
        
        email = data.get('email')
        if not email:
            return jsonify({
                "success": False,
                "error": "Email is required",
                "error_code": "MISSING_EMAIL"
            }), 400
        
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
            return jsonify({
                "success": True,
                "lead_id": cached_result.get('response_data', {}).get('lead_id'),
                "message": "Lead captured successfully",
                "deduplicated": True,
                "idempotency_key": idempotency_key[:16] + "..."
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
                'metadata': {
                    'idempotency_key': idempotency_key,
                    **(data.get('metadata', {}))
                }
            }
            
            if tenant_id:
                lead_data['tenant_id'] = tenant_id
            
            result = enhanced_crm_service.create_lead(user_id, lead_data)
            lead_id = result.get('lead_id')
            
            # Update idempotency key with result
            idempotency_manager.update_key_result(
                idempotency_key,
                'completed',
                {'lead_id': lead_id, 'success': True}
            )
            
            logger.info(f"✅ Lead captured: email={email}, lead_id={lead_id}")
            
            return jsonify({
                "success": True,
                "lead_id": lead_id,
                "message": "Lead captured successfully",
                "deduplicated": False,
                "idempotency_key": idempotency_key[:16] + "..."
            }), 200
            
        except Exception as e:
            # Update idempotency key with error
            idempotency_manager.update_key_result(
                idempotency_key,
                'failed',
                {'error': str(e), 'success': False}
            )
            raise
        
    except Exception as e:
        logger.error(f"❌ Lead capture error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }), 500
