"""
Docs & Forms API Integration for Fikiri Solutions
Unified API for document processing, form automation, templates, and analytics
"""

import json
import logging
import io
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import uuid

from core.ai_document_processor import get_document_processor
from core.form_automation_system import get_form_automation
from core.document_templates_system import get_document_templates
from core.document_analytics_system import get_document_analytics

logger = logging.getLogger(__name__)

# Create Blueprint
docs_forms_bp = Blueprint('docs_forms', __name__, url_prefix='/api/docs-forms')

# Initialize systems
doc_processor = get_document_processor()
form_automation = get_form_automation()
doc_templates = get_document_templates()
doc_analytics = get_document_analytics()

# Document Processing Endpoints

@docs_forms_bp.route('/documents/process', methods=['POST'])
def process_document():
    """Process uploaded document"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        # Get user ID from request
        user_id = request.form.get('user_id', 1, type=int)
        session_id = request.form.get('session_id')
        
        # Secure filename
        filename = secure_filename(file.filename)
        
        # Read file content
        file_content = file.read()
        
        # Check if format is supported
        if not doc_processor.is_format_supported(filename):
            return jsonify({
                "success": False, 
                "error": f"Unsupported file format: {filename}"
            }), 400
        
        # Process document
        start_time = datetime.now()
        result = doc_processor.process_document(filename, file_content)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Track analytics
        doc_analytics.track_document_processing(
            user_id=user_id,
            file_type=result.content.metadata.file_type if result.content else "unknown",
            processing_time=processing_time,
            success=result.success,
            error=result.error,
            session_id=session_id
        )
        
        if result.success:
            return jsonify({
                "success": True,
                "document_id": str(uuid.uuid4()),
                "content": {
                    "text": result.content.text,
                    "entities": result.content.entities,
                    "confidence": result.content.confidence,
                    "metadata": {
                        "filename": result.content.metadata.filename,
                        "file_type": result.content.metadata.file_type,
                        "file_size": result.content.metadata.file_size,
                        "pages": result.content.metadata.pages,
                        "processing_time": processing_time
                    }
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": result.error,
                "processing_time": processing_time
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Document processing failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/documents/capabilities', methods=['GET'])
def get_processing_capabilities():
    """Get document processing capabilities"""
    try:
        capabilities = doc_processor.get_processing_capabilities()
        supported_formats = doc_processor.get_supported_formats()
        
        return jsonify({
            "success": True,
            "capabilities": capabilities,
            "supported_formats": supported_formats
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get capabilities: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Form Automation Endpoints

@docs_forms_bp.route('/forms/templates', methods=['GET'])
def list_form_templates():
    """List all form templates"""
    try:
        industry = request.args.get('industry')
        templates = form_automation.list_form_templates(industry)
        
        return jsonify({
            "success": True,
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "industry": t.industry,
                    "purpose": t.purpose,
                    "field_count": len(t.fields),
                    "created_at": t.created_at.isoformat()
                } for t in templates
            ]
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to list form templates: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/forms/templates/<template_id>', methods=['GET'])
def get_form_template(template_id):
    """Get specific form template"""
    try:
        template = form_automation.get_form_template(template_id)
        
        if not template:
            return jsonify({"success": False, "error": "Template not found"}), 404
        
        return jsonify({
            "success": True,
            "template": {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "industry": template.industry,
                "purpose": template.purpose,
                "fields": [
                    {
                        "id": f.id,
                        "name": f.name,
                        "label": f.label,
                        "field_type": f.field_type.value,
                        "placeholder": f.placeholder,
                        "help_text": f.help_text,
                        "required": f.required,
                        "validation_rules": f.validation_rules,
                        "options": f.options,
                        "default_value": f.default_value,
                        "order": f.order
                    } for f in template.fields
                ],
                "settings": template.settings,
                "created_at": template.created_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get form template: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/forms/templates/<template_id>/html', methods=['GET'])
def get_form_html(template_id):
    """Get form HTML for template"""
    try:
        form_action = request.args.get('action', '/api/docs-forms/forms/submit')
        html = form_automation.generate_form_html(template_id, form_action)
        
        return html, 200, {'Content-Type': 'text/html'}
        
    except Exception as e:
        logger.error(f"❌ Failed to generate form HTML: {e}")
        return f"<p>Error generating form: {str(e)}</p>", 500

@docs_forms_bp.route('/forms/submit', methods=['POST'])
def submit_form():
    """Submit form data"""
    try:
        # Get form data
        if request.is_json:
            data = request.json
            form_id = data.get('form_id')
            form_data = data.get('data', {})
            user_id = data.get('user_id', 1)
        else:
            form_id = request.form.get('form_id')
            user_id = request.form.get('user_id', 1, type=int)
            form_data = {k: v for k, v in request.form.items() if k not in ['form_id', 'user_id']}
        
        if not form_id:
            return jsonify({"success": False, "error": "Form ID is required"}), 400
        
        # Track form submission start
        session_id = request.headers.get('X-Session-ID')
        start_time = datetime.now()
        
        # Submit form
        result = form_automation.submit_form(
            form_id=form_id,
            data=form_data,
            user_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Calculate completion time
        completion_time = (datetime.now() - start_time).total_seconds()
        
        # Track analytics
        doc_analytics.track_form_submission(
            user_id=user_id,
            form_id=form_id,
            completion_time=completion_time,
            success=result['success'],
            validation_errors=result.get('errors', []),
            session_id=session_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Form submission failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/forms/<form_id>/submissions', methods=['GET'])
def get_form_submissions(form_id):
    """Get form submissions"""
    try:
        user_id = request.args.get('user_id', type=int)
        submissions = form_automation.get_form_submissions(form_id, user_id)
        
        return jsonify({
            "success": True,
            "submissions": [
                {
                    "id": s.id,
                    "form_id": s.form_id,
                    "user_id": s.user_id,
                    "data": s.data,
                    "submitted_at": s.submitted_at.isoformat(),
                    "ip_address": s.ip_address
                } for s in submissions
            ]
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get form submissions: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Document Templates Endpoints

@docs_forms_bp.route('/templates', methods=['GET'])
def list_document_templates():
    """List document templates"""
    try:
        document_type = request.args.get('document_type')
        industry = request.args.get('industry')
        
        templates = doc_templates.list_templates(
            document_type=document_type,
            industry=industry
        )
        
        return jsonify({
            "success": True,
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "document_type": t.document_type.value,
                    "industry": t.industry,
                    "format": t.format.value,
                    "variable_count": len(t.variables),
                    "created_at": t.created_at.isoformat()
                } for t in templates
            ]
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to list document templates: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/templates/<template_id>', methods=['GET'])
def get_document_template(template_id):
    """Get specific document template"""
    try:
        template = doc_templates.get_template(template_id)
        
        if not template:
            return jsonify({"success": False, "error": "Template not found"}), 404
        
        return jsonify({
            "success": True,
            "template": {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "document_type": template.document_type.value,
                "industry": template.industry,
                "format": template.format.value,
                "variables": [
                    {
                        "name": v.name,
                        "label": v.label,
                        "type": v.type,
                        "required": v.required,
                        "default_value": v.default_value,
                        "description": v.description,
                        "options": v.options
                    } for v in template.variables
                ],
                "settings": template.settings,
                "created_at": template.created_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get document template: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/templates/<template_id>/generate', methods=['POST'])
def generate_document(template_id):
    """Generate document from template"""
    try:
        data = request.json
        variables = data.get('variables', {})
        user_id = data.get('user_id', 1)
        
        # Track template usage start
        session_id = request.headers.get('X-Session-ID')
        start_time = datetime.now()
        
        # Generate document
        document = doc_templates.generate_document(template_id, variables, user_id)
        
        # Calculate generation time
        generation_time = (datetime.now() - start_time).total_seconds()
        
        # Track analytics
        template = doc_templates.get_template(template_id)
        if template:
            doc_analytics.track_template_usage(
                user_id=user_id,
                template_id=template_id,
                document_type=template.document_type.value,
                generation_time=generation_time,
                session_id=session_id
            )
        
        return jsonify({
            "success": True,
            "document": {
                "id": document.id,
                "content": document.content,
                "format": document.format.value,
                "generated_at": document.generated_at.isoformat(),
                "metadata": document.metadata
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Document generation failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/documents/<doc_id>', methods=['GET'])
def get_generated_document(doc_id):
    """Get generated document"""
    try:
        document = doc_templates.get_generated_document(doc_id)
        
        if not document:
            return jsonify({"success": False, "error": "Document not found"}), 404
        
        return jsonify({
            "success": True,
            "document": {
                "id": document.id,
                "template_id": document.template_id,
                "content": document.content,
                "format": document.format.value,
                "generated_at": document.generated_at.isoformat(),
                "metadata": document.metadata
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get generated document: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/documents/<doc_id>/convert', methods=['POST'])
def convert_document_format(doc_id):
    """Convert document to different format"""
    try:
        data = request.json
        target_format = data.get('format')
        
        if not target_format:
            return jsonify({"success": False, "error": "Target format is required"}), 400
        
        content = doc_templates.convert_document_format(doc_id, target_format)
        
        return jsonify({
            "success": True,
            "content": content,
            "format": target_format
        })
        
    except Exception as e:
        logger.error(f"❌ Document conversion failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Analytics Endpoints

@docs_forms_bp.route('/analytics/report', methods=['GET'])
def get_analytics_report():
    """Get comprehensive analytics report"""
    try:
        days = request.args.get('days', 30, type=int)
        report = doc_analytics.get_comprehensive_report(days)
        
        return jsonify({
            "success": True,
            "report": report
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get analytics report: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/analytics/real-time', methods=['GET'])
def get_real_time_stats():
    """Get real-time statistics"""
    try:
        stats = doc_analytics.get_real_time_stats()
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get real-time stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/analytics/processing', methods=['GET'])
def get_processing_metrics():
    """Get document processing metrics"""
    try:
        days = request.args.get('days', 30, type=int)
        metrics = doc_analytics.get_processing_metrics(days)
        
        return jsonify({
            "success": True,
            "metrics": {
                "total_documents": metrics.total_documents,
                "successful_processes": metrics.successful_processes,
                "failed_processes": metrics.failed_processes,
                "avg_processing_time": metrics.avg_processing_time,
                "success_rate": metrics.success_rate,
                "most_common_format": metrics.most_common_format,
                "formats_processed": metrics.formats_processed
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get processing metrics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/analytics/forms', methods=['GET'])
def get_form_metrics():
    """Get form submission metrics"""
    try:
        days = request.args.get('days', 30, type=int)
        metrics = doc_analytics.get_form_metrics(days)
        
        return jsonify({
            "success": True,
            "metrics": {
                "total_submissions": metrics.total_submissions,
                "successful_submissions": metrics.successful_submissions,
                "validation_failures": metrics.validation_failures,
                "avg_completion_time": metrics.avg_completion_time,
                "completion_rate": metrics.completion_rate,
                "most_popular_form": metrics.most_popular_form,
                "submissions_by_form": metrics.submissions_by_form
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get form metrics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@docs_forms_bp.route('/analytics/export', methods=['GET'])
def export_analytics():
    """Export analytics data"""
    try:
        days = request.args.get('days', 30, type=int)
        format_type = request.args.get('format', 'json')
        
        data = doc_analytics.export_analytics_data(days, format_type)
        
        # Create file response
        filename = f"fikiri_analytics_{datetime.now().strftime('%Y%m%d')}.{format_type}"
        
        return send_file(
            io.BytesIO(data.encode()),
            mimetype=f'application/{format_type}',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to export analytics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Status and Health Endpoints

@docs_forms_bp.route('/status', methods=['GET'])
def get_system_status():
    """Get system status"""
    try:
        processing_capabilities = doc_processor.get_processing_capabilities()
        template_stats = doc_templates.get_template_statistics()
        form_stats = form_automation.get_form_statistics("landscaping_quote")  # Example form
        real_time_stats = doc_analytics.get_real_time_stats()
        
        return jsonify({
            "success": True,
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "systems": {
                "document_processing": {
                    "status": "operational",
                    "capabilities": processing_capabilities
                },
                "form_automation": {
                    "status": "operational",
                    "total_templates": len(form_automation.form_templates),
                    "total_submissions": len(form_automation.submissions)
                },
                "document_templates": {
                    "status": "operational",
                    "statistics": template_stats
                },
                "analytics": {
                    "status": "operational",
                    "real_time_stats": real_time_stats
                }
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get system status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Error handlers
@docs_forms_bp.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404

@docs_forms_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"success": False, "error": "Method not allowed"}), 405

@docs_forms_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500
