import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
import faiss
from sentence_transformers import SentenceTransformer
import pickle
import os


class TicketVectorStore:
    """Vector store for ticket descriptions using sentence transformers and FAISS."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.tickets_data = []
        self.embeddings = None
        self.is_built = False
        
    def build_index(self, tickets_df: pd.DataFrame, text_column: str = 'combined_text'):
        """Build FAISS index from ticket descriptions."""
        print("🔄 Building vector index from ticket descriptions...")
        
        # Extract ticket data and text
        tickets_text = []
        tickets_metadata = []
        
        for _, ticket in tickets_df.iterrows():
            text = ticket.get(text_column, '')
            if text and len(text.strip()) > 0:
                tickets_text.append(text.strip())
                tickets_metadata.append({
                    'id': ticket.get('#', 'N/A'),
                    'subject': ticket.get('Subject', 'No subject'),
                    'status': ticket.get('Status', 'Unknown'),
                    'priority': ticket.get('Priority', 'Unknown'),
                    'assignee': ticket.get('Assignee', 'Unassigned'),
                    'project': ticket.get('Project', 'Unknown'),
                    'description': ticket.get('Description', '')[:500],  # Truncate for storage
                    'created': ticket.get('Created', 'Unknown'),
                    'text': text[:1000]  # Store first 1000 chars
                })
        
        if not tickets_text:
            print("❌ No valid ticket descriptions found for indexing")
            return
        
        print(f"📝 Processing {len(tickets_text)} ticket descriptions...")
        
        # Generate embeddings
        self.embeddings = self.model.encode(
            tickets_text, 
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Build FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings)
        self.index.add(self.embeddings)
        
        # Store metadata
        self.tickets_data = tickets_metadata
        self.is_built = True
        
        print(f"✅ Vector index built successfully with {len(tickets_text)} tickets")
        print(f"🎯 Embedding dimension: {dimension}")
        
    def search_similar_tickets(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar tickets based on query."""
        if not self.is_built:
            return []
        
        # Encode query
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, k)
        
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(self.tickets_data):
                ticket_data = self.tickets_data[idx].copy()
                ticket_data['similarity_score'] = float(score)
                ticket_data['rank'] = i + 1
                results.append(ticket_data)
        
        return results
    
    def get_context_for_query(self, query: str, max_tickets: int = 3) -> str:
        """Get relevant ticket context for a query."""
        if not self.is_built:
            return "Vector index not available."
        
        similar_tickets = self.search_similar_tickets(query, k=max_tickets)
        
        if not similar_tickets:
            return "No relevant tickets found."
        
        context = f"**Relevant tickets from dataset (similarity search):**\n\n"
        
        for ticket in similar_tickets:
            context += f"**Ticket #{ticket['id']}** (similarity: {ticket['similarity_score']:.3f})\n"
            context += f"- **Subject:** {ticket['subject']}\n"
            context += f"- **Status:** {ticket['status']}, **Priority:** {ticket['priority']}\n"
            context += f"- **Assignee:** {ticket['assignee']}\n"
            context += f"- **Description:** {ticket['description']}...\n\n"
        
        return context
    
    def save_index(self, filepath: str):
        """Save the vector index and metadata to disk."""
        if not self.is_built:
            print("❌ No index to save")
            return
        
        try:
            # Save FAISS index
            faiss.write_index(self.index, f"{filepath}.faiss")
            
            # Save metadata and embeddings
            data_to_save = {
                'tickets_data': self.tickets_data,
                'embeddings': self.embeddings,
                'model_name': self.model_name
            }
            
            with open(f"{filepath}.pkl", 'wb') as f:
                pickle.dump(data_to_save, f)
            
            print(f"✅ Vector index saved to {filepath}")
            
        except Exception as e:
            print(f"❌ Error saving index: {e}")
    
    def load_index(self, filepath: str) -> bool:
        """Load the vector index and metadata from disk."""
        try:
            # Load FAISS index
            if os.path.exists(f"{filepath}.faiss"):
                self.index = faiss.read_index(f"{filepath}.faiss")
            else:
                return False
            
            # Load metadata
            if os.path.exists(f"{filepath}.pkl"):
                with open(f"{filepath}.pkl", 'rb') as f:
                    data = pickle.load(f)
                    self.tickets_data = data['tickets_data']
                    self.embeddings = data['embeddings']
                    
                    # Reinitialize model if different
                    if data['model_name'] != self.model_name:
                        self.model = SentenceTransformer(data['model_name'])
                        self.model_name = data['model_name']
            else:
                return False
            
            self.is_built = True
            print(f"✅ Vector index loaded from {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading index: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        if not self.is_built:
            return {'status': 'not_built'}
        
        return {
            'status': 'ready',
            'total_tickets': len(self.tickets_data),
            'embedding_dimension': self.embeddings.shape[1] if self.embeddings is not None else 0,
            'model_name': self.model_name
        } 