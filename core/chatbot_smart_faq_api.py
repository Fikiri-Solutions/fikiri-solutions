"""
Chatbot/Smart FAQ API Integration for Fikiri Solutions
Unified API for chatbot, FAQ, knowledge base, and multi-channel support
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from core.smart_faq_system import get_smart_faq, FAQCategory
from core.knowledge_base_system import get_knowledge_base, DocumentType
from core.context_aware_responses import get_context_system, MessageType
from core.multi_channel_support import get_multi_channel_system, ChannelType
from core.minimal_vector_search import MinimalVectorSearch, get_vector_search as _get_vector_search
from core.api_validation import handle_api_errors, create_error_response
from core.public_chatbot_api import require_api_key
from core.chatbot_auth import require_api_key_or_jwt
from core.database_optimization import db_optimizer
from core.secure_sessions import get_current_user_id

logger = logging.getLogger(__name__)

# Create Blueprint
chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/chatbot')

# Initialize systems (lighter loads first)
faq_system = get_smart_faq()
knowledge_base = get_knowledge_base()
context_system = get_context_system()
multi_channel = get_multi_channel_system()

# Lazy-load vector search via singleton in minimal_vector_search (shared with KB layer)
def get_vector_search() -> MinimalVectorSearch:
    """Return shared vector search singleton. Prefer app.services if set; else use minimal_vector_search.get_vector_search()."""
    try:
        import sys
        if 'app' in sys.modules:
            from app import services
            if 'vector_search' in services and services['vector_search'] is not None:
                return services['vector_search']
    except (ImportError, AttributeError, KeyError):
        pass
    vs = _get_vector_search()
    try:
        import sys
        if 'app' in sys.modules:
            from app import services
            services['vector_search'] = vs
    except (ImportError, AttributeError):
        pass
    return vs

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

        # Persist FAQ to vector index for semantic search
        try:
            # Combine question and answer for better searchability
            faq_content = f"Question: {question}\nAnswer: {answer}"
            if keywords:
                faq_content += f"\nKeywords: {', '.join(keywords)}"
            
            vector_id = get_vector_search().add_document(
                text=faq_content,
                metadata={
                    "type": "faq",
                    "faq_id": faq_id,
                    "question": question,
                    "category": category,
                    "priority": priority
                }
            )
            logger.info(f"✅ FAQ {faq_id} persisted to vector index: {vector_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to persist FAQ to vector index: {e}")
            # Don't fail the request if vectorization fails

        return jsonify({
            "success": True,
            "faq_id": faq_id,
            "vector_id": vector_id if 'vector_id' in locals() else None,
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
        
        # Extract tenant_id for multi-tenant isolation
        tenant_id = None
        try:
            from flask import g
            if hasattr(g, 'api_key_info') and g.api_key_info:
                tenant_id = g.api_key_info.get('tenant_id')
            elif hasattr(g, 'user_id') and g.user_id:
                # For session-based auth, use user_id as tenant_id
                tenant_id = str(g.user_id)
        except Exception:
            pass
        
        # Ensure tenant_id is in filters for multi-tenant isolation
        if tenant_id and 'tenant_id' not in filters:
            filters['tenant_id'] = tenant_id
        
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

        # Extract tenant_id and user_id for multi-tenant isolation
        tenant_id = None
        user_id = None
        
        # Try API key auth first (for public API)
        try:
            from flask import g
            if hasattr(g, 'api_key_info') and g.api_key_info:
                tenant_id = g.api_key_info.get('tenant_id')
                user_id = g.api_key_info.get('user_id')
        except Exception:
            pass
        
        # Fallback to session auth (for authenticated users)
        if not tenant_id and not user_id:
            try:
                from flask import g
                from core.secure_sessions import get_current_user_id
                user_id = get_current_user_id()
                # For session-based auth, tenant_id might be same as user_id or derived from user
                # For now, use user_id as tenant_id if no explicit tenant_id exists
                if user_id:
                    tenant_id = str(user_id)  # Use user_id as tenant_id for single-tenant users
            except Exception:
                pass

        # Build metadata with tenant isolation
        kb_metadata = {}
        if tenant_id:
            kb_metadata['tenant_id'] = tenant_id
        if user_id:
            kb_metadata['user_id'] = user_id

        doc_id = knowledge_base.add_document(
            title=title,
            content=content,
            summary=summary,
            document_type=DocumentType.ARTICLE,
            tags=tags,
            keywords=keywords,
            category=category,
            author=author,
            metadata=kb_metadata
        )

        # Persist document to vector index for semantic search; store vector_id for future sync on update/delete
        vector_id = None
        try:
            doc_content = f"Title: {title}\n{content}"
            if summary:
                doc_content = f"{summary}\n\n{doc_content}"
            
            # Include tenant_id in vector metadata for multi-tenant isolation
            vector_metadata = {
                "type": "knowledge_base",
                "document_id": doc_id,
                "title": title,
                "category": category,
                "tags": tags,
                "author": author
            }
            if tenant_id:
                vector_metadata['tenant_id'] = tenant_id
            if user_id:
                vector_metadata['user_id'] = user_id
            
            vs = get_vector_search()
            if getattr(vs, "use_pinecone", False):
                ok = vs.upsert_document(doc_id, doc_content, vector_metadata)
                vector_id = doc_id if ok else None
            else:
                vector_id = vs.add_document(text=doc_content, metadata=vector_metadata)
                vector_id = vector_id if (vector_id is not None and vector_id >= 0) else None
            logger.info(f"✅ Knowledge document {doc_id} persisted to vector index: {vector_id}")
            # Store vector_id in KB document metadata so update/delete can sync to vector index (see docs/CRUD_RAG_ARCHITECTURE.md)
            doc = knowledge_base.get_document(doc_id)
            if doc is not None and vector_id is not None:
                new_meta = dict(doc.metadata) if getattr(doc, "metadata", None) else {}
                new_meta["vector_id"] = vector_id
                knowledge_base.update_document(doc_id, {"metadata": new_meta})
        except Exception as e:
            logger.warning(f"⚠️ Failed to persist document to vector index: {e}")

        return jsonify({
            "success": True,
            "document_id": doc_id,
            "vector_id": vector_id,
            "message": "Knowledge document added"
        })

    except Exception as e:
        logger.error(f"❌ Failed to add knowledge document: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@chatbot_bp.route('/knowledge/import', methods=['POST'])
@handle_api_errors
@require_api_key_or_jwt
def import_knowledge_document():
    """Import a knowledge document or FAQ using API key context (tenant-scoped)."""
    try:
        data = request.json or {}
        title = (data.get('title') or '').strip()
        content = (data.get('content') or '').strip()
        question = (data.get('question') or '').strip()
        answer = (data.get('answer') or '').strip()
        category = (data.get('category') or 'general')
        document_type = data.get('document_type', DocumentType.FAQ.value)
        tags = data.get('tags') or []
        keywords = data.get('keywords') or []

        if not content and not (question and answer):
            return create_error_response("Provide content or question/answer", 400, 'MISSING_CONTENT')

        if question and answer:
            title = title or question
            content = f"Question: {question}\nAnswer: {answer}"
            if keywords:
                content += f"\nKeywords: {', '.join(keywords)}"

        try:
            document_type_enum = DocumentType(document_type)
        except ValueError:
            document_type_enum = DocumentType.FAQ

        if not isinstance(tags, list):
            tags = [tags]
        if not isinstance(keywords, list):
            keywords = [keywords]

        tenant_id = None
        user_id = None
        if hasattr(g, 'api_key_info') and g.api_key_info:
            tenant_id = g.api_key_info.get('tenant_id')
            user_id = g.api_key_info.get('user_id')

        kb_metadata: Dict[str, Any] = {}
        if tenant_id:
            kb_metadata['tenant_id'] = tenant_id
        if user_id:
            kb_metadata['user_id'] = user_id

        doc_id = knowledge_base.add_document(
            title=title or "Imported Knowledge",
            content=content,
            summary=(content or "")[:500] or "Imported",
            document_type=document_type_enum,
            category=category,
            tags=tags,
            keywords=keywords,
            author="import",
            metadata=kb_metadata
        )

        vector_id = None
        try:
            vs = get_vector_search()
            if getattr(vs, "use_pinecone", False):
                ok = vs.upsert_document(doc_id, content, {
                    "type": "knowledge_base",
                    "document_id": doc_id,
                    "title": title or "Imported Knowledge",
                    "category": category,
                    "tenant_id": tenant_id,
                    "user_id": user_id
                })
                vector_id = doc_id if ok else None
            else:
                vector_id = vs.add_document(
                    text=content,
                    metadata={
                        "type": "knowledge_base",
                        "document_id": doc_id,
                        "title": title or "Imported Knowledge",
                        "category": category,
                        "tenant_id": tenant_id,
                        "user_id": user_id
                    }
                )
                vector_id = vector_id if (vector_id is not None and vector_id >= 0) else None
            if vector_id is not None:
                doc = knowledge_base.get_document(doc_id)
                if doc:
                    new_meta = dict(doc.metadata or {})
                    new_meta["vector_id"] = vector_id
                    knowledge_base.update_document(doc_id, {"metadata": new_meta})
        except Exception as e:
            logger.warning("⚠️ Failed to persist imported knowledge to vector index: %s", e)

        return jsonify({
            "success": True,
            "document_id": doc_id,
            "vector_id": vector_id,
            "message": "Knowledge imported successfully"
        })
    except Exception as e:
        logger.error(f"❌ Failed to import knowledge: {e}")
        return create_error_response("Failed to import knowledge document", 500, 'KNOWLEDGE_IMPORT_ERROR')


@chatbot_bp.route('/knowledge/import/bulk', methods=['POST'])
@handle_api_errors
@require_api_key_or_jwt
def import_knowledge_bulk():
    """Import multiple knowledge documents in one request. Body: { "documents": [ { title?, content? | question?, answer?, category?, document_type?, tags?, keywords? }, ... ] }."""
    try:
        data = request.json or {}
        documents = data.get('documents')
        if not documents or not isinstance(documents, list):
            return create_error_response("documents array is required", 400, 'MISSING_DOCUMENTS')

        results = []
        for i, item in enumerate(documents):
            if not isinstance(item, dict):
                results.append({"index": i, "success": False, "error": "Each item must be an object"})
                continue
            title = (item.get('title') or '').strip()
            content = (item.get('content') or '').strip()
            question = (item.get('question') or '').strip()
            answer = (item.get('answer') or '').strip()
            category = (item.get('category') or 'general')
            document_type = item.get('document_type', DocumentType.FAQ.value)
            tags = item.get('tags') or []
            keywords = item.get('keywords') or []

            if not content and not (question and answer):
                results.append({"index": i, "success": False, "error": "Provide content or question/answer"})
                continue

            if question and answer:
                title = title or question
                content = f"Question: {question}\nAnswer: {answer}"
                if keywords:
                    content += f"\nKeywords: {', '.join(keywords)}"

            try:
                document_type_enum = DocumentType(document_type)
            except ValueError:
                document_type_enum = DocumentType.FAQ
            if not isinstance(tags, list):
                tags = [tags]
            if not isinstance(keywords, list):
                keywords = [keywords]

            tenant_id = None
            user_id = None
            if hasattr(g, 'api_key_info') and g.api_key_info:
                tenant_id = g.api_key_info.get('tenant_id')
                user_id = g.api_key_info.get('user_id')
            kb_metadata: Dict[str, Any] = {}
            if tenant_id:
                kb_metadata['tenant_id'] = tenant_id
            if user_id:
                kb_metadata['user_id'] = user_id

            try:
                doc_id = knowledge_base.add_document(
                    title=title or "Imported Knowledge",
                    content=content,
                    summary=(content or "")[:500] or "Imported",
                    document_type=document_type_enum,
                    category=category,
                    tags=tags,
                    keywords=keywords,
                    author="import",
                    metadata=kb_metadata
                )
                vector_id = None
                try:
                    vs = get_vector_search()
                    if getattr(vs, "use_pinecone", False):
                        ok = vs.upsert_document(doc_id, content, {
                            "type": "knowledge_base",
                            "document_id": doc_id,
                            "title": title or "Imported Knowledge",
                            "category": category,
                            "tenant_id": tenant_id,
                            "user_id": user_id
                        })
                        vector_id = doc_id if ok else None
                    else:
                        vector_id = get_vector_search().add_document(
                            text=content,
                            metadata={
                                "type": "knowledge_base",
                                "document_id": doc_id,
                                "title": title or "Imported Knowledge",
                                "category": category,
                                "tenant_id": tenant_id,
                                "user_id": user_id
                            }
                        )
                        vector_id = vector_id if (vector_id is not None and vector_id >= 0) else None
                    if vector_id is not None:
                        doc = knowledge_base.get_document(doc_id)
                        if doc:
                            new_meta = dict(doc.metadata or {})
                            new_meta["vector_id"] = vector_id
                            knowledge_base.update_document(doc_id, {"metadata": new_meta})
                except Exception as e:
                    logger.warning("⚠️ Bulk import: vector index failed for doc %s: %s", doc_id, e)
                results.append({"index": i, "success": True, "document_id": doc_id, "vector_id": vector_id})
            except Exception as e:
                logger.warning("Bulk import item %s failed: %s", i, e)
                results.append({"index": i, "success": False, "error": str(e)})

        success_count = sum(1 for r in results if r.get("success"))
        return jsonify({
            "success": True,
            "imported": success_count,
            "total": len(documents),
            "results": results
        })
    except Exception as e:
        logger.exception("Bulk import failed")
        return create_error_response("Bulk import failed", 500, 'BULK_IMPORT_ERROR')


@chatbot_bp.route('/knowledge/revectorize', methods=['POST'])
@handle_api_errors
@require_api_key_or_jwt
def revectorize_knowledge():
    """Re-index all KB documents into the vector store (e.g. after Pinecone dimension change). Tenant-scoped."""
    try:
        tenant_id = None
        user_id = None
        if hasattr(g, 'api_key_info') and g.api_key_info:
            tenant_id = g.api_key_info.get('tenant_id')
            user_id = g.api_key_info.get('user_id')
        docs = knowledge_base.list_documents(tenant_id)
        vs = get_vector_search()
        results = []
        for doc in docs:
            text = (doc.content or "").strip()
            if not text:
                results.append({"document_id": doc.id, "success": False, "error": "Empty content"})
                continue
            meta = dict(doc.metadata or {})
            vector_meta = {
                "type": "knowledge_base",
                "document_id": doc.id,
                "title": doc.title,
                "category": doc.category,
                "tenant_id": tenant_id,
                "user_id": user_id,
                **{k: v for k, v in meta.items() if k in ("tenant_id", "user_id")}
            }
            ok = vs.upsert_document(doc.id, text, vector_meta)
            if ok:
                new_meta = dict(doc.metadata or {})
                new_meta["vector_id"] = doc.id
                knowledge_base.update_document(doc.id, {"metadata": new_meta})
            results.append({"document_id": doc.id, "success": ok})
        revectorized = sum(1 for r in results if r.get("success"))
        return jsonify({
            "success": True,
            "revectorized": revectorized,
            "total": len(docs),
            "results": results
        })
    except Exception as e:
        logger.exception("Revectorize failed")
        return create_error_response("Revectorize failed", 500, 'REVECTORIZE_ERROR')


CHATBOT_FEEDBACK_RATINGS = frozenset({'correct', 'somewhat_correct', 'somewhat_incorrect', 'incorrect'})


@chatbot_bp.route('/feedback', methods=['POST'])
@handle_api_errors
def submit_chatbot_feedback():
    """
    Submit feedback for a chatbot answer.
    Body: { question, answer, retrieved_doc_ids, rating, metadata?, session_id?, prompt_version?, retriever_version? }
    rating must be one of: correct, somewhat_correct, somewhat_incorrect, incorrect.
    user_id is set from session when authenticated.
    """
    try:
        data = request.json or {}
        question = (data.get('question') or '').strip()
        answer = (data.get('answer') or '').strip()
        retrieved_doc_ids = data.get('retrieved_doc_ids')
        rating = (data.get('rating') or '').strip().lower()
        session_id = (data.get('session_id') or '').strip() or None
        metadata = data.get('metadata')
        prompt_version = (data.get('prompt_version') or '').strip() or None
        retriever_version = (data.get('retriever_version') or '').strip() or None

        if not question:
            return create_error_response("question is required", 400, 'MISSING_QUESTION')
        if not answer:
            return create_error_response("answer is required", 400, 'MISSING_ANSWER')
        if rating not in CHATBOT_FEEDBACK_RATINGS:
            return create_error_response(
                "rating must be one of: correct, somewhat_correct, somewhat_incorrect, incorrect",
                400,
                'INVALID_RATING'
            )

        if retrieved_doc_ids is not None and not isinstance(retrieved_doc_ids, list):
            return create_error_response("retrieved_doc_ids must be an array", 400, 'INVALID_RETRIEVED_DOC_IDS')
        if metadata is not None and not isinstance(metadata, dict):
            return create_error_response("metadata must be an object", 400, 'INVALID_METADATA')

        user_id = get_current_user_id()

        retrieved_json = json.dumps(retrieved_doc_ids if isinstance(retrieved_doc_ids, list) else [])
        metadata_json = json.dumps(metadata) if isinstance(metadata, dict) else None

        if not db_optimizer.table_exists("chatbot_feedback"):
            return create_error_response("Chatbot feedback table not available", 503, 'SERVICE_UNAVAILABLE')

        db_optimizer.execute_query(
            """INSERT INTO chatbot_feedback
               (user_id, session_id, question, answer, retrieved_doc_ids, rating, metadata, prompt_version, retriever_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, session_id, question, answer, retrieved_json, rating, metadata_json, prompt_version, retriever_version),
            fetch=False,
        )
        return jsonify({"success": True, "message": "Feedback recorded"})
    except Exception as e:
        logger.exception("Chatbot feedback failed")
        return create_error_response("Failed to record feedback", 500, 'FEEDBACK_ERROR')


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

        doc_id = get_vector_search().add_document(text=content, metadata=metadata)

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
