"""
Multi-language Support System for Fikiri Solutions
Advanced language detection and translation capabilities
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Optional dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    from core.minimal_config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_config = None

logger = logging.getLogger(__name__)

@dataclass
class LanguageResult:
    """Language detection result"""
    language: str
    confidence: float
    language_code: str
    is_supported: bool
    translation_available: bool

@dataclass
class TranslationResult:
    """Translation result"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: float
    success: bool

class MultiLanguageSupport:
    """Multi-language support with AI-powered translation"""
    
    def __init__(self):
        self.openai_client = None
        self._init_openai()
        
        # Supported languages with their codes
        self.supported_languages = {
            "english": {"code": "en", "name": "English", "priority": 1},
            "spanish": {"code": "es", "name": "Spanish", "priority": 2},
            "french": {"code": "fr", "name": "French", "priority": 3},
            "german": {"code": "de", "name": "German", "priority": 4},
            "italian": {"code": "it", "name": "Italian", "priority": 5},
            "portuguese": {"code": "pt", "name": "Portuguese", "priority": 6},
            "chinese": {"code": "zh", "name": "Chinese", "priority": 7},
            "japanese": {"code": "ja", "name": "Japanese", "priority": 8},
            "korean": {"code": "ko", "name": "Korean", "priority": 9},
            "arabic": {"code": "ar", "name": "Arabic", "priority": 10},
            "russian": {"code": "ru", "name": "Russian", "priority": 11},
            "dutch": {"code": "nl", "name": "Dutch", "priority": 12},
            "swedish": {"code": "sv", "name": "Swedish", "priority": 13},
            "norwegian": {"code": "no", "name": "Norwegian", "priority": 14},
            "danish": {"code": "da", "name": "Danish", "priority": 15}
        }
        
        # Language detection patterns for fallback
        self.language_patterns = {
            "spanish": ["hola", "gracias", "por favor", "buenos días", "adiós", "sí", "no"],
            "french": ["bonjour", "merci", "s'il vous plaît", "au revoir", "oui", "non"],
            "german": ["hallo", "danke", "bitte", "auf wiedersehen", "ja", "nein"],
            "italian": ["ciao", "grazie", "per favore", "arrivederci", "sì", "no"],
            "portuguese": ["olá", "obrigado", "por favor", "tchau", "sim", "não"],
            "chinese": ["你好", "谢谢", "请", "再见", "是", "不"],
            "japanese": ["こんにちは", "ありがとう", "お願い", "さようなら", "はい", "いいえ"],
            "korean": ["안녕하세요", "감사합니다", "부탁드립니다", "안녕히 가세요", "네", "아니요"],
            "arabic": ["مرحبا", "شكرا", "من فضلك", "وداعا", "نعم", "لا"],
            "russian": ["привет", "спасибо", "пожалуйста", "до свидания", "да", "нет"]
        }
        
        # Industry-specific terminology in different languages
        self.industry_terminology = {
            "landscaping": {
                "en": ["landscaping", "garden", "lawn", "tree", "plant", "maintenance"],
                "es": ["jardinería", "jardín", "césped", "árbol", "planta", "mantenimiento"],
                "fr": ["paysagisme", "jardin", "pelouse", "arbre", "plante", "entretien"],
                "de": ["landschaftsgestaltung", "garten", "rasen", "baum", "pflanze", "wartung"]
            },
            "real_estate": {
                "en": ["property", "house", "apartment", "sale", "rent", "price"],
                "es": ["propiedad", "casa", "apartamento", "venta", "alquiler", "precio"],
                "fr": ["propriété", "maison", "appartement", "vente", "location", "prix"],
                "de": ["eigentum", "haus", "wohnung", "verkauf", "miete", "preis"]
            },
            "healthcare": {
                "en": ["appointment", "doctor", "patient", "treatment", "health", "medical"],
                "es": ["cita", "doctor", "paciente", "tratamiento", "salud", "médico"],
                "fr": ["rendez-vous", "médecin", "patient", "traitement", "santé", "médical"],
                "de": ["termin", "arzt", "patient", "behandlung", "gesundheit", "medizinisch"]
            }
        }
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            config = get_config()
            api_key = getattr(config, 'openai_api_key', '')
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key)
                logger.info("✅ OpenAI client initialized for multi-language support")
            else:
                logger.warning("⚠️ OpenAI API key not configured for multi-language support")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI: {e}")
    
    def detect_language(self, text: str) -> LanguageResult:
        """Detect the language of the input text"""
        if not self.openai_client:
            return self._fallback_language_detection(text)
        
        try:
            prompt = f"""
            Detect the language of this text and provide the result in JSON format:
            
            Text: "{text}"
            
            Respond with:
            {{
                "language": "language_name",
                "language_code": "iso_code",
                "confidence": 0.0-1.0
            }}
            
            Use ISO 639-1 language codes (en, es, fr, de, it, pt, zh, ja, ko, ar, ru, nl, sv, no, da).
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.1
            )
            
            result_data = json.loads(response.choices[0].message.content)
            language_code = result_data.get("language_code", "en").lower()
            language_name = result_data.get("language", "english").lower()
            
            # Check if language is supported
            is_supported = language_code in [lang["code"] for lang in self.supported_languages.values()]
            
            return LanguageResult(
                language=language_name,
                confidence=result_data.get("confidence", 0.8),
                language_code=language_code,
                is_supported=is_supported,
                translation_available=is_supported
            )
            
        except Exception as e:
            logger.error(f"❌ AI language detection failed: {e}")
            return self._fallback_language_detection(text)
    
    def _fallback_language_detection(self, text: str) -> LanguageResult:
        """Fallback language detection without AI"""
        text_lower = text.lower()
        
        # Check against language patterns
        for language, patterns in self.language_patterns.items():
            pattern_count = sum(1 for pattern in patterns if pattern in text_lower)
            if pattern_count >= 2:  # At least 2 patterns match
                language_info = self.supported_languages.get(language, {"code": "en", "name": "English"})
                return LanguageResult(
                    language=language,
                    confidence=0.7,
                    language_code=language_info["code"],
                    is_supported=True,
                    translation_available=True
                )
        
        # Default to English
        return LanguageResult(
            language="english",
            confidence=0.6,
            language_code="en",
            is_supported=True,
            translation_available=True
        )
    
    def translate_text(self, text: str, target_language: str, source_language: str = None) -> TranslationResult:
        """Translate text to target language"""
        if not self.openai_client:
            return self._fallback_translation(text, target_language, source_language)
        
        try:
            # Detect source language if not provided
            if not source_language:
                lang_result = self.detect_language(text)
                source_language = lang_result.language_code
            
            # Get language names
            target_lang_name = self._get_language_name(target_language)
            source_lang_name = self._get_language_name(source_language)
            
            prompt = f"""
            Translate this text from {source_lang_name} to {target_lang_name}:
            
            Text: "{text}"
            
            Provide the translation in JSON format:
            {{
                "translated_text": "translated_text_here",
                "confidence": 0.0-1.0
            }}
            
            Maintain the original tone, formality, and context. For business communications, use professional language.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            result_data = json.loads(response.choices[0].message.content)
            
            return TranslationResult(
                original_text=text,
                translated_text=result_data.get("translated_text", text),
                source_language=source_language,
                target_language=target_language,
                confidence=result_data.get("confidence", 0.8),
                success=True
            )
            
        except Exception as e:
            logger.error(f"❌ AI translation failed: {e}")
            return self._fallback_translation(text, target_language, source_language)
    
    def _fallback_translation(self, text: str, target_language: str, source_language: str) -> TranslationResult:
        """Fallback translation without AI"""
        # Simple fallback - return original text with note
        return TranslationResult(
            original_text=text,
            translated_text=f"[Translation to {target_language} not available] {text}",
            source_language=source_language or "en",
            target_language=target_language,
            confidence=0.3,
            success=False
        )
    
    def _get_language_name(self, language_code: str) -> str:
        """Get language name from code"""
        for lang_name, lang_info in self.supported_languages.items():
            if lang_info["code"] == language_code:
                return lang_info["name"]
        return "English"
    
    def generate_multilingual_response(self, original_text: str, target_language: str, 
                                    industry: str = "general", context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate multilingual response with industry context"""
        try:
            # Detect source language
            lang_result = self.detect_language(original_text)
            
            # Translate to target language
            translation_result = self.translate_text(original_text, target_language, lang_result.language_code)
            
            # Generate industry-specific response in target language
            if self.openai_client:
                industry_terms = self.industry_terminology.get(industry, {}).get(target_language, [])
                
                prompt = f"""
                Generate a professional business response in {self._get_language_name(target_language)} for this {industry} inquiry:
                
                Original Text: "{original_text}"
                Translated Text: "{translation_result.translated_text}"
                Industry: {industry}
                Context: {json.dumps(context or {})}
                
                Create a professional response that:
                1. Acknowledges their inquiry
                2. Addresses their specific needs
                3. Uses appropriate {industry} terminology
                4. Maintains professional tone
                5. Includes next steps
                
                Respond in JSON format:
                {{
                    "response_subject": "subject_line",
                    "response_body": "response_content",
                    "suggested_actions": ["action1", "action2"]
                }}
                """
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=400,
                    temperature=0.7
                )
                
                result_data = json.loads(response.choices[0].message.content)
                
                return {
                    "success": True,
                    "source_language": lang_result.language_code,
                    "target_language": target_language,
                    "original_text": original_text,
                    "translated_text": translation_result.translated_text,
                    "response_subject": result_data.get("response_subject", ""),
                    "response_body": result_data.get("response_body", ""),
                    "suggested_actions": result_data.get("suggested_actions", []),
                    "confidence": translation_result.confidence
                }
            else:
                # Fallback response
                return {
                    "success": False,
                    "source_language": lang_result.language_code,
                    "target_language": target_language,
                    "original_text": original_text,
                    "translated_text": translation_result.translated_text,
                    "response_subject": f"Re: {original_text[:50]}...",
                    "response_body": f"Thank you for your inquiry. We will respond to you in {self._get_language_name(target_language)}.",
                    "suggested_actions": ["manual_review"],
                    "confidence": 0.3
                }
                
        except Exception as e:
            logger.error(f"❌ Multilingual response generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "source_language": "en",
                "target_language": target_language,
                "original_text": original_text
            }
    
    def get_supported_languages(self) -> List[Dict[str, Any]]:
        """Get list of supported languages"""
        return [
            {
                "code": lang_info["code"],
                "name": lang_info["name"],
                "priority": lang_info["priority"]
            }
            for lang_info in self.supported_languages.values()
        ]
    
    def get_language_statistics(self, texts: List[str]) -> Dict[str, Any]:
        """Get language distribution statistics"""
        if not texts:
            return {"error": "No texts provided"}
        
        try:
            language_counts = {}
            total_texts = len(texts)
            
            for text in texts:
                lang_result = self.detect_language(text)
                language = lang_result.language
                language_counts[language] = language_counts.get(language, 0) + 1
            
            # Calculate percentages
            language_percentages = {
                lang: (count / total_texts) * 100
                for lang, count in language_counts.items()
            }
            
            return {
                "total_texts": total_texts,
                "language_distribution": language_counts,
                "language_percentages": language_percentages,
                "most_common_language": max(language_counts, key=language_counts.get),
                "supported_languages_count": len([lang for lang in language_counts.keys() 
                                                if self.supported_languages.get(lang, {}).get("code")])
            }
            
        except Exception as e:
            logger.error(f"❌ Language statistics generation failed: {e}")
            return {"error": "Statistics generation failed"}
    
    def validate_translation_quality(self, original_text: str, translated_text: str, 
                                    source_language: str, target_language: str) -> Dict[str, Any]:
        """Validate translation quality"""
        if not self.openai_client:
            return {"quality_score": 0.5, "issues": ["AI validation not available"]}
        
        try:
            prompt = f"""
            Evaluate the quality of this translation from {source_language} to {target_language}:
            
            Original: "{original_text}"
            Translation: "{translated_text}"
            
            Rate the translation quality in JSON format:
            {{
                "quality_score": 0.0-1.0,
                "accuracy": 0.0-1.0,
                "fluency": 0.0-1.0,
                "cultural_appropriateness": 0.0-1.0,
                "issues": ["issue1", "issue2"],
                "suggestions": ["suggestion1", "suggestion2"]
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            result_data = json.loads(response.choices[0].message.content)
            
            return {
                "quality_score": result_data.get("quality_score", 0.5),
                "accuracy": result_data.get("accuracy", 0.5),
                "fluency": result_data.get("fluency", 0.5),
                "cultural_appropriateness": result_data.get("cultural_appropriateness", 0.5),
                "issues": result_data.get("issues", []),
                "suggestions": result_data.get("suggestions", [])
            }
            
        except Exception as e:
            logger.error(f"❌ Translation quality validation failed: {e}")
            return {"quality_score": 0.5, "issues": ["Validation failed"]}

# Global instance
multi_language_support = None

def get_multi_language_support() -> Optional[MultiLanguageSupport]:
    """Get the global multi-language support instance"""
    global multi_language_support
    
    if multi_language_support is None:
        multi_language_support = MultiLanguageSupport()
    
    return multi_language_support
