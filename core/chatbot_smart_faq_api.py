"""
Chatbot/Smart FAQ API Integration for Fikiri Solutions
Unified API for chatbot, FAQ, knowledge base, and multi-channel support
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from flask import Blueprint, request, jsonify

from core.smart_faq_system import get_smart_faq, FAQCategory
from core.knowledge_base_system import get_knowledge_base, DocumentType
from core.context_aware_responses import get_context_system, MessageType
from core.multi_channel_support import get_multi_channel_system, ChannelType
from core.minimal_vector_search import MinimalVectorSearch
from core.api_validation import handle_api_errors, create_error_response

logger = logging.getLogger(__name__)

# Create Blueprint
chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/chatbot')

# Initialize systems
faq_system = get_smart_faq()
knowledge_base = get_knowledge_base()
context_system = get_context_system()
multi_channel = get_multi_channel_system()
vector_search = MinimalVectorSearch()

# Smart FAQ Endpoints

@chatbot_bp.route('/faq/search', methods=['POST'])
@handle_api_errors
def search_faqs():
    """Search FAQs with intelligent matching"""
    data = request.json
    query = data.get('query', '') if data else ''
    max_results = data.get('max_results', 5) if data else 5
    
    if not query:
        return create_error_response("Query is required", 400, 'MISSING_QUERY')
    
    # Search FAQs
    response = faq_system.search_faqs(query, max_results)
    
    if response.success:
        return jsonify({
            "success": True,
            "query": response.query if hasattr(response, 'query') else query,
            "matches": [
                {
                    "faq_id": match.faq_entry.id,
                    "question": match.faq_entry.question,
                    "answer": match.faq_entry.answer,
                    "confidence": match.confidence,
                    "match_type": match.match_type,
                    "category": match.faq_entry.category.value,
                    "explanation": match.explanation
                } for match in response.matches
            ],
            "best_match": {
                "faq_id": response.best_match.faq_entry.id,
                "question": response.best_match.faq_entry.question,
                "answer": response.best_match.faq_entry.answer,
                "confidence": response.best_match.confidence
            } if response.best_match else None,
            "suggested_questions": response.suggested_questions,
            "fallback_response": response.fallback_response,
            "processing_time": response.processing_time
        })
    else:
        return create_error_response(
            "FAQ search failed", 
            500, 
            'FAQ_SEARCH_ERROR'
        )

@chatbot_bp.route('/faq/categories', methods=['GET'])
@handle_api_errors
def get_faq_categories():
    """Get all FAQ categories"""
    try:
        categories = [category.value for category in FAQCategory]
        
        return jsonify({
            "success": True,
            "categories": categories
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get FAQ categories: {e}")
        return create_error_response("Failed to get FAQ categories", 500, 'FAQ_CATEGORIES_ERROR')

@chatbot_bp.route('/faq/statistics', methods=['GET'])
@handle_api_errors
def get_faq_statistics():
    """Get FAQ system statistics"""
    try:
        stats = faq_system.get_faq_statistics()
        
        return jsonify({
            "success": True,
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get FAQ statistics: {e}")
        return create_error_response("Failed to get FAQ statistics", 500, 'FAQ_STATISTICS_ERROR')

@chatbot_bp.route('/faq/<faq_id>/feedback', methods=['POST'])
@handle_api_errors
def record_faq_feedback(faq_id):
    """Record FAQ helpfulness feedback"""
    try:
        data = request.json
        helpful = data.get('helpful', True)
        
        faq_system.record_faq_usage(faq_id, helpful)
        
        return jsonify({
            "success": True,
            "message": "Feedback recorded successfully"
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to record FAQ feedback: {e}")
        return create_error_response("Failed to record FAQ feedback", 500, 'FAQ_FEEDBACK_ERROR')

@chatbot_bp.route('/faq', methods=['POST'])
@handle_api_errors
def create_faq_entry():
    """Create a new FAQ entry"""
    try:
        data = request.json or {}
        question = data.get('question', '').strip()
        answer = data.get('answer', '').strip()
        category = data.get('category', 'general')
        keywords = data.get('keywords', [])
        variations = data.get('variations', [])
        priority = data.get('priority', 1)

        if not question or not answer:
            return create_error_response("Question and answer are required", 400, 'MISSING_FIELDS')

        try:
            category_enum = FAQCategory(category)
        except ValueError:
            category_enum = FAQCategory.GENERAL

        if not isinstance(keywords, list):
            keywords = [keywords]
        if not isinstance(variations, list):
            variations = [variations]

        faq_id = faq_system.add_faq(
            question=question,
            answer=answer,
            category=category_enum,
            keywords=keywords,
            variations=variations,
            priority=priority
        )

        return jsonify({
            "success": True,
            "faq_id": faq_id,
            "message": "FAQ entry created successfully"
        })

    except Exception as e:
        logger.error(f"❌ Failed to create FAQ entry: {e}")
        return create_error_response("Failed to create FAQ entry", 500, 'FAQ_CREATE_ERROR')

# Knowledge Base Endpoints

@chatbot_bp.route('/knowledge/search', methods=['POST'])
def search_knowledge_base():
    """Search knowledge base with intelligent ranking"""
    try:
        data = request.json
        query = data.get('query', '')
        filters = data.get('filters', {})
        limit = data.get('limit', 10)
        
        if not query:
            return jsonify({"success": False, "error": "Query is required"}), 400
        
        # Search knowledge base
        response = knowledge_base.search(query, filters, limit)
        
        if response.success:
            return jsonify({
                "success": True,
                "query": response.query,
                "results": [
                    {
                        "document_id": result.document.id,
                        "title": result.document.title,
                        "summary": result.document.summary,
                        "content_preview": result.highlighted_content,
                        "relevance_score": result.relevance_score,
                        "document_type": result.document.document_type.value,
                        "category": result.document.category,
                        "tags": result.document.tags,
                        "match_explanation": result.match_explanation,
                        "matched_sections": result.matched_sections
                    } for result in response.results
                ],
                "total_results": response.total_results,
                "search_time": response.search_time,
                "suggestions": response.suggestions,
                "filters_applied": response.filters_applied
            })
        else:
            return jsonify({
                "success": False,
                "error": "Knowledge base search failed"
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Knowledge base search failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/knowledge/document/<doc_id>', methods=['GET'])
def get_knowledge_document(doc_id):
    """Get specific knowledge base document"""
    try:
        document = knowledge_base.get_document(doc_id)
        
        if not document:
            return jsonify({"success": False, "error": "Document not found"}), 404
        
        # Increment view count
        document.view_count += 1
        
        return jsonify({
            "success": True,
            "document": {
                "id": document.id,
                "title": document.title,
                "content": document.content,
                "summary": document.summary,
                "document_type": document.document_type.value,
                "format": document.format.value,
                "category": document.category,
                "tags": document.tags,
                "keywords": document.keywords,
                "author": document.author,
                "version": document.version,
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat(),
                "view_count": document.view_count,
                "helpful_votes": document.helpful_votes,
                "unhelpful_votes": document.unhelpful_votes
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get knowledge document: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/knowledge/documents', methods=['POST'])
def create_knowledge_document():
    """Add a new knowledge base document"""
    try:
        data = request.json or {}
        title = data.get('title', 'Untitled Document').strip()
        content = data.get('content', '').strip()
        summary = data.get('summary', content[:200])
        category = data.get('category', 'general')
        tags = data.get('tags', [])
        keywords = data.get('keywords', [])
        author = data.get('author', 'system')

        if not content:
            return jsonify({"success": False, "error": "Content cannot be empty"}), 400

        if not isinstance(tags, list):
            tags = [tags]
        if not isinstance(keywords, list):
            keywords = [keywords]

        doc_id = knowledge_base.add_document(
            title=title,
            content=content,
            summary=summary,
            document_type=DocumentType.ARTICLE,
            tags=tags,
            keywords=keywords,
            category=category,
            author=author
        )

        return jsonify({
            "success": True,
            "document_id": doc_id,
            "message": "Knowledge document added"
        })

    except Exception as e:
        logger.error(f"❌ Failed to add knowledge document: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/knowledge/categories', methods=['GET'])
def get_knowledge_categories():
    """Get all knowledge base categories"""
    try:
        categories = knowledge_base.get_categories()
        
        return jsonify({
            "success": True,
            "categories": categories
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get knowledge categories: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/knowledge/popular', methods=['GET'])
def get_popular_documents():
    """Get most popular knowledge base documents"""
    try:
        limit = request.args.get('limit', 10, type=int)
        documents = knowledge_base.get_popular_documents(limit)
        
        return jsonify({
            "success": True,
            "documents": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "summary": doc.summary,
                    "category": doc.category,
                    "view_count": doc.view_count,
                    "helpful_votes": doc.helpful_votes
                } for doc in documents
            ]
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get popular documents: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/knowledge/vectorize', methods=['POST'])
def vectorize_document_content():
    """Vectorize content for chatbot retrieval"""
    try:
        data = request.json or {}
        content = data.get('content', '').strip()
        metadata = data.get('metadata', {})

        if not content:
            return jsonify({"success": False, "error": "Content cannot be empty"}), 400

        if not isinstance(metadata, dict):
            metadata = {}

        doc_id = vector_search.add_document(content, metadata)

        return jsonify({
            "success": True,
            "vector_id": doc_id,
            "message": "Content vectorized successfully"
        })

    except Exception as e:
        logger.error(f"❌ Failed to vectorize content: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Context-Aware Conversation Endpoints

@chatbot_bp.route('/conversation/start', methods=['POST'])
def start_conversation():
    """Start a new conversation with context"""
    try:
        data = request.json
        user_id = data.get('user_id', 'anonymous')
        initial_message = data.get('message', '')
        session_id = data.get('session_id')
        channel = data.get('channel', 'web')
        user_context = data.get('user_context', {})
        
        if not initial_message:
            return jsonify({"success": False, "error": "Initial message is required"}), 400
        
        # Start conversation
        conversation = context_system.start_conversation(
            user_id, initial_message, session_id, channel, user_context
        )
        
        return jsonify({
            "success": True,
            "conversation_id": conversation.conversation_id,
            "user_id": conversation.user_id,
            "state": conversation.state.value,
            "created_at": conversation.created_at.isoformat(),
            "context_data": conversation.context_data
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to start conversation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/conversation/<conversation_id>/message', methods=['POST'])
def add_conversation_message(conversation_id):
    """Add message to existing conversation"""
    try:
        data = request.json
        content = data.get('content', '')
        message_type = data.get('message_type', 'user_question')
        metadata = data.get('metadata', {})
        
        if not content:
            return jsonify({"success": False, "error": "Message content is required"}), 400
        
        # Add message
        message = context_system.add_message(
            conversation_id, content, MessageType(message_type), metadata
        )
        
        return jsonify({
            "success": True,
            "message": {
                "id": message.id,
                "conversation_id": message.conversation_id,
                "message_type": message.message_type.value,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "metadata": message.metadata
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to add conversation message: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/conversation/<conversation_id>/respond', methods=['POST'])
def generate_contextual_response(conversation_id):
    """Generate context-aware response"""
    try:
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"success": False, "error": "User message is required"}), 400
        
        # Generate contextual response
        response = context_system.generate_contextual_response(conversation_id, user_message)
        
        return jsonify({
            "success": True,
            "response": response.response,
            "confidence": response.confidence,
            "context_used": response.context_used,
            "reasoning": response.reasoning,
            "suggested_actions": response.suggested_actions,
            "requires_escalation": response.requires_escalation,
            "follow_up_questions": response.follow_up_questions
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to generate contextual response: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get conversation details"""
    try:
        conversation = context_system.get_conversation(conversation_id)
        
        if not conversation:
            return jsonify({"success": False, "error": "Conversation not found"}), 404
        
        return jsonify({
            "success": True,
            "conversation": {
                "id": conversation.conversation_id,
                "user_id": conversation.user_id,
                "state": conversation.state.value,
                "messages": [
                    {
                        "id": msg.id,
                        "type": msg.message_type.value,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "metadata": msg.metadata
                    } for msg in conversation.messages
                ],
                "context_data": conversation.context_data,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "last_activity": conversation.last_activity.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get conversation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/conversation/<conversation_id>/close', methods=['POST'])
def close_conversation(conversation_id):
    """Close a conversation"""
    try:
        data = request.json
        reason = data.get('reason', 'completed')
        
        context_system.close_conversation(conversation_id, reason)
        
        return jsonify({
            "success": True,
            "message": "Conversation closed successfully"
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to close conversation: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Multi-Channel Support Endpoints

@chatbot_bp.route('/channels', methods=['GET'])
def get_supported_channels():
    """Get list of supported channels"""
    try:
        channels = multi_channel.get_supported_channels()
        
        return jsonify({
            "success": True,
            "channels": channels
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get supported channels: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/channels/<channel_type>/message', methods=['POST'])
def process_channel_message(channel_type):
    """Process message from specific channel"""
    try:
        # Validate channel type
        try:
            channel_enum = ChannelType(channel_type)
        except ValueError:
            return jsonify({"success": False, "error": f"Unsupported channel: {channel_type}"}), 400
        
        raw_message = request.json
        
        # Process message through multi-channel system
        response = multi_channel.process_message(channel_enum, raw_message)
        
        return jsonify({
            "success": True,
            "response": {
                "content": response.content,
                "format": response.format.value,
                "response_type": response.response_type.value,
                "confidence": response.confidence,
                "suggested_actions": response.suggested_actions,
                "metadata": response.metadata,
                "timestamp": response.timestamp.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to process channel message: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/channels/<channel_type>/test', methods=['POST'])
def test_channel(channel_type):
    """Test a specific channel"""
    try:
        # Validate channel type
        try:
            channel_enum = ChannelType(channel_type)
        except ValueError:
            return jsonify({"success": False, "error": f"Unsupported channel: {channel_type}"}), 400
        
        data = request.json
        test_message = data.get('test_message', 'Hello, this is a test message')
        
        # Test channel
        result = multi_channel.test_channel(channel_enum, test_message)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Failed to test channel: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/channels/statistics', methods=['GET'])
def get_channel_statistics():
    """Get channel usage statistics"""
    try:
        stats = multi_channel.get_channel_statistics()
        
        return jsonify({
            "success": True,
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get channel statistics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Unified Chat Endpoint

@chatbot_bp.route('/chat', methods=['POST'])
def unified_chat():
    """Unified chat endpoint that uses all AI systems"""
    try:
        data = request.json
        message = data.get('message', '')
        user_id = data.get('user_id', 'anonymous')
        session_id = data.get('session_id')
        conversation_id = data.get('conversation_id')
        channel = data.get('channel', 'web')
        
        if not message:
            return jsonify({"success": False, "error": "Message is required"}), 400
        
        # Prepare raw message for multi-channel processing
        raw_message = {
            'user_id': user_id,
            'message': message,
            'session_id': session_id,
            'conversation_id': conversation_id
        }
        
        # Process through multi-channel system (will use all AI systems)
        response = multi_channel.process_message(ChannelType.WEB_CHAT, raw_message)
        
        return jsonify({
            "success": True,
            "response": response.content,
            "confidence": response.confidence,
            "response_type": response.response_type.value,
            "suggested_actions": response.suggested_actions,
            "metadata": response.metadata,
            "timestamp": response.timestamp.isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Unified chat failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# System Status and Analytics

@chatbot_bp.route('/status', methods=['GET'])
def get_system_status():
    """Get chatbot system status"""
    try:
        faq_stats = faq_system.get_faq_statistics()
        kb_stats = knowledge_base.get_statistics()
        context_stats = context_system.get_conversation_statistics()
        channel_stats = multi_channel.get_channel_statistics()
        
        return jsonify({
            "success": True,
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "systems": {
                "smart_faq": {
                    "status": "operational",
                    "statistics": faq_stats
                },
                "knowledge_base": {
                    "status": "operational",
                    "statistics": kb_stats
                },
                "context_system": {
                    "status": "operational",
                    "statistics": context_stats
                },
                "multi_channel": {
                    "status": "operational",
                    "statistics": channel_stats
                }
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get system status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/analytics/comprehensive', methods=['GET'])
def get_comprehensive_analytics():
    """Get comprehensive chatbot analytics"""
    try:
        days = request.args.get('days', 30, type=int)
        
        # Collect analytics from all systems
        analytics = {
            "period": f"Last {days} days",
            "generated_at": datetime.now().isoformat(),
            "faq_system": faq_system.get_faq_statistics(),
            "knowledge_base": knowledge_base.get_statistics(),
            "conversations": context_system.get_conversation_statistics(),
            "channels": multi_channel.get_channel_statistics()
        }
        
        # Calculate overall metrics
        analytics["overall"] = {
            "total_interactions": (
                analytics["conversations"]["total_conversations"] +
                analytics["channels"]["total_messages"]
            ),
            "unique_users": max(
                analytics["conversations"]["active_users"],
                analytics["channels"]["total_unique_users"]
            ),
            "system_health": "excellent" if all([
                analytics["faq_system"].get("total_faqs", 0) > 0,
                analytics["knowledge_base"].get("total_documents", 0) > 0,
                analytics["channels"]["active_channels"] > 0
            ]) else "good"
        }
        
        return jsonify({
            "success": True,
            "analytics": analytics
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get comprehensive analytics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# Error handlers
@chatbot_bp.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404

@chatbot_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"success": False, "error": "Method not allowed"}), 405

@chatbot_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500
