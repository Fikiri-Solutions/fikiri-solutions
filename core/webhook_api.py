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

# Create blueprint
webhook_bp = Blueprint('webhook', __name__, url_prefix='/api/webhooks')

@webhook_bp.route('/tally', methods=['POST'])
def handle_tally_webhook():
    """Handle webhook from Tally forms"""
    try:
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
                "/api/webhooks/test"
            ]
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook status error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500
