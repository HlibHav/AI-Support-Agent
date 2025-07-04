#!/usr/bin/env python3
"""
Robust knowledge base builder with multiple fallback strategies.
This script tries different approaches to build the knowledge base successfully.
"""

import os
import sys
import gc
import logging
import pickle
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('knowledge_build_robust.log')
        ]
    )

def strategy_1_ultralight():
    """Strategy 1: Ultra-lightweight - smallest model, micro batches."""
    logger = logging.getLogger("Strategy1")
    logger.info("Attempting Strategy 1: Ultra-lightweight with paraphrase-MiniLM-L3-v2")
    
    try:
        # Force garbage collection
        gc.collect()
        
        # Use smallest possible model
        from sentence_transformers import SentenceTransformer
        model_name = "paraphrase-MiniLM-L3-v2"  # Only ~61MB
        
        logger.info(f"Loading ultra-light model: {model_name}")
        encoder = SentenceTransformer(model_name)
        encoder.eval()  # Set to evaluation mode
        
        import faiss
        dimension = encoder.get_sentence_embedding_dimension()
        index = faiss.IndexFlatIP(dimension)
        
        from src.document_processor import DocumentProcessor
        doc_processor = DocumentProcessor()
        
        # Get files
        docx_files = list(Path("Knowledge").rglob("*.docx"))
        docx_files = [f for f in docx_files if not f.name.startswith('~$')]
        
        if not docx_files:
            logger.error("No documents found")
            return False
        
        logger.info(f"Processing {len(docx_files)} documents with ultra-light approach")
        
        documents = []
        
        # Process one document at a time with micro-batches
        for i, file_path in enumerate(docx_files):
            logger.info(f"Processing {i+1}/{len(docx_files)}: {file_path.name}")
            
            try:
                # Extract text
                text_content = doc_processor.extract_text_from_docx(file_path)
                if not text_content.strip():
                    continue
                
                # Get metadata
                metadata = doc_processor.get_document_metadata(file_path)
                
                # Create smaller chunks (256 chars instead of 1000)
                chunk_size = 256
                overlap = 32
                
                chunks = []
                start = 0
                chunk_id = 0
                
                while start < len(text_content):
                    end = min(start + chunk_size, len(text_content))
                    chunk_text = text_content[start:end]
                    
                    # Word boundary
                    if end < len(text_content):
                        last_space = chunk_text.rfind(' ')
                        if last_space > chunk_size * 0.7:
                            end = start + last_space
                            chunk_text = text_content[start:end]
                    
                    chunk = {
                        'id': f"doc_{len(documents) + len(chunks) + 1}_chunk_{chunk_id}",
                        'text_content': chunk_text,
                        'title': file_path.stem,
                        'category': metadata['category'],
                        'filename': metadata['filename'],
                        'relative_path': metadata['relative_path'],
                        'chunk_id': chunk_id,
                        'char_count': len(chunk_text),
                        'word_count': len(chunk_text.split()),
                        'is_chunk': True
                    }
                    
                    chunks.append(chunk)
                    chunk_id += 1
                    start = end - overlap
                    
                    if start >= end:
                        break
                
                # Process chunks in micro-batches of 3
                micro_batch_size = 3
                for batch_start in range(0, len(chunks), micro_batch_size):
                    batch_end = min(batch_start + micro_batch_size, len(chunks))
                    batch_chunks = chunks[batch_start:batch_end]
                    
                    # Create embeddings
                    texts = [chunk['text_content'] for chunk in batch_chunks]
                    embeddings = encoder.encode(texts, convert_to_numpy=True)
                    
                    # Normalize and add to index
                    embeddings_normalized = embeddings.astype('float32')
                    faiss.normalize_L2(embeddings_normalized)
                    # Handle different FAISS API versions
                    try:
                        index.add(embeddings_normalized)  # type: ignore
                    except Exception as e:
                        # Alternative API call for older FAISS versions
                        index.add(embeddings_normalized)  # type: ignore
                    
                    # Add to documents
                    documents.extend(batch_chunks)
                    
                    # Cleanup
                    del embeddings, embeddings_normalized, texts, batch_chunks
                    gc.collect()
                
                logger.info(f"Processed {file_path.name}: {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
        
        # Save results
        logger.info("Saving knowledge base...")
        faiss.write_index(index, "knowledge_vector_index.faiss")
        
        with open("knowledge_documents.pkl", 'wb') as f:
            pickle.dump(documents, f)
        
        logger.info(f"Successfully built knowledge base with {len(documents)} chunks!")
        return True
        
    except Exception as e:
        logger.error(f"Strategy 1 failed: {e}")
        return False

def strategy_2_text_only():
    """Strategy 2: Text-only approach - no vector embeddings."""
    logger = logging.getLogger("Strategy2")
    logger.info("Attempting Strategy 2: Text-only (no embeddings)")
    
    try:
        from src.document_processor import DocumentProcessor
        doc_processor = DocumentProcessor()
        
        # Get files
        docx_files = list(Path("Knowledge").rglob("*.docx"))
        docx_files = [f for f in docx_files if not f.name.startswith('~$')]
        
        if not docx_files:
            logger.error("No documents found")
            return False
        
        logger.info(f"Processing {len(docx_files)} documents (text-only)")
        
        documents = []
        
        for i, file_path in enumerate(docx_files):
            logger.info(f"Processing {i+1}/{len(docx_files)}: {file_path.name}")
            
            try:
                # Extract text
                text_content = doc_processor.extract_text_from_docx(file_path)
                if not text_content.strip():
                    continue
                
                # Get metadata
                metadata = doc_processor.get_document_metadata(file_path)
                
                # Create document entry
                document = {
                    'id': f"doc_{len(documents) + 1}",
                    'text_content': text_content,
                    'title': file_path.stem,
                    'char_count': len(text_content),
                    'word_count': len(text_content.split()),
                    **metadata
                }
                
                documents.append(document)
                
                # Force garbage collection
                gc.collect()
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
        
        # Save documents
        with open("knowledge_documents.pkl", 'wb') as f:
            pickle.dump(documents, f)
        
        # Create marker for text-only mode
        with open("knowledge_text_only.marker", 'w') as f:
            f.write("text_search_only")
        
        logger.info(f"Successfully built text-only knowledge base with {len(documents)} documents!")
        return True
        
    except Exception as e:
        logger.error(f"Strategy 2 failed: {e}")
        return False

def strategy_3_progressive():
    """Strategy 3: Progressive building with checkpoints."""
    logger = logging.getLogger("Strategy3")
    logger.info("Attempting Strategy 3: Progressive building")
    
    try:
        # Check if we can resume from checkpoint
        checkpoint_file = "knowledge_checkpoint.pkl"
        if os.path.exists(checkpoint_file):
            logger.info("Found checkpoint, resuming...")
            with open(checkpoint_file, 'rb') as f:
                checkpoint = pickle.load(f)
            processed_files = checkpoint.get('processed_files', set())
            documents = checkpoint.get('documents', [])
        else:
            processed_files = set()
            documents = []
        
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer("all-MiniLM-L6-v2")
        encoder.eval()
        
        import faiss
        dimension = encoder.get_sentence_embedding_dimension()
        
        # Load existing index if available
        if os.path.exists("knowledge_vector_index.faiss") and documents:
            index = faiss.read_index("knowledge_vector_index.faiss")
            logger.info(f"Resumed with {len(documents)} existing documents")
        else:
            index = faiss.IndexFlatIP(dimension)
        
        from src.document_processor import DocumentProcessor
        doc_processor = DocumentProcessor()
        
        # Get files
        docx_files = list(Path("Knowledge").rglob("*.docx"))
        docx_files = [f for f in docx_files if not f.name.startswith('~$')]
        remaining_files = [f for f in docx_files if str(f) not in processed_files]
        
        logger.info(f"Processing {len(remaining_files)} remaining documents")
        
        for i, file_path in enumerate(remaining_files):
            logger.info(f"Processing {i+1}/{len(remaining_files)}: {file_path.name}")
            
            try:
                # Process document (similar to strategy 1 but with checkpoints)
                text_content = doc_processor.extract_text_from_docx(file_path)
                if not text_content.strip():
                    processed_files.add(str(file_path))
                    continue
                
                metadata = doc_processor.get_document_metadata(file_path)
                
                # Create chunks
                chunk_size = 512
                chunks = []
                start = 0
                chunk_id = 0
                
                while start < len(text_content):
                    end = min(start + chunk_size, len(text_content))
                    chunk_text = text_content[start:end]
                    
                    if end < len(text_content):
                        last_space = chunk_text.rfind(' ')
                        if last_space > chunk_size * 0.7:
                            end = start + last_space
                            chunk_text = text_content[start:end]
                    
                    chunk = {
                        'id': f"doc_{len(documents) + len(chunks) + 1}_chunk_{chunk_id}",
                        'text_content': chunk_text,
                        'title': file_path.stem,
                        'category': metadata['category'],
                        'filename': metadata['filename'],
                        'relative_path': metadata['relative_path'],
                        'chunk_id': chunk_id,
                        'char_count': len(chunk_text),
                        'word_count': len(chunk_text.split()),
                        'is_chunk': True
                    }
                    
                    chunks.append(chunk)
                    chunk_id += 1
                    start = end - (chunk_size // 4)  # 25% overlap
                    
                    if start >= end:
                        break
                
                # Process in small batches
                batch_size = 5
                for batch_start in range(0, len(chunks), batch_size):
                    batch_end = min(batch_start + batch_size, len(chunks))
                    batch_chunks = chunks[batch_start:batch_end]
                    
                    texts = [chunk['text_content'] for chunk in batch_chunks]
                    embeddings = encoder.encode(texts, convert_to_numpy=True)
                    
                    embeddings_normalized = embeddings.astype('float32')
                    faiss.normalize_L2(embeddings_normalized)
                    # Handle different FAISS API versions
                    try:
                        index.add(embeddings_normalized)  # type: ignore
                    except Exception as e:
                        # Alternative API call for older FAISS versions
                        index.add(embeddings_normalized)  # type: ignore
                    
                    documents.extend(batch_chunks)
                    
                    del embeddings, embeddings_normalized, texts
                    gc.collect()
                
                processed_files.add(str(file_path))
                
                # Save checkpoint every 5 files
                if (i + 1) % 5 == 0:
                    checkpoint = {
                        'processed_files': processed_files,
                        'documents': documents
                    }
                    with open(checkpoint_file, 'wb') as f:
                        pickle.dump(checkpoint, f)
                    
                    # Save intermediate index
                    faiss.write_index(index, "knowledge_vector_index.faiss")
                    logger.info(f"Checkpoint saved at {i+1}/{len(remaining_files)}")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                processed_files.add(str(file_path))  # Mark as processed to skip
                continue
        
        # Final save
        faiss.write_index(index, "knowledge_vector_index.faiss")
        with open("knowledge_documents.pkl", 'wb') as f:
            pickle.dump(documents, f)
        
        # Cleanup checkpoint
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
        
        logger.info(f"Successfully built knowledge base with {len(documents)} chunks!")
        return True
        
    except Exception as e:
        logger.error(f"Strategy 3 failed: {e}")
        return False

def main():
    """Main function - try multiple strategies."""
    setup_logging()
    logger = logging.getLogger("Main")
    
    logger.info("Starting robust knowledge base building...")
    
    strategies = [
        ("Ultra-lightweight", strategy_1_ultralight),
        ("Progressive building", strategy_3_progressive),
        ("Text-only fallback", strategy_2_text_only),
    ]
    
    for strategy_name, strategy_func in strategies:
        logger.info(f"\n{'='*50}")
        logger.info(f"Trying strategy: {strategy_name}")
        logger.info(f"{'='*50}")
        
        try:
            if strategy_func():
                logger.info(f"\n✅ SUCCESS! Strategy '{strategy_name}' completed successfully!")
                
                # Print results
                try:
                    if os.path.exists("knowledge_documents.pkl"):
                        with open("knowledge_documents.pkl", 'rb') as f:
                            docs = pickle.load(f)
                        
                        categories = {}
                        total_words = 0
                        for doc in docs:
                            cat = doc.get('category', 'Unknown')
                            categories[cat] = categories.get(cat, 0) + 1
                            total_words += doc.get('word_count', 0)
                        
                        print("\n" + "="*50)
                        print("📚 KNOWLEDGE BASE SUCCESSFULLY BUILT!")
                        print("="*50)
                        print(f"📄 Total documents/chunks: {len(docs)}")
                        print(f"📝 Total words: {total_words:,}")
                        print(f"🏷️  Categories: {', '.join(categories.keys())}")
                        
                        if os.path.exists("knowledge_vector_index.faiss"):
                            print(f"🔍 Vector search: Available")
                        elif os.path.exists("knowledge_text_only.marker"):
                            print(f"🔍 Search mode: Text-only")
                        
                        print(f"💾 Files created:")
                        if os.path.exists("knowledge_vector_index.faiss"):
                            print(f"   - knowledge_vector_index.faiss")
                        print(f"   - knowledge_documents.pkl")
                        if os.path.exists("knowledge_text_only.marker"):
                            print(f"   - knowledge_text_only.marker")
                        
                        print("\n🚀 You can now run the Streamlit app with full knowledge base support!")
                        
                except Exception as e:
                    logger.warning(f"Could not read results: {e}")
                
                return True
                
        except Exception as e:
            logger.error(f"Strategy '{strategy_name}' failed with exception: {e}")
            continue
        
        # Force cleanup between strategies
        gc.collect()
        time.sleep(2)
    
    logger.error("\n❌ All strategies failed!")
    print("\n" + "="*50)
    print("❌ KNOWLEDGE BASE BUILD FAILED")
    print("="*50)
    print("All strategies failed. This may be due to:")
    print("1. Insufficient memory")
    print("2. Missing dependencies")
    print("3. Corrupted document files")
    print("\nYou can still use the ticket analysis features.")
    print("The enhanced chat will use text-only search if needed.")
    
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 