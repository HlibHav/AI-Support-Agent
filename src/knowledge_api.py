"""
FastAPI-based Knowledge Base Update API
Provides endpoints for updating and rebuilding the knowledge base.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Union
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="AI Support Agent - Knowledge Base API",
    description="API for managing and updating the knowledge base",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure according to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
knowledge_builder = None
last_build_time = None
build_in_progress = False

# Pydantic models
class KnowledgeStats(BaseModel):
    """Knowledge base statistics."""
    total_documents: int
    total_chunks: int
    last_updated: Optional[datetime]
    build_status: str
    knowledge_type: str  # "vector", "text", or "none"

class BuildResponse(BaseModel):
    """Response for build operations."""
    success: bool
    message: str
    task_id: Optional[str] = None
    stats: Optional[KnowledgeStats] = None

class DocumentUpload(BaseModel):
    """Document upload response."""
    success: bool
    message: str
    filename: str
    document_id: Optional[str] = None

class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(10, ge=1, le=100)
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)

class SearchResult(BaseModel):
    """Search result model."""
    content: str
    score: float
    metadata: dict[str, Union[str, int, float]]

class SearchResponse(BaseModel):
    """Search response model."""
    results: list[SearchResult]
    total_found: int
    query: str


def get_knowledge_stats() -> KnowledgeStats:
    """Get current knowledge base statistics."""
    global last_build_time, build_in_progress
    
    # Check for different knowledge base types
    has_vector = os.path.exists("knowledge_vector_index.faiss") and os.path.exists("knowledge_documents.pkl")
    has_text = os.path.exists("knowledge_text_search.marker")
    
    knowledge_type = "none"
    if has_vector:
        knowledge_type = "vector"
    elif has_text:
        knowledge_type = "text"
    
    total_documents = 0
    total_chunks = 0
    
    # Try to load stats from files
    try:
        if os.path.exists("knowledge_stats.json"):
            with open("knowledge_stats.json", "r") as f:
                stats: dict[str, Union[str, int]] = json.load(f)
                total_documents = int(stats.get("total_documents", 0))
                total_chunks = int(stats.get("total_chunks", 0))
                last_updated_str = stats.get("last_updated")
                if last_updated_str and isinstance(last_updated_str, str):
                    last_build_time = datetime.fromisoformat(last_updated_str)
    except Exception as e:
        logger.warning(f"Could not load knowledge stats: {e}")
    
    build_status = "building" if build_in_progress else "ready" if knowledge_type != "none" else "not_built"
    
    return KnowledgeStats(
        total_documents=total_documents,
        total_chunks=total_chunks,
        last_updated=last_build_time,
        build_status=build_status,
        knowledge_type=knowledge_type
    )


def save_knowledge_stats(stats: dict[str, Union[str, int]]) -> None:
    """Save knowledge base statistics to file."""
    try:
        with open("knowledge_stats.json", "w") as f:
            json.dump(stats, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Could not save knowledge stats: {e}")


def build_knowledge_base_task(build_type: str = "text") -> dict[str, Union[str, bool, dict[str, Union[str, int]]]]:
    """Background task to build knowledge base."""
    global knowledge_builder, last_build_time, build_in_progress
    
    try:
        build_in_progress = True
        logger.info(f"Starting knowledge base build: {build_type}")
        
        # Count documents in Knowledge directory
        knowledge_dir = Path("Knowledge")
        if not knowledge_dir.exists():
            raise ValueError("Knowledge directory not found")
        
        # Count .docx files recursively
        docx_files = list(knowledge_dir.rglob("*.docx"))
        total_documents = len(docx_files)
        
        if total_documents == 0:
            raise ValueError("No .docx files found in Knowledge directory")
        
        # Build based on type
        if build_type == "vector":
            # Vector-based build
            _ = os.system("python build_knowledge_base_robust.py")
        elif build_type == "text":
            # Text-search build
            _ = os.system("python build_text_search_knowledge.py")
        elif build_type == "lightweight":
            # Lightweight build
            _ = os.system("python build_knowledge_base.py")
        else:
            raise ValueError(f"Unknown build type: {build_type}")
        
        # Update stats
        last_build_time = datetime.now()
        stats = {
            "total_documents": total_documents,
            "total_chunks": total_documents * 10,  # Estimate
            "last_updated": last_build_time.isoformat(),
            "build_type": build_type
        }
        save_knowledge_stats(stats)
        
        logger.info(f"Knowledge base build completed: {build_type}")
        return {
            "success": True,
            "message": f"Knowledge base built successfully ({build_type})",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Knowledge base build failed: {e}")
        return {
            "success": False,
            "message": f"Build failed: {str(e)}"
        }
    finally:
        build_in_progress = False


@app.get("/", response_model=dict[str, Union[str, list[str]]])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Support Agent - Knowledge Base API",
        "version": "1.0.0",
        "description": "API for managing and updating the knowledge base",
        "endpoints": [
            "/stats - Get knowledge base statistics",
            "/build - Build knowledge base",
            "/search - Search knowledge base",
            "/upload - Upload documents",
            "/health - Health check"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/stats", response_model=KnowledgeStats)
async def get_stats():
    """Get knowledge base statistics."""
    try:
        stats = get_knowledge_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build", response_model=BuildResponse)
async def build_knowledge_base(
    background_tasks: BackgroundTasks,
    build_type: str = "text",
    force: bool = False
):
    """Build or rebuild the knowledge base."""
    global build_in_progress
    
    if build_in_progress and not force:
        raise HTTPException(
            status_code=409, 
            detail="Knowledge base build already in progress"
        )
    
    if build_type not in ["vector", "text", "lightweight"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid build type. Use 'vector', 'text', or 'lightweight'"
        )
    
    try:
        # Check if Knowledge directory exists
        knowledge_dir = Path("Knowledge")
        if not knowledge_dir.exists():
            raise HTTPException(
                status_code=404, 
                detail="Knowledge directory not found"
            )
        
        # Count documents
        docx_files = list(knowledge_dir.rglob("*.docx"))
        if not docx_files:
            raise HTTPException(
                status_code=404, 
                detail="No .docx files found in Knowledge directory"
            )
        
        # Start background task
        background_tasks.add_task(build_knowledge_base_task, build_type)
        
        return BuildResponse(
            success=True,
            message=f"Knowledge base build started ({build_type})",
            task_id=f"build_{datetime.now().isoformat()}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting build: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
async def search_knowledge_base(request: SearchRequest):
    """Search the knowledge base."""
    try:
        # Check if knowledge base exists
        has_vector = os.path.exists("knowledge_vector_index.faiss")
        has_text = os.path.exists("knowledge_text_search.marker")
        
        if not has_vector and not has_text:
            raise HTTPException(
                status_code=404, 
                detail="Knowledge base not found. Please build it first."
            )
        
        results = []
        
        if has_vector:
            # Use vector search (implement based on your vector store)
            try:
                from .knowledge_vector_store import KnowledgeVectorStore
                vector_store = KnowledgeVectorStore("knowledge_vector_index.faiss")
                search_results = vector_store.search(request.query, request.limit)
                
                results = [
                    SearchResult(
                        content=str(result.get("content", "")),
                        score=float(result.get("score", 0.0)),
                        metadata=dict(result.get("metadata", {}))
                    )
                    for result in search_results
                ]
            except Exception as e:
                logger.warning(f"Vector search failed: {e}")
        
        if has_text and not results:
            # Use text search as fallback
            try:
                # Load text search index
                if os.path.exists("knowledge_word_index.json"):
                    with open("knowledge_word_index.json", "r") as f:
                        word_index: dict[str, list[int]] = json.load(f)
                    
                    # Simple text search (implement more sophisticated search as needed)
                    query_words = request.query.lower().split()
                    matching_docs = set()
                    
                    for word in query_words:
                        if word in word_index:
                            matching_docs.update(word_index[word])
                    
                    # Load document content
                    if os.path.exists("knowledge_documents.pkl"):
                        import pickle
                        with open("knowledge_documents.pkl", "rb") as f:
                            documents: list[dict[str, Union[str, dict[str, Union[str, int]]]]] = pickle.load(f)
                        
                        for doc_id in list(matching_docs)[:request.limit]:
                            if doc_id < len(documents):
                                doc = documents[doc_id]
                                content = doc.get("content", "")
                                content_str = str(content)[:500] if content else ""
                                metadata = doc.get("metadata", {})
                                metadata_dict = dict(metadata) if isinstance(metadata, dict) else {}
                                results.append(SearchResult(
                                    content=content_str,
                                    score=0.8,  # Default score for text search
                                    metadata=metadata_dict
                                ))
                            
            except Exception as e:
                logger.warning(f"Text search failed: {e}")
        
        return SearchResponse(
            results=results,
            total_found=len(results),
            query=request.query
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload", response_model=DocumentUpload)
async def upload_document(
    file: UploadFile = File(...),
    rebuild: bool = Form(default=False)
):
    """Upload a new document to the knowledge base."""
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith('.docx'):
            raise HTTPException(
                status_code=400, 
                detail="Only .docx files are supported"
            )
        
        # Create Knowledge directory if it doesn't exist
        knowledge_dir = Path("Knowledge")
        knowledge_dir.mkdir(exist_ok=True)
        
        # Save uploaded file
        filename = file.filename  # Type narrowing - we know it's not None from check above
        file_path = knowledge_dir / filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        response = DocumentUpload(
            success=True,
            message=f"Document '{file.filename}' uploaded successfully",
            filename=file.filename,
            document_id=str(file_path)
        )
        
        # Trigger rebuild if requested
        if rebuild:
            background_tasks = BackgroundTasks()
            background_tasks.add_task(build_knowledge_base_task, "text")
            response.message += " (rebuild started)"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/clear")
async def clear_knowledge_base():
    """Clear the knowledge base (remove all index files)."""
    try:
        files_to_remove = [
            "knowledge_vector_index.faiss",
            "knowledge_documents.pkl",
            "knowledge_text_search.marker",
            "knowledge_word_index.json",
            "knowledge_phrase_index.json",
            "knowledge_category_index.json",
            "knowledge_stats.json"
        ]
        
        removed_files = []
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
                removed_files.append(file_path)
        
        global last_build_time, build_in_progress
        last_build_time = None
        build_in_progress = False
        
        return {
            "success": True,
            "message": "Knowledge base cleared successfully",
            "removed_files": removed_files
        }
        
    except Exception as e:
        logger.error(f"Clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def list_documents():
    """List all documents in the Knowledge directory."""
    try:
        knowledge_dir = Path("Knowledge")
        if not knowledge_dir.exists():
            return {"documents": [], "total": 0}
        
        documents = []
        for file_path in knowledge_dir.rglob("*.docx"):
            stat = file_path.stat()
            documents.append({
                "name": file_path.name,
                "path": str(file_path.relative_to(knowledge_dir)),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return {
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 