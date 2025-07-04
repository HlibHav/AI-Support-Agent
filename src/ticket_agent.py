import os
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# Phoenix setup moved to global scope in streamlit_app.py
# The @trace decorator is no longer needed with OpenInference instrumentation
def trace(func):
    """Placeholder trace decorator - actual tracing handled by OpenInference."""
    return func

from src.data_processor import TicketDataProcessor


class AgentState(TypedDict):
    """State of the ticket analysis agent."""
    messages: Annotated[list, add_messages]
    data_processor: TicketDataProcessor
    current_analysis: Optional[Dict[str, Any]]
    user_query: str
    response: str


class TicketAnalysisAgent:
    """LangGraph-based agent for analyzing support tickets."""
    
    def __init__(self, csv_path: str, gemini_api_key: str):
        self.csv_path = csv_path
        self.data_processor = TicketDataProcessor(csv_path)
        
        # Initialize LLM
        os.environ["GOOGLE_API_KEY"] = gemini_api_key
        self.llm = ChatGoogleGenerativeAI(
            model="models/gemini-1.5-flash",
            temperature=0.1
        )
        
        # Create tools
        self.tools = [
            self.analyze_ticket_patterns,
            self.search_tickets_tool,
            self.get_priority_tickets_tool,
            self.get_ticket_details_tool,
            self.cluster_tickets_tool,
            self.get_status_summary_tool,
            self.get_dataset_info_tool
        ]
        
        # Initialize the graph
        self.graph = self._create_graph()
        
        # Load and process data
        self._initialize_data()
    

    
    def _initialize_data(self):
        """Load and process the ticket data."""
        print("Loading and processing ticket data...")
        self.data_processor.load_data()
        self.data_processor.clean_data()
        print("Data processing complete")
    
    @tool
    def analyze_ticket_patterns(self) -> str:
        """Analyze overall patterns in support tickets."""
        analysis = self.data_processor.analyze_patterns()
        
        summary = f"""
## Support Ticket Analysis Summary

**Overall Statistics:**
- Total Tickets: {analysis.get('total_tickets', 0)}
- Average Days Open: {analysis.get('avg_days_open', 0):.1f}
- Urgent Tickets: {analysis.get('urgent_tickets', 0)}
- New Tickets: {analysis.get('new_tickets', 0)}
- Closed Tickets: {analysis.get('closed_tickets', 0)}

**Status Distribution:**
{json.dumps(analysis.get('status_distribution', {}), indent=2)}

**Priority Distribution:**
{json.dumps(analysis.get('priority_distribution', {}), indent=2)}

**Project Distribution:**
{json.dumps(analysis.get('project_distribution', {}), indent=2)}

**Top Assignees:**
{json.dumps(analysis.get('top_assignees', {}), indent=2)}
        """
        
        return summary.strip()
    
    @tool
    def search_tickets_tool(self, query: str, limit: int = 5) -> str:
        """Search for tickets containing specific text."""
        tickets = self.data_processor.search_tickets(query, limit)
        
        if not tickets:
            return f"No tickets found matching '{query}'"
        
        results = f"Found {len(tickets)} tickets matching '{query}':\n\n"
        
        for i, ticket in enumerate(tickets, 1):
            results += f"""
**Ticket #{ticket.get('#', 'N/A')}** - {ticket.get('Subject', 'No subject')}
- Status: {ticket.get('Status', 'Unknown')}
- Priority: {ticket.get('Priority', 'Unknown')}
- Assignee: {ticket.get('Assignee', 'Unassigned')}
- Created: {ticket.get('Created', 'Unknown')}

"""
        
        return results.strip()
    
    @tool
    def get_priority_tickets_tool(self, priority: str = "Urgent") -> str:
        """Get tickets by priority level (Urgent, High, Normal, Low, Immediate)."""
        tickets = self.data_processor.get_priority_tickets(priority)
        
        if not tickets:
            return f"No {priority} priority tickets found"
        
        results = f"Found {len(tickets)} {priority} priority tickets:\n\n"
        
        for ticket in tickets[:10]:  # Limit to first 10
            results += f"""
**Ticket #{ticket.get('#', 'N/A')}** - {ticket.get('Subject', 'No subject')}
- Status: {ticket.get('Status', 'Unknown')}
- Assignee: {ticket.get('Assignee', 'Unassigned')}
- Created: {ticket.get('Created', 'Unknown')}
- Description: {str(ticket.get('Description', ''))[:200]}...

"""
        
        return results.strip()
    
    @tool
    def get_ticket_details_tool(self, ticket_id: int) -> str:
        """Get detailed information about a specific ticket."""
        ticket = self.data_processor.get_ticket_by_id(ticket_id)
        
        if not ticket:
            return f"Ticket #{ticket_id} not found"
        
        details = f"""
**Ticket #{ticket.get('#', 'N/A')} Details:**

**Subject:** {ticket.get('Subject', 'No subject')}
**Status:** {ticket.get('Status', 'Unknown')}
**Priority:** {ticket.get('Priority', 'Unknown')}
**Project:** {ticket.get('Project', 'Unknown')}
**Tracker:** {ticket.get('Tracker', 'Unknown')}
**Author:** {ticket.get('Author', 'Unknown')}
**Assignee:** {ticket.get('Assignee', 'Unassigned')}
**Created:** {ticket.get('Created', 'Unknown')}
**Updated:** {ticket.get('Updated', 'Unknown')}

**Description:**
{ticket.get('Description', 'No description')}

**Last Notes:**
{ticket.get('Last notes', 'No notes')}
        """
        
        return details.strip()
    
    @tool
    def cluster_tickets_tool(self, n_clusters: int = 5) -> str:
        """Cluster tickets by content similarity to identify common themes."""
        clusters = self.data_processor.cluster_tickets(n_clusters)
        
        if 'error' in clusters:
            return f"Clustering failed: {clusters['error']}"
        
        results = f"Ticket Clustering Analysis (k={n_clusters}):\n\n"
        
        for cluster_name, cluster_info in clusters.items():
            results += f"""
**{cluster_name.replace('_', ' ').title()}:**
- Size: {cluster_info.get('size', 0)} tickets
- Top Terms: {', '.join(cluster_info.get('top_terms', [])[:5])}
- Priority Distribution: {json.dumps(cluster_info.get('priority_dist', {}), indent=2)}
- Status Distribution: {json.dumps(cluster_info.get('status_dist', {}), indent=2)}

"""
        
        return results.strip()
    
    @tool
    def get_status_summary_tool(self, status: str) -> str:
        """Get summary of tickets by status (New, Feedback, Solved, etc.)."""
        tickets = self.data_processor.get_tickets_by_status(status)
        
        if not tickets:
            return f"No tickets found with status '{status}'"
        
        results = f"Found {len(tickets)} tickets with status '{status}':\n\n"
        
        # Show summary statistics
        if tickets:
            priorities = {}
            assignees = {}
            for ticket in tickets:
                priority = ticket.get('Priority', 'Unknown')
                assignee = ticket.get('Assignee', 'Unassigned')
                priorities[priority] = priorities.get(priority, 0) + 1
                assignees[assignee] = assignees.get(assignee, 0) + 1
            
            results += f"**Priority Breakdown:** {json.dumps(priorities, indent=2)}\n"
            results += f"**Assignee Breakdown:** {json.dumps(dict(list(assignees.items())[:5]), indent=2)}\n\n"
        
        # Show recent tickets
        results += "**Recent Tickets:**\n"
        for ticket in tickets[:5]:
            results += f"""
- **#{ticket.get('#', 'N/A')}**: {ticket.get('Subject', 'No subject')}
  Assignee: {ticket.get('Assignee', 'Unassigned')}, Priority: {ticket.get('Priority', 'Unknown')}

"""
        
        return results.strip()
    
    @tool
    def get_dataset_info_tool(self) -> str:
        """Get information about the dataset scope and limitations."""
        return """
**Dataset Information:**
- This analysis is based on your specific support ticket dataset only
- Contains 420 support tickets from your system
- Includes tickets with various statuses: New, Feedback, Solved, etc.
- Priority levels: Immediate, Urgent, High, Normal, Low
- Projects: Mainly Aventura project tickets
- Time period: Various dates from your ticket system

**What I CAN analyze:**
- Ticket counts, distributions, and patterns from this dataset
- Search and filter tickets by any field
- Identify trends and clusters in your specific data
- Provide statistics about assignees, priorities, status, etc.

**What I CANNOT provide:**
- General support best practices or industry advice
- Information not contained in your ticket dataset
- Recommendations based on external knowledge
- Comparisons with other companies or systems

All my responses are based solely on analyzing your ticket data.
        """
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow."""
        
        def should_use_tools(state: AgentState) -> str:
            """Decide whether to use tools based on the last message."""
            last_message = state["messages"][-1]
            
            # If the last message has tool calls, execute them
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            
            # Otherwise, generate the final response
            return "generate"
        
        def call_model(state: AgentState) -> AgentState:
            """Call the LLM with tools."""
            system_prompt = """You are a support ticket data analyst. You ONLY provide information based on the specific support ticket dataset you have access to.

STRICT RULES:
- ONLY answer questions using data from the support ticket dataset
- NEVER provide general advice, industry knowledge, or information not in the dataset
- ALWAYS use the provided tools to gather information from the data
- If information is not available in the dataset, clearly state "This information is not available in the current dataset"
- Base ALL responses on actual data from the tickets

Available data sources:
- Support ticket details (ID, subject, description, status, priority, assignee, dates, etc.)
- You can search, filter, analyze, and cluster this specific ticket data
- You can provide statistics and patterns from this dataset only

Response format:
1. ALWAYS use tools first to gather relevant data
2. Only report what you find in the actual dataset
3. Include specific ticket numbers, counts, and data points
4. If asked about something not in the data, say so explicitly
5. Never make assumptions or provide general recommendations not based on the data

Remember: You are analyzing THIS specific support ticket dataset only, not providing general support advice."""

            messages = [SystemMessage(content=system_prompt)] + state["messages"]
            
            # Bind tools to the model
            model_with_tools = self.llm.bind_tools(self.tools)
            response = model_with_tools.invoke(messages)
            
            return {"messages": [response]}
        
        def generate_final_response(state: AgentState) -> AgentState:
            """Generate final response without tools."""
            response = self.llm.invoke(state["messages"])
            return {"messages": [response]}
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("generate", generate_final_response)
        
        # Add edges
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            should_use_tools,
            {
                "tools": "tools",
                "generate": "generate"
            }
        )
        workflow.add_edge("tools", "agent")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
    
    @trace
    def analyze_query(self, user_query: str) -> str:
        """Analyze a user query about support tickets."""
        
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "data_processor": self.data_processor,
            "current_analysis": None,
            "user_query": user_query,
            "response": ""
        }
        
        # Run the graph
        result = self.graph.invoke(initial_state)
        
        # Get the final response
        final_message = result["messages"][-1]
        if hasattr(final_message, 'content'):
            return final_message.content
        else:
            return str(final_message)
    
    def get_quick_stats(self) -> Dict[str, Any]:
        """Get quick statistics for the dashboard."""
        return self.data_processor.analyze_patterns() 