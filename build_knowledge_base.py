#!/usr/bin/env python3
"""
Standalone script to build the knowledge base from documents.
This script processes documents one by one to minimize memory usage.
"""

import os
import sys
import logging
import gc
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.knowledge_vector_store import KnowledgeVectorStore

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('knowledge_build.log')
        ]
    )

def main():
    """Main function to build knowledge base."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting knowledge base build process...")
    
    try:
        # Force garbage collection
        gc.collect()
        
        # Initialize knowledge vector store
        knowledge_store = KnowledgeVectorStore()
        
        # Build the index with minimum batch size
        logger.info("Building knowledge vector index with minimal memory usage...")
        knowledge_store.build_index(force_rebuild=True, batch_size=1)
        
        # Get and display statistics
        stats = knowledge_store.get_stats()
        logger.info(f"Knowledge base built successfully!")
        logger.info(f"Total documents: {stats['total_documents']}")
        logger.info(f"Total chunks: {stats['total_chunks']}")
        logger.info(f"Categories: {', '.join(stats['categories'])}")
        
        print("\n" + "="*50)
        print("✅ KNOWLEDGE BASE BUILD COMPLETE!")
        print("="*50)
        print(f"📚 Total documents: {stats['total_documents']}")
        print(f"📄 Total chunks: {stats['total_chunks']}")
        print(f"🏷️  Categories: {', '.join(stats['categories'])}")
        print(f"💾 Index saved to: knowledge_vector_index.faiss")
        print(f"📋 Documents saved to: knowledge_documents.pkl")
        print("\nYou can now run the Streamlit app with full knowledge base support!")
        
    except Exception as e:
        logger.error(f"Error building knowledge base: {str(e)}")
        print(f"\n❌ Error building knowledge base: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 