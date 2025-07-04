"""
Translation service for multilingual support in the ticket agent.
Translates English queries to Russian for better knowledge base search.
"""

import logging
from typing import Optional, Dict, Any
import re

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class TranslationService:
    """Service for translating queries and responses between English and Russian."""
    
    def __init__(self, gemini_api_key: str):
        self.logger = logging.getLogger(__name__)
        self.gemini_api_key = gemini_api_key
        
        if GEMINI_AVAILABLE:
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")
        else:
            self.model = None
            self.logger.warning("Google Gemini not available for translation")
    
    def detect_language(self, text: str) -> str:
        """
        Detect if text is primarily in English or Russian.
        
        Args:
            text: Text to analyze
            
        Returns:
            'en' for English, 'ru' for Russian, 'unknown' for unclear
        """
        if not text:
            return 'unknown'
        
        # Count Cyrillic characters
        cyrillic_count = len(re.findall(r'[а-яё]', text.lower()))
        # Count Latin characters
        latin_count = len(re.findall(r'[a-z]', text.lower()))
        
        total_chars = cyrillic_count + latin_count
        
        if total_chars == 0:
            return 'unknown'
        
        cyrillic_ratio = cyrillic_count / total_chars
        
        if cyrillic_ratio > 0.6:
            return 'ru'
        elif cyrillic_ratio < 0.3:
            return 'en'
        else:
            return 'unknown'
    
    def translate_to_russian(self, english_text: str) -> str:
        """
        Translate English text to Russian.
        
        Args:
            english_text: English text to translate
            
        Returns:
            Russian translation or original text if translation fails
        """
        if not english_text or not self.model:
            return english_text
        
        try:
            prompt = f"""
            Translate the following English text to Russian. Focus on technical terms related to:
            - Travel booking systems
            - Hotel management
            - GDS (Global Distribution System)
            - Payment processing
            - Website configuration
            
            Preserve technical terms when appropriate and provide accurate translations for:
            - "hotel matching" → "матчинг отелей" or "привязка отелей"
            - "payment issues" → "проблемы с оплатой"
            - "booking" → "бронирование"
            - "configuration" → "конфигурация" or "настройка"
            - "setup" → "настройка"
            
            English text: {english_text}
            
            Provide only the Russian translation, no additional text:
            """
            
            response = self.model.generate_content(prompt)
            
            if hasattr(response, 'text') and response.text:
                translated = response.text.strip()
                self.logger.info(f"Translated '{english_text}' to '{translated}'")
                return translated
            else:
                self.logger.warning(f"No translation received for: {english_text}")
                return english_text
                
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            return english_text
    
    def translate_to_english(self, russian_text: str) -> str:
        """
        Translate Russian text to English.
        
        Args:
            russian_text: Russian text to translate
            
        Returns:
            English translation or original text if translation fails
        """
        if not russian_text or not self.model:
            return russian_text
        
        try:
            prompt = f"""
            Translate the following Russian text to English. This is documentation for a travel booking system.
            Preserve technical terms and provide clear, professional translations.
            
            Russian text: {russian_text}
            
            Provide only the English translation, no additional text:
            """
            
            response = self.model.generate_content(prompt)
            
            if hasattr(response, 'text') and response.text:
                translated = response.text.strip()
                self.logger.info(f"Translated Russian text to English")
                return translated
            else:
                self.logger.warning("No translation received for Russian text")
                return russian_text
                
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            return russian_text
    
    def get_search_queries(self, original_query: str) -> Dict[str, str]:
        """
        Get both original and translated versions of a query for searching.
        
        Args:
            original_query: Original user query
            
        Returns:
            Dictionary with 'original', 'translated', and 'language' keys
        """
        language = self.detect_language(original_query)
        
        result = {
            'original': original_query,
            'translated': original_query,
            'language': language
        }
        
        if language == 'en':
            # Translate English to Russian for better search
            result['translated'] = self.translate_to_russian(original_query)
        elif language == 'ru':
            # Keep Russian as is, but could add English translation for broader search
            result['translated'] = original_query
        
        return result
    
    def format_multilingual_response(self, content: str, user_language: str) -> str:
        """
        Format response content based on user's language preference.
        
        Args:
            content: Response content (may contain mixed languages)
            user_language: User's preferred language ('en' or 'ru')
            
        Returns:
            Formatted response in the preferred language
        """
        if user_language == 'en' and self.detect_language(content) == 'ru':
            # Translate Russian content to English
            return self.translate_to_english(content)
        else:
            # Return as is for Russian users or already English content
            return content
    
    def create_multilingual_prompt_instructions(self, user_language: str) -> str:
        """
        Create language-specific instructions for the AI model.
        
        Args:
            user_language: User's preferred language
            
        Returns:
            Language-specific instructions
        """
        if user_language == 'en':
            return """
            LANGUAGE & COMMUNICATION STYLE:
            - The user asked in English, so respond naturally in English
            - When you reference Russian documentation, seamlessly translate the key information without saying "this document says" or "according to the document"
            - For Russian menu paths, naturally explain them: "Go to Menu → Orders" (not "Меню → Заказы means...")
            - Write as if you personally know the system: "To set this up, you'll need to..." instead of "The documentation indicates..."
            - Give detailed, step-by-step instructions with helpful context
            - Include tips and warnings based on your expertise: "Watch out for..." or "Pro tip:"
            """
        else:
            return """
            ЯЗЫК И СТИЛЬ ОБЩЕНИЯ:
            - Пользователь задал вопрос на русском языке, отвечайте естественно на русском
            - Говорите как знающий коллега, который лично знает систему
            - Давайте подробные пошаговые инструкции с полезными советами
            - Используйте личный стиль: "Чтобы настроить это, вам нужно..." вместо "Документация указывает..."
            - Включайте советы и предупреждения: "Обратите внимание..." или "Совет:"
            """
    
    def enhance_search_results(self, results: list, user_language: str) -> list:
        """
        Enhance search results with translations if needed.
        
        Args:
            results: Original search results
            user_language: User's preferred language
            
        Returns:
            Enhanced results with translations
        """
        if user_language != 'en':
            return results
        
        enhanced_results = []
        for result in results:
            enhanced_result = result.copy()
            
            # Add English translations of titles if they're in Russian
            title = result.get('title', '')
            if title and self.detect_language(title) == 'ru':
                enhanced_result['title_en'] = self.translate_to_english(title)
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results 