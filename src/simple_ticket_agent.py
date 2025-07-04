import os
from typing import Dict, List, Any, Optional
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.data_processor import TicketDataProcessor
from src.vector_store import TicketVectorStore


class SimpleTicketAgent:
    """Simple agent that only provides dataset-based responses."""
    
    def __init__(self, csv_path: str, gemini_api_key: str):
        self.csv_path = csv_path
        self.data_processor = TicketDataProcessor(csv_path)
        self.vector_store = TicketVectorStore()
        
        # Initialize LLM
        os.environ["GOOGLE_API_KEY"] = gemini_api_key
        self.llm = ChatGoogleGenerativeAI(
            model="models/gemini-1.5-flash",
            temperature=0.1
        )
        
        # Load and process data
        self._initialize_data()
    
    def _initialize_data(self):
        """Load and process the ticket data."""
        print("Loading and processing ticket data...")
        self.data_processor.load_data()
        self.data_processor.clean_data()
        print("Data processing complete")
        
        # Build vector index for similarity search
        print("Building vector index for enhanced context...")
        try:
            # Try to load existing index first
            index_path = "ticket_vector_index"
            if not self.vector_store.load_index(index_path):
                # Build new index if loading fails
                if self.data_processor.processed_df is not None:
                    self.vector_store.build_index(self.data_processor.processed_df)
                    # Save for future use
                    self.vector_store.save_index(index_path)
                else:
                    print("⚠️ No processed data available for vector indexing")
            
            print("✅ Vector index ready for context-aware responses")
        except Exception as e:
            print(f"⚠️ Vector index unavailable: {e}")
            print("📝 Agent will work without vector context")
    
    def _get_dataset_context(self) -> str:
        """Get a summary of the dataset for context."""
        analysis = self.data_processor.analyze_patterns()
        
        context = f"""
DATASET SUMMARY:
- Total tickets: {analysis.get('total_tickets', 0)}
- Urgent tickets: {analysis.get('urgent_tickets', 0)}
- New tickets: {analysis.get('new_tickets', 0)}
- Closed tickets: {analysis.get('closed_tickets', 0)}
- Average days open: {analysis.get('avg_days_open', 0):.1f}
- Status distribution: {analysis.get('status_distribution', {})}
- Priority distribution: {analysis.get('priority_distribution', {})}
- Top assignees: {analysis.get('top_assignees', {})}
"""
        return context
    
    def _search_tickets(self, query: str) -> str:
        """Search tickets based on query."""
        tickets = self.data_processor.search_tickets(query, limit=10)
        
        if not tickets:
            return f"No tickets found matching '{query}' in the dataset."
        
        results = f"Found {len(tickets)} tickets matching '{query}':\n\n"
        for ticket in tickets:
            results += f"- **#{ticket.get('#', 'N/A')}**: {ticket.get('Subject', 'No subject')}\n"
            results += f"  Status: {ticket.get('Status', 'Unknown')}, Priority: {ticket.get('Priority', 'Unknown')}\n"
            results += f"  Assignee: {ticket.get('Assignee', 'Unassigned')}\n\n"
        
        return results
    
    def _get_priority_tickets(self, priority: str) -> str:
        """Get tickets by priority."""
        tickets = self.data_processor.get_priority_tickets(priority)
        
        if not tickets:
            return f"No {priority} priority tickets found in the dataset."
        
        results = f"Found {len(tickets)} {priority} priority tickets in the dataset:\n\n"
        for ticket in tickets[:5]:  # Show first 5
            results += f"- **#{ticket.get('#', 'N/A')}**: {ticket.get('Subject', 'No subject')}\n"
            results += f"  Status: {ticket.get('Status', 'Unknown')}\n"
            results += f"  Assignee: {ticket.get('Assignee', 'Unassigned')}\n\n"
        
        if len(tickets) > 5:
            results += f"... and {len(tickets) - 5} more {priority} priority tickets.\n"
        
        return results
    
    def _get_status_tickets(self, status: str) -> str:
        """Get tickets by status."""
        tickets = self.data_processor.get_tickets_by_status(status)
        
        if not tickets:
            return f"No tickets with status '{status}' found in the dataset."
        
        results = f"Found {len(tickets)} tickets with status '{status}' in the dataset:\n\n"
        for ticket in tickets[:5]:  # Show first 5
            results += f"- **#{ticket.get('#', 'N/A')}**: {ticket.get('Subject', 'No subject')}\n"
            results += f"  Priority: {ticket.get('Priority', 'Unknown')}\n"
            results += f"  Assignee: {ticket.get('Assignee', 'Unassigned')}\n\n"
        
        if len(tickets) > 5:
            results += f"... and {len(tickets) - 5} more '{status}' tickets.\n"
        
        return results
    
    def _get_ticket_details(self, ticket_id: int) -> str:
        """Get detailed information about a specific ticket."""
        ticket = self.data_processor.get_ticket_by_id(ticket_id)
        
        if not ticket:
            return f"Ticket #{ticket_id} not found in the dataset."
        
        details = f"""
**Ticket #{ticket.get('#', 'N/A')} Details (from dataset):**

**Subject:** {ticket.get('Subject', 'No subject')}
**Status:** {ticket.get('Status', 'Unknown')}
**Priority:** {ticket.get('Priority', 'Unknown')}
**Assignee:** {ticket.get('Assignee', 'Unassigned')}
**Created:** {ticket.get('Created', 'Unknown')}
**Updated:** {ticket.get('Updated', 'Unknown')}

**Description:** {ticket.get('Description', 'No description')[:300]}...
        """
        
        return details.strip()
    
    def _get_project_tickets(self, project: str) -> str:
        """Get tickets by project."""
        if self.data_processor.processed_df is None:
            return "Dataset not loaded."
        
        # Filter tickets by project
        project_tickets = self.data_processor.processed_df[
            self.data_processor.processed_df['Project'].str.contains(project, case=False, na=False)
        ]
        
        if len(project_tickets) == 0:
            return f"No tickets found for project '{project}' in the dataset."
        
        results = f"Found {len(project_tickets)} tickets for project '{project}' in the dataset:\n\n"
        
        # Show first 10 tickets
        for _, ticket in project_tickets.head(10).iterrows():
            results += f"- **#{ticket.get('#', 'N/A')}**: {ticket.get('Subject', 'No subject')}\n"
            results += f"  Status: {ticket.get('Status', 'Unknown')}, Priority: {ticket.get('Priority', 'Unknown')}\n"
            results += f"  Assignee: {ticket.get('Assignee', 'Unassigned')}\n\n"
        
        if len(project_tickets) > 10:
            results += f"... and {len(project_tickets) - 10} more tickets for this project.\n"
        
        # Add project statistics
        results += f"\n**Project Statistics:**\n"
        results += f"- Total tickets: {len(project_tickets)}\n"
        
        return results
    
    def _get_assignee_tickets(self, assignee: str) -> str:
        """Get tickets by assignee."""
        if self.data_processor.processed_df is None:
            return "Dataset not loaded."
        
        # Filter tickets by assignee
        assignee_tickets = self.data_processor.processed_df[
            self.data_processor.processed_df['Assignee'].str.contains(assignee, case=False, na=False)
        ]
        
        if len(assignee_tickets) == 0:
            return f"No tickets found assigned to '{assignee}' in the dataset."
        
        results = f"Found {len(assignee_tickets)} tickets assigned to '{assignee}' in the dataset:\n\n"
        
        # Show first 10 tickets
        for _, ticket in assignee_tickets.head(10).iterrows():
            results += f"- **#{ticket.get('#', 'N/A')}**: {ticket.get('Subject', 'No subject')}\n"
            results += f"  Status: {ticket.get('Status', 'Unknown')}, Priority: {ticket.get('Priority', 'Unknown')}\n"
            results += f"  Created: {ticket.get('Created', 'Unknown')}\n\n"
        
        if len(assignee_tickets) > 10:
            results += f"... and {len(assignee_tickets) - 10} more tickets assigned to {assignee}.\n"
        
        return results
    
    def analyze_query(self, user_query: str) -> str:
        """Analyze a user query and provide dataset-only response."""
        
        # Get dataset context
        dataset_context = self._get_dataset_context()
        
        # Check for specific data requests
        query_lower = user_query.lower()
        
        # Handle specific queries with data
        if "urgent" in query_lower and ("ticket" in query_lower or "show" in query_lower):
            return self._get_priority_tickets("Urgent")
        
        elif "immediate" in query_lower and ("ticket" in query_lower or "show" in query_lower):
            return self._get_priority_tickets("Immediate")
        
        elif "new" in query_lower and ("ticket" in query_lower or "status" in query_lower):
            return self._get_status_tickets("New")
        
        elif "payment" in query_lower or "duplicate" in query_lower:
            return self._search_tickets("payment")
        
        elif "currency" in query_lower:
            return self._search_tickets("currency")
        
        elif "reservation" in query_lower:
            return self._search_tickets("reservation")
        
        elif "project" in query_lower or "aventura" in query_lower:
            return self._get_project_tickets("Aventura")
        
        elif "assignee" in query_lower or any(name in query_lower for name in ["john", "jane", "support", "admin"]):
            # Extract assignee name if present
            import re
            assignee_match = re.search(r'assignee[:\s]+([^\s,]+)', user_query, re.IGNORECASE)
            if assignee_match:
                assignee = assignee_match.group(1)
                return self._get_assignee_tickets(assignee)
            else:
                return "Please specify an assignee name (e.g., 'Show tickets assigned to John')"
        
        elif "ticket #" in query_lower or "details" in query_lower:
            # Extract ticket number if present
            import re
            ticket_match = re.search(r'#?(\d+)', user_query)
            if ticket_match:
                ticket_id = int(ticket_match.group(1))
                return self._get_ticket_details(ticket_id)
            else:
                return "Please specify a ticket number (e.g., 'Show details for ticket #14398')"
        
        elif any(word in query_lower for word in ["how many", "count", "total", "number"]):
            analysis = self.data_processor.analyze_patterns()
            return f"""
**Dataset Statistics:**
- Total tickets in dataset: {analysis.get('total_tickets', 0)}
- Urgent tickets: {analysis.get('urgent_tickets', 0)}
- New tickets: {analysis.get('new_tickets', 0)}
- Closed tickets: {analysis.get('closed_tickets', 0)}
- Status breakdown: {analysis.get('status_distribution', {})}
- Priority breakdown: {analysis.get('priority_distribution', {})}
"""
        
        # Get vector context for better responses
        vector_context = ""
        try:
            if self.vector_store.is_built:
                vector_context = self.vector_store.get_context_for_query(user_query, max_tickets=3)
        except Exception as e:
            print(f"Vector search error: {e}")
        
        # For general questions, use LLM with strict dataset-only prompt + vector context
        system_prompt = f"""You are a data analyst for support tickets. You ONLY provide information based on the specific dataset provided below.

STRICT RULES:
- ONLY answer using the dataset information provided
- NEVER provide general advice, best practices, or external knowledge
- If asked about something not in the dataset, say "This information is not available in the current dataset"
- Always reference that your response is based on "the dataset" or "these tickets"
- Use the relevant similar tickets to provide more specific context when available

{dataset_context}

{vector_context}

Base your response ONLY on this data. Do not provide general advice."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Based only on the dataset provided above, answer this question: {user_query}")
        ]
        
        try:
            response = self.llm.invoke(messages)
            return str(response.content) if response.content else "No response generated"
        except Exception as e:
            return f"Error analyzing dataset: {e}"
    
    def get_quick_stats(self) -> Dict[str, Any]:
        """Get quick statistics for the dashboard."""
        analysis = self.data_processor.analyze_patterns()
        vector_stats = self.vector_store.get_stats()
        
        analysis['vector_store'] = vector_stats
        return analysis
    
    def search_similar_tickets(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for tickets similar to the query using vector search."""
        try:
            return self.vector_store.search_similar_tickets(query, k=max_results)
        except Exception as e:
            print(f"Vector search error: {e}")
            return [] 