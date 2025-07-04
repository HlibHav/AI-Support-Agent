import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from .simple_ticket_agent import SimpleTicketAgent
from .knowledge_vector_store import KnowledgeVectorStore
from .translation_service import TranslationService

class EnhancedTicketAgent:
    def __init__(self, gemini_api_key: str, model_name: str = "models/gemini-1.5-flash"):
        """
        Initialize the enhanced ticket agent with both ticket and knowledge capabilities.
        
        Args:
            gemini_api_key: Google Gemini API key
            model_name: Gemini model name
        """
        self.gemini_api_key = gemini_api_key
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
        # Configure Gemini API
        genai.configure(api_key=gemini_api_key)  # type: ignore
        
        # Initialize Gemini model
        self.model = genai.GenerativeModel(model_name=model_name)  # type: ignore
        
        # Initialize both systems
        self.ticket_agent = SimpleTicketAgent("sample_tickets_template.csv", gemini_api_key)
        self.knowledge_store = KnowledgeVectorStore()
        self.translation_service = TranslationService(gemini_api_key)
        self.knowledge_ready = self.knowledge_store.is_built()
    
    def ensure_knowledge_ready(self):
        """Ensure knowledge base is ready, build if necessary."""
        if not self.knowledge_ready:
            try:
                self.logger.info("Attempting to load knowledge base...")
                if self.knowledge_store.load_index():
                    self.knowledge_ready = True
                    self.logger.info("Knowledge base loaded successfully")
                else:
                    self.logger.warning("Knowledge base not available - use build_text_search_knowledge.py to build it")
                    self.knowledge_ready = False
            except Exception as e:
                self.logger.error(f"Failed to load knowledge base: {e}")
                self.knowledge_ready = False
    
    def classify_query(self, query: str) -> str:
        """
        Classify whether a query is about tickets or general knowledge.
        
        Args:
            query: User query
            
        Returns:
            'ticket' or 'knowledge' or 'both'
        """
        # Keywords that indicate ticket queries
        ticket_keywords = [
            'ticket', 'issue', 'problem', 'bug', 'error', 'support', 'help',
            'id', 'status', 'priority', 'assignee', 'project', 'description',
            'closed', 'open', 'urgent', 'high', 'medium', 'low', 'new',
            'aventura', 'assigned', 'resolved', 'fix', 'duplicate'
        ]
        
        # Keywords that indicate knowledge queries
        knowledge_keywords = [
            'how to', 'what is', 'explain', 'guide', 'tutorial', 'manual',
            'documentation', 'help', 'instruction', 'process', 'procedure',
            'configure', 'setup', 'install', 'api', 'menu', 'settings',
            'pricing', 'contract', 'hotel', 'booking', 'gds', 'finance',
            'payment', 'website', 'marketing', 'quotas', 'catalog'
        ]
        
        query_lower = query.lower()
        
        # Count keyword matches
        ticket_matches = sum(1 for keyword in ticket_keywords if keyword in query_lower)
        knowledge_matches = sum(1 for keyword in knowledge_keywords if keyword in query_lower)
        
        # Determine query type
        if ticket_matches > knowledge_matches:
            return 'ticket'
        elif knowledge_matches > ticket_matches:
            return 'knowledge'
        else:
            # If equal or both zero, default to both
            return 'both'
    
    def get_ticket_context(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get relevant ticket context for a query.
        
        Args:
            query: User query
            limit: Maximum number of tickets to return
            
        Returns:
            List of relevant tickets
        """
        try:
            return self.ticket_agent.vector_store.search_similar_tickets(query, k=limit)
        except Exception as e:
            self.logger.error(f"Error getting ticket context: {str(e)}")
            return []
    
    def get_knowledge_context(self, query: str, limit: int = 3, user_language: str = 'en') -> List[Dict[str, Any]]:
        """
        Get relevant knowledge base context for a query with translation support.
        
        Args:
            query: User query
            limit: Maximum number of documents to return
            user_language: User's preferred language ('en' or 'ru')
            
        Returns:
            List of relevant knowledge documents
        """
        try:
            self.ensure_knowledge_ready()
            if not self.knowledge_ready:
                return []
            
            # Get search queries (original and translated)
            search_queries = self.translation_service.get_search_queries(query)
            
            # Search with the translated query for better results
            search_query = search_queries['translated']
            self.logger.info(f"Searching with query: '{search_query}' (translated from '{query}')")
            
            results = self.knowledge_store.search(search_query, max_results=limit)
            
            # Enhance results with translations if needed
            enhanced_results = self.translation_service.enhance_search_results(results, user_language)
            
            return enhanced_results
            
        except Exception as e:
            self.logger.error(f"Error getting knowledge context: {str(e)}")
            return []
    
    def generate_response(self, query: str, query_type: Optional[str] = None) -> str:
        """
        Generate a response based on the query and available context with multilingual support.
        
        Args:
            query: User query
            query_type: Type of query ('ticket', 'knowledge', 'both', or None for auto-detect)
            
        Returns:
            Generated response in the user's language
        """
        try:
            # Detect user language
            user_language = self.translation_service.detect_language(query)
            self.logger.info(f"Detected user language: {user_language}")
            
            # Classify query if not specified
            if query_type is None:
                query_type = self.classify_query(query)
            
            # Get relevant context
            ticket_context = []
            knowledge_context = []
            
            if query_type in ['ticket', 'both']:
                ticket_context = self.get_ticket_context(query)
            
            if query_type in ['knowledge', 'both']:
                knowledge_context = self.get_knowledge_context(query, user_language=user_language)
            
            # Build prompt with context
            prompt = self._build_prompt(query, ticket_context, knowledge_context, query_type, user_language)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            if hasattr(response, 'text') and response.text:
                return response.text
            else:
                return "I apologize, but I couldn't generate a response. Please try rephrasing your question."
                
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            return f"I encountered an error while processing your query: {str(e)}"
    
    def _build_prompt(self, query: str, ticket_context: List[Dict[str, Any]], 
                     knowledge_context: List[Dict[str, Any]], query_type: str, user_language: str = 'en') -> str:
        """
        Build the prompt for the AI model with relevant context and language support.
        
        Args:
            query: User query
            ticket_context: Relevant ticket context
            knowledge_context: Relevant knowledge context
            query_type: Type of query
            user_language: User's preferred language
            
        Returns:
            Formatted prompt
        """
        prompt_parts = []
        
        # System instructions
        prompt_parts.append("""You are a friendly and knowledgeable support specialist for the Goodwin travel booking system. You're here to help users with both specific ticket issues and general system questions.
        
        IMPORTANT PERSONALITY GUIDELINES:
        - Sound natural and conversational, like a helpful colleague
        - NEVER use robotic phrases like "The provided knowledge base documents describe", "Document 1 explains", "Document 2 details", etc.
        - Instead, speak directly: "Here's how to do that...", "I can help you with this...", "Let me walk you through this process..."
        - Be warm, professional, and genuinely helpful
        - Use natural transitions and explanations
        
        RESPONSE STYLE:
        - Start with acknowledgment: "I can help you with that!" or "Great question!"
        - Give detailed, step-by-step instructions when needed
        - Use bullet points or numbered lists for complex procedures
        - Include helpful tips and warnings where relevant
        - End with offers for additional help: "Let me know if you need any clarification on these steps!"
        
        TECHNICAL CONTEXT:
        - You have access to both ticket data and comprehensive documentation
        - The system handles hotel bookings, payments, GDS integration, and website management
        - Documentation may be in Russian or English - translate naturally when needed
        - GDS = Global Distribution System for travel bookings
        - Common menu paths: "Меню" (Menu), "Настройки" (Settings), "Заказы" (Orders), "Прайсер" (Pricing)
        """)
        
        # Add language-specific instructions
        language_instructions = self.translation_service.create_multilingual_prompt_instructions(user_language)
        prompt_parts.append(language_instructions)
        
        # Add ticket context if available
        if ticket_context:
            prompt_parts.append("\n=== RELATED TICKETS FROM YOUR SYSTEM ===")
            for i, ticket in enumerate(ticket_context, 1):
                score = ticket.get('similarity_score', 0)
                description = ticket.get('Description', 'N/A')
                
                prompt_parts.append(f"""
                TICKET #{ticket.get('ID', 'N/A')} - {ticket.get('Subject', 'N/A')}
                Status: {ticket.get('Status', 'N/A')} | Priority: {ticket.get('Priority', 'N/A')} | Project: {ticket.get('Project', 'N/A')}
                Details: {description[:500]}{'...' if len(description) > 500 else ''}
                """)
                
                # Add separator between tickets
                if i < len(ticket_context):
                    prompt_parts.append("---")
        
        # Add knowledge context if available
        if knowledge_context:
            prompt_parts.append("\n=== RELEVANT INFORMATION FROM YOUR SYSTEM ===")
            for i, doc in enumerate(knowledge_context, 1):
                # Get the correct score field name
                score = doc.get('search_score', doc.get('similarity_score', 0))
                content = doc.get('text_content', 'N/A')
                title = doc.get('title', 'N/A')
                category = doc.get('category', 'N/A')
                
                # Include English translation of title if available
                if 'title_en' in doc:
                    title_display = f"{title} ({doc['title_en']})"
                else:
                    title_display = title
                
                prompt_parts.append(f"""
                FROM: {title_display} ({category} section)
                CONTENT: {content[:1500]}{'...' if len(content) > 1500 else ''}
                """)
                
                # Add separator between documents
                if i < len(knowledge_context):
                    prompt_parts.append("---")
        
        # Add the user query
        prompt_parts.append(f"\n=== USER QUERY ===\n{query}")
        
        # Add response instructions
        if user_language == 'en':
            prompt_parts.append(f"""
            === YOUR RESPONSE TASK ===
            The user asked: "{query}"
            
            Based on the information above, provide a helpful, detailed response. Remember to:
            - Respond naturally in English, as if you're a knowledgeable colleague
            - Give step-by-step instructions where needed
            - Include helpful tips and context
            - Reference specific tickets by ID when relevant
            - Don't say "according to the document" - speak as if you know this personally
            - End with an offer to help further if needed
            """)
        else:
            prompt_parts.append(f"""
            === ВАША ЗАДАЧА ===
            Пользователь спросил: "{query}"
            
            На основе информации выше, дайте полезный, подробный ответ. Помните:
            - Отвечайте естественно на русском языке, как знающий коллега
            - Давайте пошаговые инструкции где необходимо
            - Включайте полезные советы и контекст
            - Упоминайте конкретные тикеты по ID если актуально
            - Не говорите "согласно документу" - говорите как будто знаете это лично
            - Завершите предложением дальнейшей помощи если нужно
            """)
        
        return "\n".join(prompt_parts)
    
    def search_tickets(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for tickets using the ticket vector store.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant tickets
        """
        return self.ticket_agent.vector_store.search_similar_tickets(query, k=limit)
    
    def search_knowledge(self, query: str, limit: int = 10, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for knowledge documents using the knowledge vector store.
        
        Args:
            query: Search query
            limit: Maximum number of results
            category: Optional category filter
            
        Returns:
            List of relevant knowledge documents
        """
        self.ensure_knowledge_ready()
        if not self.knowledge_ready:
            return []
        results = self.knowledge_store.search(query, max_results=limit)
        
        # Filter by category if specified
        if category:
            results = [doc for doc in results if doc.get('category') == category]
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about both ticket and knowledge systems.
        
        Returns:
            Dictionary with statistics
        """
        ticket_stats = self.ticket_agent.get_quick_stats()
        
        if self.knowledge_ready:
            knowledge_stats = self.knowledge_store.get_stats()
        else:
            knowledge_stats = {'total_documents': 0, 'status': 'not_ready'}
        
        return {
            'tickets': ticket_stats,
            'knowledge': knowledge_stats,
            'total_documents': ticket_stats.get('total_tickets', 0) + knowledge_stats.get('total_documents', 0)
        }
    
    def get_knowledge_categories(self) -> List[str]:
        """
        Get available knowledge categories.
        
        Returns:
            List of knowledge categories
        """
        if not self.knowledge_ready:
            return []
        return self.knowledge_store.get_categories()
    
    def rebuild_knowledge_index(self):
        """
        Rebuild the knowledge vector index.
        Note: Use build_text_search_knowledge.py to rebuild the knowledge base.
        """
        self.logger.warning("Knowledge index rebuilding is not supported in this version")
        self.logger.info("Use build_text_search_knowledge.py to rebuild the knowledge base")
    
    def is_ready(self) -> bool:
        """
        Check if both systems are ready.
        
        Returns:
            True if both ticket and knowledge systems are ready
        """
        return (self.ticket_agent.vector_store.is_built and 
                self.knowledge_ready) 