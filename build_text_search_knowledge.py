#!/usr/bin/env python3
"""
Text-only knowledge base builder - no ML models required.
Uses simple text indexing for fast search without memory-intensive embeddings.
"""

import os
import sys
import logging
import pickle
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Any, Set, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('text_knowledge_build.log')
        ]
    )

class TextKnowledgeBuilder:
    """Build a text-searchable knowledge base without ML dependencies."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.documents = []
        self.word_index = defaultdict(set)  # word -> set of document IDs
        self.phrase_index = defaultdict(set)  # phrase -> set of document IDs
        self.category_index = defaultdict(list)  # category -> list of documents
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text for indexing."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-\(\)]', ' ', text)
        return text.strip()
    
    def extract_keywords(self, text: str) -> Set[str]:
        """Extract keywords from text."""
        # Convert to lowercase and split
        words = text.lower().split()
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
            'his', 'her', 'its', 'our', 'their'
        }
        
        # Extract meaningful words (length > 2, not stop words)
        keywords = set()
        for word in words:
            cleaned_word = re.sub(r'[^\w]', '', word)
            if len(cleaned_word) > 2 and cleaned_word not in stop_words:
                keywords.add(cleaned_word)
        
        return keywords
    
    def extract_phrases(self, text: str) -> Set[str]:
        """Extract meaningful phrases from text."""
        sentences = re.split(r'[.!?]+', text)
        phrases = set()
        
        for sentence in sentences:
            sentence = sentence.strip().lower()
            if len(sentence) > 10:  # Meaningful phrases
                # Split into phrases of 2-4 words
                words = sentence.split()
                for i in range(len(words)):
                    for j in range(2, min(5, len(words) - i + 1)):
                        phrase = ' '.join(words[i:i+j])
                        if len(phrase) > 10:  # Skip very short phrases
                            phrases.add(phrase)
        
        return phrases
    
    def process_document(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Process a single document and extract searchable content."""
        try:
            from src.document_processor import DocumentProcessor
            doc_processor = DocumentProcessor()
            
            # Extract text content
            text_content = doc_processor.extract_text_from_docx(file_path)
            if not text_content.strip():
                return None
            
            # Get metadata
            metadata = doc_processor.get_document_metadata(file_path)
            
            # Clean text
            cleaned_text = self.clean_text(text_content)
            
            # Create document
            doc_id = f"doc_{len(self.documents) + 1}"
            document = {
                'id': doc_id,
                'text_content': text_content,
                'cleaned_text': cleaned_text,
                'title': file_path.stem,
                'char_count': len(text_content),
                'word_count': len(text_content.split()),
                **metadata
            }
            
            # Extract keywords and phrases for indexing
            keywords = self.extract_keywords(cleaned_text)
            phrases = self.extract_phrases(cleaned_text)
            
            # Add to indices
            for keyword in keywords:
                self.word_index[keyword].add(doc_id)
            
            for phrase in phrases:
                self.phrase_index[phrase].add(doc_id)
            
            # Add to category index
            category = metadata.get('category', 'General')
            self.category_index[category].append(doc_id)
            
            self.logger.info(f"Processed {file_path.name}: {len(keywords)} keywords, {len(phrases)} phrases")
            return document
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return None
    
    def build_knowledge_base(self) -> bool:
        """Build the text-searchable knowledge base."""
        try:
            self.logger.info("Building text-searchable knowledge base...")
            
            # Get document files
            docx_files = list(Path("Knowledge").rglob("*.docx"))
            docx_files = [f for f in docx_files if not f.name.startswith('~$')]
            
            if not docx_files:
                self.logger.error("No documents found in Knowledge directory")
                return False
            
            self.logger.info(f"Processing {len(docx_files)} documents...")
            
            for i, file_path in enumerate(docx_files):
                self.logger.info(f"Processing {i+1}/{len(docx_files)}: {file_path.name}")
                
                document = self.process_document(file_path)
                if document:
                    self.documents.append(document)
            
            if not self.documents:
                self.logger.error("No documents were processed successfully")
                return False
            
            # Convert sets to lists for JSON serialization
            word_index_serializable = {word: list(doc_ids) for word, doc_ids in self.word_index.items()}
            phrase_index_serializable = {phrase: list(doc_ids) for phrase, doc_ids in self.phrase_index.items()}
            
            # Save all components
            self.logger.info("Saving knowledge base components...")
            
            # Save documents
            with open("knowledge_documents.pkl", 'wb') as f:
                pickle.dump(self.documents, f)
            
            # Save text indices
            with open("knowledge_word_index.json", 'w', encoding='utf-8') as f:
                json.dump(word_index_serializable, f, ensure_ascii=False, indent=2)
            
            with open("knowledge_phrase_index.json", 'w', encoding='utf-8') as f:
                json.dump(phrase_index_serializable, f, ensure_ascii=False, indent=2)
            
            with open("knowledge_category_index.json", 'w', encoding='utf-8') as f:
                json.dump(dict(self.category_index), f, ensure_ascii=False, indent=2)
            
            # Create marker for text-search mode
            with open("knowledge_text_search.marker", 'w') as f:
                f.write("text_search_ready")
            
            # Create search statistics
            stats = {
                'total_documents': len(self.documents),
                'total_words': sum(doc['word_count'] for doc in self.documents),
                'total_characters': sum(doc['char_count'] for doc in self.documents),
                'unique_keywords': len(self.word_index),
                'unique_phrases': len(self.phrase_index),
                'categories': list(self.category_index.keys()),
                'documents_by_category': {cat: len(docs) for cat, docs in self.category_index.items()},
                'search_mode': 'text_only'
            }
            
            with open("knowledge_stats.json", 'w') as f:
                json.dump(stats, f, indent=2)
            
            self.logger.info(f"Successfully built text-search knowledge base!")
            self.logger.info(f"- Documents: {stats['total_documents']}")
            self.logger.info(f"- Keywords: {stats['unique_keywords']}")
            self.logger.info(f"- Phrases: {stats['unique_phrases']}")
            self.logger.info(f"- Categories: {len(stats['categories'])}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error building knowledge base: {e}")
            return False

class TextSearchEngine:
    """Simple text search engine for the knowledge base."""
    
    def __init__(self):
        self.documents = []
        self.word_index = {}
        self.phrase_index = {}
        self.category_index = {}
        self.loaded = False
    
    def load_indices(self) -> bool:
        """Load the text search indices."""
        try:
            # Load documents
            with open("knowledge_documents.pkl", 'rb') as f:
                self.documents = pickle.load(f)
            
            # Load indices
            with open("knowledge_word_index.json", 'r', encoding='utf-8') as f:
                self.word_index = json.load(f)
            
            with open("knowledge_phrase_index.json", 'r', encoding='utf-8') as f:
                self.phrase_index = json.load(f)
            
            with open("knowledge_category_index.json", 'r', encoding='utf-8') as f:
                self.category_index = json.load(f)
            
            self.loaded = True
            return True
            
        except Exception as e:
            print(f"Error loading indices: {e}")
            return False
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for documents matching the query."""
        if not self.loaded:
            return []
        
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
            if query_lower in doc['cleaned_text'].lower():
                doc_scores[doc['id']] += 0.5
        
        # Sort by score and return top results
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in sorted_docs[:max_results]:
            doc = next((d for d in self.documents if d['id'] == doc_id), None)
            if doc:
                result = doc.copy()
                result['search_score'] = score
                results.append(result)
        
        return results

def test_search_engine():
    """Test the text search engine."""
    print("\n" + "="*50)
    print("🔍 TESTING TEXT SEARCH ENGINE")
    print("="*50)
    
    engine = TextSearchEngine()
    if not engine.load_indices():
        print("❌ Could not load search indices")
        return
    
    test_queries = [
        "hotel booking",
        "payment configuration",
        "GDS setup",
        "pricing contract",
        "cancel reservation"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        results = engine.search(query, max_results=3)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['title']} (score: {result['search_score']:.1f})")
                print(f"     Category: {result['category']}")
                print(f"     Preview: {result['text_content'][:100]}...")
        else:
            print("  No results found")

def main():
    """Main function."""
    setup_logging()
    logger = logging.getLogger("Main")
    
    print("🔨 Building Text-Search Knowledge Base")
    print("="*50)
    print("This approach uses simple text indexing without ML models.")
    print("It requires minimal memory and works on any system.")
    print("="*50)
    
    builder = TextKnowledgeBuilder()
    
    if builder.build_knowledge_base():
        print("\n✅ SUCCESS! Text-search knowledge base built successfully!")
        
        # Show statistics
        try:
            with open("knowledge_stats.json", 'r') as f:
                stats = json.load(f)
            
            print("\n📊 KNOWLEDGE BASE STATISTICS")
            print("="*30)
            print(f"📄 Documents: {stats['total_documents']}")
            print(f"📝 Total words: {stats['total_words']:,}")
            print(f"🔤 Total characters: {stats['total_characters']:,}")
            print(f"🔑 Unique keywords: {stats['unique_keywords']:,}")
            print(f"💬 Unique phrases: {stats['unique_phrases']:,}")
            print(f"🏷️  Categories: {', '.join(stats['categories'])}")
            
            print("\n💾 FILES CREATED:")
            print("- knowledge_documents.pkl (document storage)")
            print("- knowledge_word_index.json (keyword index)")
            print("- knowledge_phrase_index.json (phrase index)")
            print("- knowledge_category_index.json (category index)")
            print("- knowledge_stats.json (statistics)")
            print("- knowledge_text_search.marker (mode indicator)")
            
            print("\n🚀 The Streamlit app will now use text-search mode!")
            print("While not as advanced as vector search, it provides:")
            print("- Fast keyword and phrase matching")
            print("- Category-based filtering")
            print("- Low memory requirements")
            print("- Reliable performance")
            
        except Exception as e:
            logger.warning(f"Could not read statistics: {e}")
        
        # Test the search engine
        test_search_engine()
        
        return True
    else:
        print("\n❌ FAILED to build knowledge base")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 