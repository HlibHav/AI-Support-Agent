import os
import pickle
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict

# Try to import vector search dependencies
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False

class KnowledgeVectorStore:
    """
    Knowledge vector store with fallback to text-search mode.
    Supports both vector similarity search and text-based search.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.documents = []
        self.index = None
        self.encoder = None
        self.search_mode = None
        
        # Text-search components
        self.word_index = {}
        self.phrase_index = {}
        self.category_index = {}
        
        # Try to determine available search mode
        self._detect_search_mode()
    
    def _detect_search_mode(self):
        """Detect which search mode is available."""
        # Check for text-search mode
        if os.path.exists("knowledge_text_search.marker"):
            self.search_mode = "text_search"
            self.logger.info("Text-search mode detected")
            return
        
        # Check for vector search mode
        if (os.path.exists("knowledge_vector_index.faiss") and 
            os.path.exists("knowledge_documents.pkl") and
            VECTOR_SEARCH_AVAILABLE):
            self.search_mode = "vector_search"
            self.logger.info("Vector search mode detected")
            return
        
        # No search mode available
        self.search_mode = None
        self.logger.warning("No search mode available")
    
    def is_built(self) -> bool:
        """Check if knowledge base is built."""
        if self.search_mode == "text_search":
            return (os.path.exists("knowledge_documents.pkl") and 
                   os.path.exists("knowledge_word_index.json") and
                   os.path.exists("knowledge_phrase_index.json"))
        elif self.search_mode == "vector_search":
            return (os.path.exists("knowledge_vector_index.faiss") and 
                   os.path.exists("knowledge_documents.pkl"))
        return False
    
    def load_index(self) -> bool:
        """Load the appropriate search index."""
        if not self.is_built():
            return False
        
        try:
            # Load documents (common to both modes)
            with open("knowledge_documents.pkl", 'rb') as f:
                self.documents = pickle.load(f)
            
            if self.search_mode == "text_search":
                return self._load_text_search_index()
            elif self.search_mode == "vector_search":
                return self._load_vector_search_index()
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error loading index: {e}")
            return False
    
    def _load_text_search_index(self) -> bool:
        """Load text-search indices."""
        try:
            with open("knowledge_word_index.json", 'r', encoding='utf-8') as f:
                self.word_index = json.load(f)
            
            with open("knowledge_phrase_index.json", 'r', encoding='utf-8') as f:
                self.phrase_index = json.load(f)
            
            with open("knowledge_category_index.json", 'r', encoding='utf-8') as f:
                self.category_index = json.load(f)
            
            self.logger.info(f"Loaded text-search indices: {len(self.word_index)} keywords, {len(self.phrase_index)} phrases")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading text-search indices: {e}")
            return False
    
    def _load_vector_search_index(self) -> bool:
        """Load vector search index."""
        try:
            if not VECTOR_SEARCH_AVAILABLE:
                self.logger.error("Vector search dependencies not available")
                return False
            
            # Load FAISS index
            self.index = faiss.read_index("knowledge_vector_index.faiss")
            
            # Load sentence transformer
            self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
            self.encoder.eval()
            
            vector_count = getattr(self.index, 'ntotal', 0)
            self.logger.info(f"Loaded vector search index with {vector_count} vectors")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading vector search index: {e}")
            return False
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents."""
        if not self.documents:
            return []
        
        if self.search_mode == "text_search":
            return self._text_search(query, max_results)
        elif self.search_mode == "vector_search":
            return self._vector_search(query, max_results)
        else:
            # Fallback to basic text search
            return self._fallback_search(query, max_results)
    
    def _text_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Perform text-based search."""
        query_lower = query.lower()
        query_words = query_lower.split()
        
        # Score documents based on matches
        doc_scores = defaultdict(float)
        
        # Word-based scoring
        for word in query_words:
            if word in self.word_index:
                for doc_id in self.word_index[word]:
                    doc_scores[doc_id] += 1.0
        
        # Phrase-based scoring (higher weight)
        for phrase in self.phrase_index:
            if query_lower in phrase or phrase in query_lower:
                for doc_id in self.phrase_index[phrase]:
                    doc_scores[doc_id] += 2.0
        
        # Direct text search as fallback
        for doc in self.documents:
            doc_id = doc['id']
            if query_lower in doc.get('text_content', '').lower():
                doc_scores[doc_id] += 0.5
        
        # Sort by score and return top results
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in sorted_docs[:max_results]:
            doc = next((d for d in self.documents if d['id'] == doc_id), None)
            if doc:
                result = doc.copy()
                result['search_score'] = score
                result['search_type'] = 'text_search'
                results.append(result)
        
        return results
    
    def _vector_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        if not self.index or not self.encoder:
            return []
        
        try:
            # Create query embedding
            query_embedding = self.encoder.encode([query], convert_to_numpy=True)
            query_embedding = query_embedding.astype('float32')
            
            if VECTOR_SEARCH_AVAILABLE:
                faiss.normalize_L2(query_embedding)
                
                # Search - handle different FAISS API versions
                try:
                    scores, indices = self.index.search(query_embedding, max_results)
                except Exception:
                    # Fallback for different FAISS versions
                    distances = np.empty((1, max_results), dtype=np.float32)
                    labels = np.empty((1, max_results), dtype=np.int64)
                    self.index.search(query_embedding, max_results, distances, labels)
                    scores, indices = distances, labels
                
                results = []
                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                    if idx < len(self.documents):
                        doc = self.documents[idx].copy()
                        doc['search_score'] = float(score)
                        doc['search_type'] = 'vector_search'
                        results.append(doc)
                
                return results
            else:
                return []
            
        except Exception as e:
            self.logger.error(f"Error in vector search: {e}")
            return []
    
    def _fallback_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Fallback to basic text search in document content."""
        query_lower = query.lower()
        results = []
        
        for doc in self.documents:
            content = doc.get('text_content', '').lower()
            if query_lower in content:
                doc_copy = doc.copy()
                doc_copy['search_score'] = 1.0
                doc_copy['search_type'] = 'fallback_search'
                results.append(doc_copy)
        
        return results[:max_results]
    
    def get_categories(self) -> List[str]:
        """Get available categories."""
        if self.search_mode == "text_search" and self.category_index:
            return list(self.category_index.keys())
        elif self.documents:
            categories = set()
            for doc in self.documents:
                categories.add(doc.get('category', 'General'))
            return sorted(categories)
        return []
    
    def get_documents_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get documents by category."""
        if self.search_mode == "text_search" and category in self.category_index:
            doc_ids = self.category_index[category]
            return [doc for doc in self.documents if doc['id'] in doc_ids]
        else:
            return [doc for doc in self.documents if doc.get('category') == category]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        stats = {
            'search_mode': self.search_mode,
            'total_documents': len(self.documents),
            'available': self.is_built()
        }
        
        if self.documents:
            stats['total_words'] = sum(doc.get('word_count', 0) for doc in self.documents)
            stats['total_characters'] = sum(doc.get('char_count', 0) for doc in self.documents)
            stats['categories'] = self.get_categories()
        
        if self.search_mode == "text_search":
            stats['unique_keywords'] = len(self.word_index)
            stats['unique_phrases'] = len(self.phrase_index)
        elif self.search_mode == "vector_search" and self.index:
            vector_count = getattr(self.index, 'ntotal', 0)
            stats['vector_count'] = vector_count
        
        return stats
    
    def search_similar(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents (compatibility method).
        
        Args:
            query: Search query
            top_k: Number of results to return
            category: Optional category filter
            
        Returns:
            List of similar documents
        """
        results = self.search(query, max_results=top_k)
        
        # Filter by category if specified
        if category:
            results = [doc for doc in results if doc.get('category') == category]
        
        return results
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID."""
        for doc in self.documents:
            if doc['id'] == doc_id:
                return doc
        return None 