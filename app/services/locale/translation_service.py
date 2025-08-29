"""
Gemini-based translation service for automatically translating Russian text to English and Kazakh.

This service uses Google's Gemini AI to provide contextual translations for menu items,
categories, and modification types when admins input data in Russian.
"""
import os
import logging
import json
from typing import Dict, Optional, List

# Graceful handling of Gemini API imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)

class GeminiTranslationService:
    """Service for translating text using Google Gemini AI."""
    
    def __init__(self):
        """Initialize the Gemini translation service."""
        self.model = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini client if API key is available."""
        if not GEMINI_AVAILABLE:
            logger.warning("Google Generative AI library not installed. Translation service disabled.")
            self.model = None
            return
        
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini translation service initialized successfully")
            else:
                logger.warning("GEMINI_API_KEY not found. Translation service disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if translation service is available."""
        return self.model is not None
    
    def translate_text(self, text: str, target_language: str, source_language: str = "ru") -> Optional[str]:
        """
        Translate text from source language to target language using Gemini.
        
        Args:
            text: Text to translate
            target_language: Target language code (en, kk)
            source_language: Source language code (default: ru)
            
        Returns:
            Translated text or None if translation fails
        """
        if not self.model or not text or not text.strip():
            return None
        
        # Language mapping for better prompts
        language_names = {
            "ru": "Russian",
            "en": "English", 
            "kk": "Kazakh"
        }
        
        source_lang_name = language_names.get(source_language, source_language)
        target_lang_name = language_names.get(target_language, target_language)
        
        try:
            prompt = f"""
            Translate the following {source_lang_name} text to {target_lang_name}. 
            This is for a restaurant menu, so provide culturally appropriate translations that preserve the food item's meaning.
            Only return the translated text, nothing else.
            
            Text to translate: "{text}"
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip().strip('"').strip("'")
            
        except Exception as e:
            logger.error(f"Gemini translation failed for text '{text[:50]}...' to {target_language}: {e}")
            return None
    
    def translate_to_multiple_languages(
        self, 
        text: str, 
        target_languages: List[str] = ["en", "kk"], 
        source_language: str = "ru"
    ) -> Dict[str, str]:
        """
        Translate text to multiple target languages using Gemini.
        
        Args:
            text: Text to translate
            target_languages: List of target language codes
            source_language: Source language code
            
        Returns:
            Dictionary with language codes as keys and translations as values
        """
        if not self.model or not text or not text.strip():
            return {}
        
        # Language mapping for better prompts
        language_names = {
            "ru": "Russian",
            "en": "English", 
            "kk": "Kazakh"
        }
        
        source_lang_name = language_names.get(source_language, source_language)
        target_lang_names = [language_names.get(lang, lang) for lang in target_languages]
        
        try:
            prompt = f"""
            Translate the following {source_lang_name} restaurant menu text to {', '.join(target_lang_names)}.
            Provide culturally appropriate translations that preserve the food item's meaning.
            Return the result as a JSON object with language codes as keys.
            
            Example format: {{"en": "English translation", "kk": "Kazakh translation"}}
            
            Text to translate: "{text}"
            """
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Try to parse JSON response
            try:
                translations = json.loads(result_text)
                # Filter to only requested languages
                return {lang: translations.get(lang, '') for lang in target_languages if lang in translations}
            except json.JSONDecodeError:
                # Fallback to individual translations if JSON parsing fails
                logger.warning(f"Failed to parse JSON response from Gemini, falling back to individual translations")
                translations = {}
                for lang in target_languages:
                    if lang != source_language:
                        translated = self.translate_text(text, lang, source_language)
                        if translated:
                            translations[lang] = translated
                return translations
            
        except Exception as e:
            logger.error(f"Gemini batch translation failed for text '{text[:50]}...': {e}")
            return {}
    
    def auto_populate_translations(
        self, 
        russian_text: str, 
        existing_translations: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Auto-populate translation fields for Russian input using Gemini.
        
        This function creates translations for English and Kazakh from Russian input,
        while preserving any existing translations.
        
        Args:
            russian_text: Russian text to translate
            existing_translations: Existing translation dictionary to preserve
            
        Returns:
            Complete translation dictionary with ru, en, and kk keys
        """
        # Start with existing translations or empty dict
        # Handle Mock objects in tests by ensuring we always work with a real dict
        translations = {}
        if existing_translations and isinstance(existing_translations, dict):
            try:
                translations = existing_translations.copy()
            except (TypeError, AttributeError):
                # If copy fails, start with empty dict
                translations = {}
        # For Mock objects or non-dict objects, just start with empty dict
        
        # Always set Russian as the source
        if russian_text and russian_text.strip():
            translations["ru"] = russian_text.strip()
        
        # Generate missing translations using Gemini
        if self.is_available() and russian_text:
            # Find which translations are missing
            needed_languages = [lang for lang in ["en", "kk"] if lang not in translations]
            
            if needed_languages:
                auto_translations = self.translate_to_multiple_languages(
                    russian_text, 
                    target_languages=needed_languages, 
                    source_language="ru"
                )
                
                # Add the new translations
                for lang, translated_text in auto_translations.items():
                    if translated_text:
                        translations[lang] = translated_text
        
        return translations

# Global translation service instance
gemini_translation_service = GeminiTranslationService()

def get_translation_service() -> GeminiTranslationService:
    """Get the global Gemini translation service instance."""
    return gemini_translation_service