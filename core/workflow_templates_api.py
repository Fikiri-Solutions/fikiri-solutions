"""
Workflow Templates API
REST endpoints for managing workflow templates
"""

from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any
from core.workflow_templates_system import workflow_templates_system, WorkflowCategory
# from core.enterprise_logging import log_api_request

logger = logging.getLogger(__name__)

# Create blueprint
workflow_templates_bp = Blueprint('workflow_templates', __name__, url_prefix='/api/workflow-templates')

@workflow_templates_bp.route('/templates', methods=['GET'])
def get_templates():
    """Get all workflow templates with optional filtering"""
    try:
        # Get query parameters
        category = request.args.get('category')
        industry = request.args.get('industry')
        complexity = request.args.get('complexity')
        search = request.args.get('search')
        
        templates = workflow_templates_system.templates
        
        # Apply filters
        if category:
            try:
                category_enum = WorkflowCategory(category)
                templates = workflow_templates_system.get_templates_by_category(category_enum)
            except ValueError:
                return jsonify({'error': 'Invalid category'}), 400
        
        if industry:
            templates = [t for t in templates if t.industry.lower() == industry.lower()]
        
        if complexity:
            templates = [t for t in templates if t.complexity == complexity]
        
        if search:
            templates = workflow_templates_system.search_templates(search)
        
        # Convert to dict format
        templates_data = []
        for template in templates:
            templates_data.append({
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'category': template.category.value,
                'industry': template.industry,
                'complexity': template.complexity,
                'estimated_setup_time': template.estimated_setup_time,
                'features': template.features,
                'prerequisites': template.prerequisites,
                'success_metrics': template.success_metrics
            })
        
        return jsonify({
            'success': True,
            'templates': templates_data,
            'total': len(templates_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return jsonify({'error': str(e)}), 500

@workflow_templates_bp.route('/templates/<template_id>', methods=['GET'])
def get_template(template_id: str):
    """Get specific workflow template"""
    try:
        template = workflow_templates_system.get_template_by_id(template_id)
        
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        
        template_data = {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'category': template.category.value,
            'industry': template.industry,
            'complexity': template.complexity,
            'estimated_setup_time': template.estimated_setup_time,
            'features': template.features,
            'trigger': template.trigger,
            'actions': template.actions,
            'variables': template.variables,
            'prerequisites': template.prerequisites,
            'success_metrics': template.success_metrics
        }
        
        return jsonify({
            'success': True,
            'template': template_data
        })
        
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        return jsonify({'error': str(e)}), 500

@workflow_templates_bp.route('/templates/<template_id>/create', methods=['POST'])
def create_automation_from_template(template_id: str):
    """Create automation rule from template"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        customizations = data.get('customizations', {})
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        result = workflow_templates_system.create_automation_from_template(
            template_id, user_id, customizations
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Error creating automation from template: {e}")
        return jsonify({'error': str(e)}), 500

@workflow_templates_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all workflow categories"""
    try:
        categories = [category.value for category in WorkflowCategory]
        return jsonify({
            'success': True,
            'categories': categories
        })
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({'error': str(e)}), 500

@workflow_templates_bp.route('/industries', methods=['GET'])
def get_industries():
    """Get all industries"""
    try:
        industries = list(set(template.industry for template in workflow_templates_system.templates))
        return jsonify({
            'success': True,
            'industries': industries
        })
        
    except Exception as e:
        logger.error(f"Error getting industries: {e}")
        return jsonify({'error': str(e)}), 500

@workflow_templates_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get template statistics"""
    try:
        stats = workflow_templates_system.get_template_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'error': str(e)}), 500

@workflow_templates_bp.route('/search', methods=['GET'])
def search_templates():
    """Search templates"""
    try:
        query = request.args.get('q')
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        templates = workflow_templates_system.search_templates(query)
        
        templates_data = []
        for template in templates:
            templates_data.append({
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'category': template.category.value,
                'industry': template.industry,
                'complexity': template.complexity,
                'estimated_setup_time': template.estimated_setup_time,
                'features': template.features
            })
        
        return jsonify({
            'success': True,
            'templates': templates_data,
            'total': len(templates_data),
            'query': query
        })
        
    except Exception as e:
        logger.error(f"Error searching templates: {e}")
        return jsonify({'error': str(e)}), 500

@workflow_templates_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        stats = workflow_templates_system.get_template_statistics()
        return jsonify({
            'success': True,
            'status': 'healthy',
            'templates_loaded': stats['total_templates']
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'error': str(e)}), 500
