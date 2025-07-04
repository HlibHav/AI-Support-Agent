#!/usr/bin/env python3
"""
Lightweight knowledge base builder with aggressive memory management.
Uses multiple strategies to avoid memory issues.
"""

import os
import gc
import sys
import logging
import pickle
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

# Try different embedding approaches
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from .document_processor import DocumentProcessor

class LightweightKnowledgeBuilder:
    """Memory-efficient knowledge base builder with multiple fallback strategies."""
    
    def __init__(self, use_small_model: bool = True):
        self.logger = logging.getLogger(__name__)
        self.documents = []
        self.use_small_model = use_small_model
        
        # Use smallest possible model for memory efficiency
        if self.use_small_model:
            self.model_name = "paraphrase-MiniLM-L3-v2"  # Only 61MB vs 384MB
            self.dimension = 384
        else:
            self.model_name = "all-MiniLM-L6-v2"
            self.dimension = 384
        
        self.encoder = None
        self.index = None
        self.document_processor = DocumentProcessor()
        
        # File paths
        self.index_file = "knowledge_vector_index.faiss"
        self.documents_file = "knowledge_documents.pkl"
        self.temp_dir = tempfile.mkdtemp()
        
    def initialize_encoder(self):
        """Initialize encoder with memory management."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers not available")
        
        try:
            # Force garbage collection before loading model
            gc.collect()
            
            self.logger.info(f"Loading lightweight model: {self.model_name}")
            self.encoder = SentenceTransformer(self.model_name)
            
            # Set to evaluation mode to save memory
            self.encoder.eval()
            
            self.logger.info(f"Model loaded successfully, dimension: {self.dimension}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            return False
    
    def process_single_document(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process a single document and return chunks."""
        try:
            # Extract text content
            text_content = self.document_processor.extract_text_from_docx(file_path)
            if not text_content.strip():
                return []
            
            # Get metadata
            metadata = self.document_processor.get_document_metadata(file_path)
            
            # Create document
            document = {
                'id': f"doc_{len(self.documents) + 1}",
                'text_content': text_content,
                'title': file_path.stem,
                'char_count': len(text_content),
                'word_count': len(text_content.split()),
                **metadata
            }
            
            # Chunk the document
            chunks = self._chunk_document(document)
            
            self.logger.info(f"Processed {file_path.name}: {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return []
    
    def _chunk_document(self, document: Dict[str, Any], chunk_size: int = 512, overlap: int = 50) -> List[Dict[str, Any]]:
        """Create smaller chunks to reduce memory usage."""
        text = document['text_content']
        chunks = []
        
        if len(text) <= chunk_size:
            return [document]
        
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            
            # Try to break at word boundaries
            if end < len(text):
                last_space = chunk_text.rfind(' ')
                if last_space > chunk_size * 0.7:
                    end = start + last_space
                    chunk_text = text[start:end]
            
            chunk = {
                'id': f"{document['id']}_chunk_{chunk_id}",
                'text_content': chunk_text,
                'title': document['title'],
                'category': document['category'],
                'filename': document['filename'],
                'relative_path': document['relative_path'],
                'chunk_id': chunk_id,
                'parent_id': document['id'],
                'char_count': len(chunk_text),
                'word_count': len(chunk_text.split()),
                'is_chunk': True
            }
            
            chunks.append(chunk)
            chunk_id += 1
            start = end - overlap
            
            if start >= end:
                break
        
        return chunks
    
    def build_with_streaming(self) -> bool:
        """Build knowledge base using streaming approach."""
        try:
            # Initialize encoder
            if not self.initialize_encoder():
                return False
            
            # Initialize FAISS index
            if FAISS_AVAILABLE:
                self.index = faiss.IndexFlatIP(self.dimension)
            else:
                self.logger.warning("FAISS not available, using simple storage")
                self.index = []
            
            # Get document files
            docx_files = list(self.document_processor.knowledge_path.rglob("*.docx"))
            docx_files = [f for f in docx_files if not f.name.startswith('~$')]
            
            if not docx_files:
                self.logger.error("No documents found")
                return False
            
            self.logger.info(f"Processing {len(docx_files)} documents with streaming approach")
            
            processed_count = 0
            
            for i, file_path in enumerate(docx_files):
                try:
                    self.logger.info(f"Processing document {i+1}/{len(docx_files)}: {file_path.name}")
                    
                    # Process single document
                    chunks = self.process_single_document(file_path)
                    if not chunks:
                        continue
                    
                    # Create embeddings for this document's chunks only
                    texts = [chunk['text_content'] for chunk in chunks]
                    
                    # Process in micro-batches to save memory
                    batch_size = 5
                    for batch_start in range(0, len(texts), batch_size):
                        batch_end = min(batch_start + batch_size, len(texts))
                        batch_texts = texts[batch_start:batch_end]
                        batch_chunks = chunks[batch_start:batch_end]
                        
                        # Create embeddings
                        embeddings = self.encoder.encode(batch_texts, convert_to_numpy=True)
                        
                        # Normalize and add to index
                        if FAISS_AVAILABLE:
                            embeddings_normalized = embeddings.astype('float32')
                            faiss.normalize_L2(embeddings_normalized)
                            self.index.add(embeddings_normalized)
                        else:
                            # Store embeddings in simple list
                            for emb in embeddings:
                                self.index.append(emb.astype('float32'))
                        
                        # Add chunks to documents
                        self.documents.extend(batch_chunks)
                        
                        # Force garbage collection after each micro-batch
                        del embeddings, batch_texts, batch_chunks
                        gc.collect()
                    
                    processed_count += 1
                    
                    # Save progress every 10 documents
                    if processed_count % 10 == 0:
                        self._save_progress()
                    
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {e}")
                    continue
            
            self.logger.info(f"Successfully processed {processed_count} documents, {len(self.documents)} chunks")
            
            # Save final result
            return self._save_final()
            
        except Exception as e:
            self.logger.error(f"Error in streaming build: {e}")
            return False
    
    def build_with_minimal_memory(self) -> bool:
        """Build with absolute minimal memory usage - no vector index."""
        try:
            self.logger.info("Building with minimal memory approach (text search only)")
            
            # Get document files
            docx_files = list(self.document_processor.knowledge_path.rglob("*.docx"))
            docx_files = [f for f in docx_files if not f.name.startswith('~$')]
            
            if not docx_files:
                self.logger.error("No documents found")
                return False
            
            self.logger.info(f"Processing {len(docx_files)} documents")
            
            for i, file_path in enumerate(docx_files):
                try:
                    self.logger.info(f"Processing {i+1}/{len(docx_files)}: {file_path.name}")
                    
                    chunks = self.process_single_document(file_path)
                    self.documents.extend(chunks)
                    
                    # Force garbage collection
                    gc.collect()
                    
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {e}")
                    continue
            
            # Save documents without vector index
            with open(self.documents_file, 'wb') as f:
                pickle.dump(self.documents, f)
            
            # Create a simple marker file to indicate text-only mode
            with open("knowledge_text_only.marker", 'w') as f:
                f.write("text_search_only")
            
            self.logger.info(f"Built text-only knowledge base with {len(self.documents)} chunks")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in minimal memory build: {e}")
            return False
    
    def _save_progress(self):
        """Save intermediate progress."""
        try:
            progress_file = os.path.join(self.temp_dir, "progress.pkl")
            with open(progress_file, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'processed_count': len(self.documents)
                }, f)
            self.logger.info(f"Saved progress: {len(self.documents)} chunks")
        except Exception as e:
            self.logger.warning(f"Could not save progress: {e}")
    
    def _save_final(self) -> bool:
        """Save final results."""
        try:
            # Save FAISS index if available
            if FAISS_AVAILABLE and hasattr(self.index, 'ntotal'):
                faiss.write_index(self.index, self.index_file)
                self.logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")
            elif self.index:
                # Save simple index
                with open("knowledge_simple_index.pkl", 'wb') as f:
                    pickle.dump(self.index, f)
                self.logger.info(f"Saved simple index with {len(self.index)} vectors")
            
            # Save documents
            with open(self.documents_file, 'wb') as f:
                pickle.dump(self.documents, f)
            
            self.logger.info(f"Saved {len(self.documents)} document chunks")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving final results: {e}")
            return False
    
    def cleanup(self):
        """Clean up temporary files."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

def build_knowledge_base_robust() -> bool:
    """Try multiple strategies to build knowledge base."""
    builder = LightweightKnowledgeBuilder()
    
    strategies = [
        ("Streaming with small model", lambda: builder.build_with_streaming()),
        ("Minimal memory (text search only)", lambda: builder.build_with_minimal_memory()),
    ]
    
    for strategy_name, strategy_func in strategies:
        try:
            logging.info(f"Trying strategy: {strategy_name}")
            if strategy_func():
                logging.info(f"Success with strategy: {strategy_name}")
                return True
        except Exception as e:
            logging.error(f"Strategy '{strategy_name}' failed: {e}")
            continue
        finally:
            # Always cleanup between attempts
            gc.collect()
    
    logging.error("All strategies failed")
    return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = build_knowledge_base_robust()
    sys.exit(0 if success else 1) 