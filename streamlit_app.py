import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path
import time
import warnings

# Suppress SSL warnings
warnings.filterwarnings("ignore", message="urllib3.*")
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

# Global Phoenix setup for observability
phoenix_available = False
phoenix_error = None

try:
    import phoenix as phoenix_app
    from phoenix.otel import register
    from openinference.instrumentation.langchain import LangChainInstrumentor
    
    # Start Phoenix globally
    phoenix_app.launch_app()
    
    # Register OpenTelemetry tracer and instrument LangChain
    tracer_provider = register()
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    
    phoenix_available = True
    print("✅ Phoenix observability initialized globally")
    
except ImportError as e:
    phoenix_error = f"Phoenix not available: {e}"
    print(f"⚠️  Phoenix not available: {e}")
    
except Exception as e:
    phoenix_error = f"Phoenix initialization failed: {e}"
    print(f"⚠️  Phoenix initialization failed: {e}")

from src.simple_ticket_agent import SimpleTicketAgent
from src.enhanced_ticket_agent import EnhancedTicketAgent
from src.data_processor import TicketDataProcessor
from src.knowledge_vector_store import KnowledgeVectorStore
from src.document_processor import DocumentProcessor
from src.data_only_prompts import PROMPT_SUGGESTIONS, validate_dataset_query
from src.redmine_service import RedmineService, RedmineConfig, RedmineAuthType, RedmineTicketManager
from src.database_manager import DatabaseManager


# Page configuration
st.set_page_config(
    page_title="AI Support Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 2rem;
    }
    .redmine-section {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .metric-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    .user-message {
        background-color: #f0f9ff;
        border-left-color: #3b82f6;
    }
    .agent-message {
        background-color: #f0fdf4;
        border-left-color: #10b981;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'tickets_df' not in st.session_state:
    st.session_state.tickets_df = None
if 'simple_agent' not in st.session_state:
    st.session_state.simple_agent = None
if 'enhanced_agent' not in st.session_state:
    st.session_state.enhanced_agent = None
if 'knowledge_base_built' not in st.session_state:
    st.session_state.knowledge_base_built = False
if 'redmine_service' not in st.session_state:
    st.session_state.redmine_service = None
if 'redmine_connected' not in st.session_state:
    st.session_state.redmine_connected = False
if 'database_manager' not in st.session_state:
    st.session_state.database_manager = None
if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False


@st.cache_data(ttl=600)
def load_data():
    """Load and process ticket data."""
    try:
        # Check if data file exists
        if not os.path.exists("sample_tickets_template.csv"):
            st.error("Data file 'sample_tickets_template.csv' not found. Please make sure the file exists in the project directory.")
            return None
            
        processor = TicketDataProcessor("sample_tickets_template.csv")
        
        # Load data with better error handling
        df = processor.load_data()
        if df is None or df.empty:
            st.error("Failed to load data or data file is empty.")
            return None
        
        # Clean data
        processed_df = processor.clean_data()
        if processed_df is None or processed_df.empty:
            st.error("Failed to process data.")
            return None
        
        # --- COLUMN RENAME PATCH FOR UI COMPATIBILITY ---
        # Ensure columns match expected UI names
        rename_map = {
            ' #': '#',
            'Subject': 'Subject',
            'Status': 'Status',
            'Priority': 'Priority',
            'Project': 'Project',
            'Assignee': 'Assignee',
            'Created': 'Created',
        }
        # Remove leading/trailing spaces from columns
        processed_df.columns = [c.strip() for c in processed_df.columns]
        processed_df = processed_df.rename(columns=rename_map)
        processor.processed_df = processed_df
        st.success(f"✅ Successfully loaded {len(processed_df)} tickets")
        return processor
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.error("Please check that your data file is properly formatted and accessible.")
        return None


@st.cache_resource
def initialize_simple_agent():
    """Initialize the simple ticket agent."""
    gemini_key = st.session_state.get('gemini_api_key', '')
    if not gemini_key:
        return None
    
    try:
        with st.spinner("Building vector index for enhanced context..."):
            agent = SimpleTicketAgent("sample_tickets_template.csv", gemini_key)
            st.success("✅ Vector index ready for context-aware responses")
            return agent
    except Exception as e:
        st.error(f"Failed to initialize simple agent: {str(e)}")
        st.error("Please check your API key and try again.")
        return None


def build_knowledge_base():
    """Check knowledge base status and provide user guidance."""
    if st.session_state.knowledge_base_built:
        return
    
    st.info("🔄 Checking knowledge base status...")
    
    # Check if knowledge base files exist
    has_vector_index = os.path.exists("knowledge_vector_index.faiss") and os.path.exists("knowledge_documents.pkl")
    has_text_search = os.path.exists("knowledge_text_search.marker")
    
    if has_vector_index:
        st.success("✅ Vector-based knowledge base found!")
        st.session_state.knowledge_base_built = True
        return
    elif has_text_search:
        st.success("✅ Text-search knowledge base found!")
        st.session_state.knowledge_base_built = True
        return
    else:
        st.warning("⚠️ Knowledge base not found!")
        st.info("""
        **To build the knowledge base, please run one of these commands in your terminal:**
        
        1. **For text-search mode (recommended, works on any system):**
           ```bash
           python build_text_search_knowledge.py
           ```
        
        2. **For vector-search mode (requires more memory):**
           ```bash
           python build_knowledge_base_robust.py
           ```
        
        3. **For ultra-lightweight approach:**
           ```bash
           python build_knowledge_base.py
           ```
        
        **Note:** The knowledge base will be built from the documentation files in your Knowledge directory.
        Once built, you'll have access to both ticket analysis and comprehensive system documentation.
        """)
        
        if st.button("🔄 Refresh Status"):
            st.rerun()


def create_redmine_configuration():
    """Create Redmine configuration section."""
    st.markdown("### 🔗 Redmine Integration")
    
    with st.expander("Configure Redmine Connection", expanded=not st.session_state.redmine_connected):
        col1, col2 = st.columns(2)
        
        with col1:
            redmine_url = st.text_input(
                "Redmine URL", 
                placeholder="https://your-redmine.example.com",
                help="Base URL of your Redmine instance"
            )
            
            auth_type = st.selectbox(
                "Authentication Type",
                ["API Key", "Basic Auth"],
                help="Choose authentication method"
            )
        
        with col2:
            if auth_type == "API Key":
                api_key = st.text_input(
                    "API Key", 
                    type="password",
                    help="Your Redmine API key (from My Account page)"
                )
                username = password = None
            else:
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                api_key = None
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔌 Connect to Redmine"):
                if redmine_url:
                    try:
                        config = RedmineConfig(
                            base_url=redmine_url.rstrip('/'),
                            api_key=api_key,
                            username=username,
                            password=password,
                            auth_type=RedmineAuthType.API_KEY if auth_type == "API Key" else RedmineAuthType.BASIC_AUTH
                        )
                        
                        service = RedmineService(config)
                        
                        # Test connection
                        if service.test_connection():
                            st.session_state.redmine_service = service
                            st.session_state.redmine_connected = True
                            st.success("✅ Connected to Redmine successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to connect to Redmine. Please check your credentials.")
                            
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")
                else:
                    st.error("Please enter a Redmine URL")
        
        with col2:
            if st.button("🔧 Test Connection") and st.session_state.redmine_service:
                try:
                    if st.session_state.redmine_service.test_connection():
                        st.success("✅ Connection is working!")
                    else:
                        st.error("❌ Connection failed!")
                except Exception as e:
                    st.error(f"❌ Test failed: {str(e)}")
        
        with col3:
            if st.button("🔌 Disconnect") and st.session_state.redmine_connected:
                st.session_state.redmine_service = None
                st.session_state.redmine_connected = False
                st.success("Disconnected from Redmine")
                st.rerun()
    
    # Show connection status
    if st.session_state.redmine_connected:
        st.markdown(
            '<div class="redmine-section">🟢 Connected to Redmine - Ready to update tickets</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="redmine-section">🔴 Not connected to Redmine - Configure above to enable ticket updates</div>',
            unsafe_allow_html=True
        )


def create_ticket_management_interface():
    """Create ticket management interface with Redmine integration."""
    if not st.session_state.redmine_connected:
        st.info("🔗 Connect to Redmine to manage tickets")
        return
    
    st.markdown("### 🎫 Ticket Management")
    
    try:
        service = st.session_state.redmine_service
        
        # Ticket actions
        action = st.selectbox(
            "Action",
            ["View Ticket", "Update Ticket", "Add Note", "Change Status", "Assign Ticket"],
            key="ticket_action"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            ticket_id = st.number_input("Ticket ID", min_value=1, step=1)
        
        with col2:
            if action == "View Ticket":
                if st.button("📋 Get Ticket Details"):
                    try:
                        ticket = service.get_issue(ticket_id, include=["journals", "attachments"])
                        issue = ticket.get("issue", {})
                        
                        st.json(issue)
                        
                    except Exception as e:
                        st.error(f"Error fetching ticket: {str(e)}")
            
            elif action == "Add Note":
                note_text = st.text_area("Note", placeholder="Enter your note here...")
                private_note = st.checkbox("Private note")
                
                if st.button("📝 Add Note"):
                    try:
                        result = service.add_issue_note(ticket_id, note_text, private_note)
                        st.success(f"✅ Note added to ticket #{ticket_id}")
                        st.json(result)
                    except Exception as e:
                        st.error(f"Error adding note: {str(e)}")
            
            elif action == "Change Status":
                # Get available statuses
                try:
                    statuses = service.get_issue_statuses()
                    status_options = {
                        status["name"]: status["id"] 
                        for status in statuses.get("issue_statuses", [])
                    }
                    
                    selected_status = st.selectbox("New Status", list(status_options.keys()))
                    status_note = st.text_area("Status Change Note (optional)")
                    
                    if st.button("🔄 Update Status"):
                        try:
                            result = service.update_issue_status(
                                ticket_id, 
                                status_options[selected_status], 
                                status_note if status_note else None
                            )
                            st.success(f"✅ Status updated for ticket #{ticket_id}")
                            st.json(result)
                        except Exception as e:
                            st.error(f"Error updating status: {str(e)}")
                            
                except Exception as e:
                    st.error(f"Error loading statuses: {str(e)}")
            
            elif action == "Assign Ticket":
                # Get available users (requires admin privileges)
                try:
                    users = service.get_users()
                    user_options = {
                        f"{user['firstname']} {user['lastname']}": user['id']
                        for user in users.get("users", [])
                    }
                    
                    selected_user = st.selectbox("Assign to", list(user_options.keys()))
                    assign_note = st.text_area("Assignment Note (optional)")
                    
                    if st.button("👤 Assign Ticket"):
                        try:
                            result = service.assign_issue(
                                ticket_id,
                                user_options[selected_user],
                                assign_note if assign_note else None
                            )
                            st.success(f"✅ Ticket #{ticket_id} assigned to {selected_user}")
                            st.json(result)
                        except Exception as e:
                            st.error(f"Error assigning ticket: {str(e)}")
                            
                except Exception as e:
                    st.info("User assignment requires admin privileges")
                    
                    # Manual user ID input as fallback
                    user_id = st.number_input("User ID", min_value=1, step=1)
                    assign_note = st.text_area("Assignment Note (optional)")
                    
                    if st.button("👤 Assign by ID"):
                        try:
                            result = service.assign_issue(
                                ticket_id,
                                user_id,
                                assign_note if assign_note else None
                            )
                            st.success(f"✅ Ticket #{ticket_id} assigned to user #{user_id}")
                            st.json(result)
                        except Exception as e:
                            st.error(f"Error assigning ticket: {str(e)}")
            
            elif action == "Update Ticket":
                st.markdown("**Custom Update**")
                
                # Allow custom field updates
                update_fields = {}
                
                col3, col4 = st.columns(2)
                
                with col3:
                    if st.checkbox("Update Priority"):
                        try:
                            priorities = service.get_priorities()
                            priority_options = {
                                priority["name"]: priority["id"] 
                                for priority in priorities.get("issue_priorities", [])
                            }
                            selected_priority = st.selectbox("Priority", list(priority_options.keys()))
                            update_fields["priority_id"] = priority_options[selected_priority]
                        except Exception as e:
                            st.error(f"Error loading priorities: {str(e)}")
                    
                    if st.checkbox("Update Subject"):
                        new_subject = st.text_input("New Subject")
                        if new_subject:
                            update_fields["subject"] = new_subject
                
                with col4:
                    if st.checkbox("Update Description"):
                        new_description = st.text_area("New Description")
                        if new_description:
                            update_fields["description"] = new_description
                
                update_note = st.text_area("Update Note")
                if update_note:
                    update_fields["notes"] = update_note
                
                if st.button("🔄 Update Ticket") and update_fields:
                    try:
                        result = service.update_issue(ticket_id, update_fields)
                        st.success(f"✅ Ticket #{ticket_id} updated successfully")
                        st.json(result)
                    except Exception as e:
                        st.error(f"Error updating ticket: {str(e)}")
        
        # Bulk operations
        st.markdown("### 📦 Bulk Operations")
        
        with st.expander("Bulk Ticket Updates"):
            bulk_action = st.selectbox(
                "Bulk Action",
                ["Bulk Status Change", "Bulk Assignment", "Bulk Note Addition"],
                key="bulk_action"
            )
            
            ticket_ids = st.text_input(
                "Ticket IDs (comma-separated)",
                placeholder="1,2,3,4,5"
            )
            
            if bulk_action == "Bulk Status Change":
                try:
                    statuses = service.get_issue_statuses()
                    status_options = {
                        status["name"]: status["id"] 
                        for status in statuses.get("issue_statuses", [])
                    }
                    
                    bulk_status = st.selectbox("Status", list(status_options.keys()), key="bulk_status")
                    bulk_note = st.text_area("Bulk Note", key="bulk_note")
                    
                    if st.button("🔄 Bulk Update Status"):
                        try:
                            ticket_list = [int(t.strip()) for t in ticket_ids.split(",") if t.strip()]
                            updates = []
                            
                            for tid in ticket_list:
                                update_data = {
                                    "issue_id": tid,
                                    "updates": {
                                        "status_id": status_options[bulk_status],
                                        "notes": bulk_note if bulk_note else f"Bulk status update to {bulk_status}"
                                    }
                                }
                                updates.append(update_data)
                            
                            manager = RedmineTicketManager(service)
                            results = manager.bulk_update_tickets(updates)
                            
                            success_count = sum(1 for r in results if r.get("success"))
                            st.success(f"✅ Updated {success_count}/{len(results)} tickets")
                            
                            with st.expander("View Results"):
                                st.json(results)
                                
                        except Exception as e:
                            st.error(f"Bulk update error: {str(e)}")
                            
                except Exception as e:
                    st.error(f"Error loading statuses: {str(e)}")
    
    except Exception as e:
        st.error(f"Error with Redmine service: {str(e)}")
        st.session_state.redmine_connected = False


def initialize_enhanced_agent():
    """Initialize the enhanced ticket agent."""
    gemini_key = st.session_state.get('gemini_api_key', '')
    if not gemini_key:
        return None
    
    try:
        # Initialize agent (this should be fast now)
        agent = EnhancedTicketAgent(gemini_key)
        
        # Show knowledge base status
        if agent.knowledge_ready:
            st.success("✅ Enhanced agent ready with knowledge base!")
        else:
            st.info("ℹ️ Enhanced agent ready. Knowledge base will be built on first use.")
        
        return agent
    except Exception as e:
        st.error(f"Error initializing enhanced agent: {e}")
        st.warning("💡 Try refreshing the page or check your API key")
        return None


def create_dashboard(processor):
    """Create the main dashboard with key metrics and visualizations."""
    st.markdown('<div class="main-header">🎫 Support Ticket Analysis Dashboard</div>', 
                unsafe_allow_html=True)
    
    # Get analysis data
    analysis = processor.analyze_patterns()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Tickets",
            analysis.get('total_tickets', 0),
            delta=f"{analysis.get('recent_tickets', 0)} recent"
        )
    
    with col2:
        st.metric(
            "Urgent Tickets",
            analysis.get('urgent_tickets', 0),
            delta="High priority"
        )
    
    with col3:
        st.metric(
            "New Tickets",
            analysis.get('new_tickets', 0),
            delta="Needs attention"
        )
    
    with col4:
        st.metric(
            "Avg Days Open",
            f"{analysis.get('avg_days_open', 0):.1f}",
            delta="Processing time"
        )
    
    # Visualizations and Tables Section - Moved to top
    st.markdown("---")
    st.markdown("### 📊 Visualizations & Data Tables")
    
    # Charts in a 2-column layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Status Distribution")
        status_data = analysis.get('status_distribution', {})
        if status_data:
            fig = px.pie(
                values=list(status_data.values()),
                names=list(status_data.keys()),
                title="Tickets by Status"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⚡ Priority Distribution")
        priority_data = analysis.get('priority_distribution', {})
        if priority_data:
            fig = px.bar(
                x=list(priority_data.values()),
                y=list(priority_data.keys()),
                orientation='h',
                title="Tickets by Priority",
                color=list(priority_data.values()),
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Top assignees table - Full width
    st.subheader("👥 Top Assignees")
    assignee_data = analysis.get('top_assignees', {})
    if assignee_data:
        assignee_df = pd.DataFrame.from_dict(
            assignee_data, 
            orient='index'
        ).reset_index().rename(columns={'index': 'Assignee', 0: 'Tickets'})
        st.dataframe(assignee_df, use_container_width=True)
    else:
        st.info("No assignee data available")
    
    # Additional visualizations section
    st.markdown("---")
    st.markdown("### 📈 Additional Insights")
    
    # Project and Tracker distribution in a 2-column layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏢 Project Distribution")
        project_data = analysis.get('project_distribution', {})
        if project_data:
            fig = px.pie(
                values=list(project_data.values()),
                names=list(project_data.keys()),
                title="Tickets by Project"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Tracker Distribution")
        tracker_data = analysis.get('tracker_distribution', {})
        if tracker_data:
            fig = px.bar(
                x=list(tracker_data.keys()),
                y=list(tracker_data.values()),
                title="Tickets by Tracker",
                color=list(tracker_data.values()),
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)


def create_enhanced_chat_interface(enhanced_agent):
    """Create the enhanced chat interface with knowledge base support."""
    st.markdown('<div class="main-header">🧠 Enhanced Chat with Knowledge Base</div>', 
                unsafe_allow_html=True)
    
    # Information box about enhanced capabilities
    st.info("🚀 **Enhanced Agent**: This agent has access to both your ticket data AND the comprehensive knowledge base from your documentation. It can help with both specific ticket issues and general system knowledge.")
    
    st.info("🗣️ **Natural Conversation**: The agent responds like a real person! It gives detailed, step-by-step instructions and avoids robotic language. Ask questions naturally and get helpful, conversational responses.")
    
    # Knowledge base stats
    stats = None
    if enhanced_agent and enhanced_agent.is_ready():
        stats = enhanced_agent.get_stats()
    knowledge_docs = 0
    if stats and 'knowledge' in stats:
        knowledge_docs = stats['knowledge'].get('total_documents', 0)
    if (not knowledge_docs) and os.path.exists('knowledge_stats.json'):
        with open('knowledge_stats.json', 'r') as f:
            file_stats = json.load(f)
            knowledge_docs = file_stats.get('total_documents', 0)
    if stats and 'tickets' in stats:
        ticket_count = stats['tickets'].get('total_tickets', 0)
    else:
        ticket_count = 0
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Tickets", ticket_count)
    with col2:
        st.metric("📚 Knowledge Documents", knowledge_docs)
    with col3:
        st.metric("🔍 Total Searchable Items", knowledge_docs)
    
    # Query type selector
    query_type = st.selectbox(
        "🎯 Query Type",
        ["Auto-detect", "Ticket Query", "Knowledge Query", "Both"],
        help="Select what type of information you're looking for"
    )
    
    # Map display names to internal values
    query_type_map = {
        "Auto-detect": None,
        "Ticket Query": "ticket",
        "Knowledge Query": "knowledge", 
        "Both": "both"
    }
    
    # Category filter for knowledge queries
    category_filter = None
    if query_type in ["Knowledge Query", "Both"]:
        categories = enhanced_agent.get_knowledge_categories() if enhanced_agent else []
        if categories:
            category_filter = st.selectbox(
                "📂 Knowledge Category (Optional)",
                ["All Categories"] + categories,
                help="Filter knowledge base by category"
            )
            if category_filter == "All Categories":
                category_filter = None
    
    # Initialize chat history for enhanced agent
    if "enhanced_messages" not in st.session_state:
        st.session_state.enhanced_messages = []
    
    # Chat input
    if prompt := st.chat_input("Ask me about tickets or system knowledge..."):
        # Add user message
        st.session_state.enhanced_messages.append({"role": "user", "content": prompt})
        
        # Get response from enhanced agent
        if enhanced_agent:
            # Check if this might trigger knowledge base building
            query_type_val = query_type_map[query_type]
            needs_knowledge = query_type_val in ['knowledge', 'both'] or query_type_val is None
            
            if needs_knowledge and not enhanced_agent.knowledge_ready:
                with st.spinner("Building knowledge base for first time (this may take a few minutes)..."):
                    response = enhanced_agent.generate_response(prompt, query_type=query_type_val)
            else:
                with st.spinner("Thinking..."):
                    response = enhanced_agent.generate_response(prompt, query_type=query_type_val)
            
            st.session_state.enhanced_messages.append({"role": "assistant", "content": response})
        else:
            st.session_state.enhanced_messages.append({
                "role": "assistant", 
                "content": "Enhanced agent is not available. Please check your API key and try again."
            })
    
    # Display chat history
    for message in st.session_state.enhanced_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def create_knowledge_base_page(enhanced_agent):
    """Create the knowledge base exploration page."""
    st.markdown('<div class="main-header">📚 Knowledge Base Explorer</div>', 
                unsafe_allow_html=True)
    
    # --- PATCH: Always show correct stats, even if knowledge store is empty ---
    stats = None
    if enhanced_agent and hasattr(enhanced_agent, 'get_stats'):
        stats = enhanced_agent.get_stats()
    # If stats are nested under 'knowledge', flatten them
    if stats and 'knowledge' in stats:
        stats = stats['knowledge']
    if (not stats or not stats.get('total_documents')) and os.path.exists('knowledge_stats.json'):
        with open('knowledge_stats.json', 'r') as f:
            stats = json.load(f)
    knowledge_stats = stats if stats else {}
    
    st.subheader("📊 Knowledge Base Statistics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 Total Documents", knowledge_stats.get('total_documents', 0))
    with col2:
        st.metric("📝 Total Words", f"{knowledge_stats.get('total_words', 0):,}")
    with col3:
        st.metric("🔤 Total Characters", f"{knowledge_stats.get('total_characters', 0):,}")
    with col4:
        st.metric("📂 Categories", len(knowledge_stats.get('categories', [])))
    
    # Category distribution
    if knowledge_stats.get('categories'):
        st.subheader("📂 Documents by Category")
        categories_list = knowledge_stats.get('categories', [])
        if categories_list and enhanced_agent.knowledge_store and enhanced_agent.knowledge_ready:
            # Count documents per category
            category_counts = {}
            for category in categories_list:
                try:
                    # Try to get documents by category
                    docs_in_category = enhanced_agent.knowledge_store.get_documents_by_category(category)
                    category_counts[category] = len(docs_in_category)
                except Exception as e:
                    # Fallback: count manually from documents if available
                    try:
                        if hasattr(enhanced_agent.knowledge_store, 'documents') and enhanced_agent.knowledge_store.documents:
                            count = sum(1 for doc in enhanced_agent.knowledge_store.documents 
                                      if doc.get('category') == category)
                            category_counts[category] = count
                        else:
                            category_counts[category] = 0
                    except Exception:
                        category_counts[category] = 0
            
            if category_counts and any(count > 0 for count in category_counts.values()):
                fig = px.bar(
                    x=list(category_counts.values()),
                    y=list(category_counts.keys()),
                    orientation='h',
                    title="Documents by Category",
                    color=list(category_counts.values()),
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Category data not available yet. Please build the knowledge base first.")
        else:
            st.info("Category data not available yet. Please build the knowledge base first.")
    
    # Document search
    st.subheader("🔍 Search Knowledge Base")
    search_query = st.text_input("Search documents...", placeholder="Enter search terms")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_category = st.selectbox(
            "Category Filter",
            ["All Categories"] + enhanced_agent.get_knowledge_categories(),
            key="kb_search_category"
        )
    with col2:
        search_limit = st.number_input("Max Results", 1, 20, 10, key="kb_search_limit")
    
    if search_query:
        category_filter = search_category if search_category != "All Categories" else None
        
        with st.spinner("Searching..."):
            results = enhanced_agent.search_knowledge(
                search_query, 
                limit=search_limit,
                category=category_filter
            )
        
        if results:
            st.success(f"Found {len(results)} relevant documents")
            
            for i, doc in enumerate(results, 1):
                with st.expander(f"📄 {doc.get('title', 'Untitled')} (Similarity: {doc.get('similarity_score', 0):.1f}%)"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**Category:** {doc.get('category', 'Unknown')}")
                        st.markdown(f"**File:** {doc.get('filename', 'Unknown')}")
                        st.markdown(f"**Size:** {doc.get('char_count', 0):,} characters")
                    
                    with col2:
                        st.markdown(f"**Similarity:** {doc.get('similarity_score', 0):.1f}%")
                        st.markdown(f"**Words:** {doc.get('word_count', 0):,}")
                    
                    st.markdown("**Content Preview:**")
                    st.text_area(
                        "Document Content",
                        doc.get('text_content', 'No content available')[:1000] + "...",
                        height=200,
                        key=f"doc_content_{i}",
                        disabled=True
                    )
        else:
            st.info("No documents found matching your search criteria.")
    
    # Rebuild index option
    st.subheader("🔧 Maintenance")
    if st.button("🔄 Rebuild Knowledge Base Index", type="secondary"):
        with st.spinner("Rebuilding knowledge base index..."):
            enhanced_agent.rebuild_knowledge_index()
        st.success("Knowledge base index rebuilt successfully!")
        st.rerun()


def create_chat_interface(agent):
    """Create the chat interface for interacting with the agent."""
    st.markdown('<div class="main-header">💬 Chat with Support Ticket Agent</div>', 
                unsafe_allow_html=True)
    
    # Information box about dataset-only responses
    st.info("🎯 **Dataset-Only Analysis**: This agent only provides information based on your specific support ticket data. It won't give general advice or external knowledge.")
    
    # Prompt suggestions
    with st.expander("💡 Example Questions (Click to expand)"):
        col1, col2 = st.columns(2)
        
        for i, category in enumerate(PROMPT_SUGGESTIONS):
            with col1 if i % 2 == 0 else col2:
                st.markdown(f"**{category['category']}**")
                for j, prompt in enumerate(category['prompts']):
                    button_key = f"prompt_{i}_{j}_{hash(prompt)}"
                    if st.button(prompt, key=button_key, use_container_width=True):
                        # Clear any existing prompt input first
                        if 'current_prompt' in st.session_state:
                            del st.session_state.current_prompt
                        
                        # Set the current prompt and trigger processing
                        st.session_state.current_prompt = prompt
                        st.session_state.process_prompt = True
                        st.rerun()
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Handle example question selection
    if st.session_state.get('process_prompt', False):
        prompt = st.session_state.get('current_prompt', '')
        if prompt:
            # Process the example question
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Get agent response
            validation = validate_dataset_query(prompt)
            if validation['is_valid']:
                try:
                    response = agent.analyze_query(prompt)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {e}"
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                st.session_state.messages.append({"role": "assistant", "content": validation['message']})
        
        # Clear the flags
        st.session_state.process_prompt = False
        if 'current_prompt' in st.session_state:
            del st.session_state.current_prompt
        st.rerun()
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input with validation
    if prompt := st.chat_input("Ask me about your support tickets..."):
        # Validate the query
        validation = validate_dataset_query(prompt)
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Show validation message if needed
        if not validation['is_valid']:
            with st.chat_message("assistant"):
                st.warning(validation['message'])
                if validation['suggestion']:
                    st.info(f"💡 {validation['suggestion']}")
            return
        
        # Get agent response
        with st.chat_message("assistant"):
            # Show validation guidance for valid but improvable queries
            if validation['suggestion']:
                st.info(f"ℹ️ {validation['message']}")
            
            with st.spinner("Analyzing your ticket dataset..."):
                try:
                    response = agent.analyze_query(prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


def create_analysis_tools(processor, agent=None):
    """Create analysis tools and filters."""
    st.markdown('<div class="main-header">🔍 Analysis Tools</div>', 
                unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.subheader("Filter by Status")
        status_options = ['All'] + list(processor.processed_df['Status'].unique())
        selected_status = st.selectbox("Select Status", status_options)
    
    with col2:
        st.subheader("Filter by Priority")
        priority_options = ['All'] + list(processor.processed_df['Priority'].unique())
        selected_priority = st.selectbox("Select Priority", priority_options)
    
    with col3:
        st.subheader("Filter by Project")
        project_options = ['All'] + list(processor.processed_df['Project'].unique())
        selected_project = st.selectbox("Select Project", project_options)
    
    with col4:
        st.subheader("Filter by Assignee")
        assignee_options = ['All'] + list(processor.processed_df['Assignee'].dropna().unique())
        selected_assignee = st.selectbox("Select Assignee", assignee_options)
    
    # Apply filters
    filtered_df = processor.processed_df.copy()
    
    if selected_status != 'All':
        filtered_df = filtered_df[filtered_df['Status'] == selected_status]
    
    if selected_priority != 'All':
        filtered_df = filtered_df[filtered_df['Priority'] == selected_priority]
    
    if selected_project != 'All':
        filtered_df = filtered_df[filtered_df['Project'] == selected_project]
    
    if selected_assignee != 'All':
        filtered_df = filtered_df[filtered_df['Assignee'] == selected_assignee]
    
    # Show filtered results
    st.subheader(f"📊 Filtered Results ({len(filtered_df)} tickets)")
    
    if len(filtered_df) > 0:
        # Show summary stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Filtered Tickets", len(filtered_df))
        with col2:
            avg_days = filtered_df['days_open'].mean() if 'days_open' in filtered_df.columns else 0
            st.metric("Avg Days Open", f"{avg_days:.1f}")
        with col3:
            urgent_count = len(filtered_df[filtered_df['Priority'] == 'Urgent'])
            st.metric("Urgent in Filter", urgent_count)
        
        # Show ticket table
        display_df = filtered_df[['#', 'Subject', 'Status', 'Priority', 'Project', 'Assignee', 'Created']].head(20)
        st.dataframe(display_df, use_container_width=True)
        
        if len(filtered_df) > 20:
            st.info(f"Showing top 20 tickets. Total filtered: {len(filtered_df)}")
    else:
        st.warning("No tickets match the selected filters.")
    
    # Search functionality
    st.subheader("🔍 Search Tickets")
    search_query = st.text_input("Enter search terms")
    if st.button("Search"):
        if search_query:
            results = processor.search_tickets(search_query, limit=20)
            if results:
                st.write(f"Found {len(results)} tickets:")
                for ticket in results:
                    with st.expander(f"#{ticket.get('#', 'N/A')} - {ticket.get('Subject', 'No subject')}"):
                        st.write(f"**Status:** {ticket.get('Status', 'Unknown')}")
                        st.write(f"**Priority:** {ticket.get('Priority', 'Unknown')}")
                        st.write(f"**Project:** {ticket.get('Project', 'Unknown')}")
                        st.write(f"**Assignee:** {ticket.get('Assignee', 'Unassigned')}")
                        st.write(f"**Created:** {ticket.get('Created', 'Unknown')}")
                        st.write(f"**Description:** {ticket.get('Description', 'No description')[:500]}...")
            else:
                st.write("No tickets found matching your search.")
    
    # Vector similarity search
    st.subheader("🔍 Vector Similarity Search")
    st.info("💡 Find tickets similar to your query using AI embeddings")
    
    vector_query = st.text_input("Enter your question or describe an issue:")
    col1, col2 = st.columns([1, 3])
    
    with col1:
        max_results = st.slider("Max results", 3, 10, 5)
    
    with col2:
        if st.button("🔍 Vector Search", type="primary"):
            if vector_query and agent:
                with st.spinner("Searching similar tickets using AI..."):
                    try:
                        similar_tickets = agent.search_similar_tickets(vector_query, max_results)
                        if similar_tickets:
                            st.write(f"**Found {len(similar_tickets)} similar tickets:**")
                            for ticket in similar_tickets:
                                similarity_score = ticket.get('similarity_score', 0)
                                color = "🔴" if similarity_score > 0.8 else "🟡" if similarity_score > 0.6 else "🟢"
                                
                                with st.expander(f"{color} #{ticket.get('id', 'N/A')} - {ticket.get('subject', 'No subject')} (Score: {similarity_score:.3f})"):
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.write(f"**Status:** {ticket.get('status', 'Unknown')}")
                                        st.write(f"**Priority:** {ticket.get('priority', 'Unknown')}")
                                        st.write(f"**Project:** {ticket.get('project', 'Unknown')}")
                                    with col2:
                                        st.write(f"**Assignee:** {ticket.get('assignee', 'Unassigned')}")
                                        st.write(f"**Created:** {ticket.get('created', 'Unknown')}")
                                        st.write(f"**Rank:** #{ticket.get('rank', 'N/A')}")
                                    
                                    st.write(f"**Description:** {ticket.get('description', 'No description')}")
                        else:
                            st.warning("No similar tickets found. Try a different query.")
                    except Exception as e:
                        st.error(f"Vector search error: {e}")
            elif not vector_query:
                st.warning("Please enter a search query.")
            else:
                st.warning("Please ensure the agent is initialized with API key.")
    
    # Vector store status
    if agent:
        try:
            stats = agent.get_quick_stats()
            vector_stats = stats.get('vector_store', {})
            
            if vector_stats.get('status') == 'ready':
                st.success(f"✅ Vector index ready: {vector_stats.get('total_tickets', 0)} tickets indexed, {vector_stats.get('embedding_dimension', 0)}D embeddings")
            else:
                st.warning("⚠️ Vector index not available - using fallback search methods")
        except:
            st.info("ℹ️ Vector store status unavailable")
    
    # Ticket clustering
    st.subheader("🎯 Ticket Clustering")
    if st.button("Cluster Tickets"):
        with st.spinner("Clustering tickets..."):
            clusters = processor.cluster_tickets(n_clusters=5)
            if 'error' not in clusters:
                for cluster_name, cluster_info in clusters.items():
                    with st.expander(f"{cluster_name.replace('_', ' ').title()} ({cluster_info['size']} tickets)"):
                        st.write(f"**Top Terms:** {', '.join(cluster_info.get('top_terms', [])[:10])}")
                        st.write(f"**Priority Distribution:** {cluster_info.get('priority_dist', {})}")
                        st.write(f"**Status Distribution:** {cluster_info.get('status_dist', {})}")
            else:
                st.error(clusters['error'])


def create_ticket_details(processor):
    """Create ticket details viewer."""
    st.markdown('<div class="main-header">📋 Ticket Details</div>', 
                unsafe_allow_html=True)
    
    # Ticket ID input
    ticket_id = st.number_input("Enter Ticket ID", min_value=1, step=1)
    
    if st.button("Get Ticket Details"):
        ticket = processor.get_ticket_by_id(ticket_id)
        if ticket:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Basic Information")
                st.write(f"**ID:** #{ticket.get('#', 'N/A')}")
                st.write(f"**Subject:** {ticket.get('Subject', 'No subject')}")
                st.write(f"**Status:** {ticket.get('Status', 'Unknown')}")
                st.write(f"**Priority:** {ticket.get('Priority', 'Unknown')}")
                st.write(f"**Project:** {ticket.get('Project', 'Unknown')}")
                st.write(f"**Tracker:** {ticket.get('Tracker', 'Unknown')}")
            
            with col2:
                st.subheader("Assignment & Dates")
                st.write(f"**Author:** {ticket.get('Author', 'Unknown')}")
                st.write(f"**Assignee:** {ticket.get('Assignee', 'Unassigned')}")
                st.write(f"**Created:** {ticket.get('Created', 'Unknown')}")
                st.write(f"**Updated:** {ticket.get('Updated', 'Unknown')}")
                st.write(f"**Due Date:** {ticket.get('Due date', 'Not set')}")
            
            st.subheader("Description")
            st.write(ticket.get('Description', 'No description'))
            
            st.subheader("Last Notes")
            st.write(ticket.get('Last notes', 'No notes'))
        else:
            st.error(f"Ticket #{ticket_id} not found")


def create_database_manager():
    """Create database management interface."""
    st.markdown('<div class="main-header">🗄️ Database Manager</div>', 
                unsafe_allow_html=True)
    
    # Initialize database manager if not exists
    if st.session_state.database_manager is None:
        st.session_state.database_manager = DatabaseManager()
    
    db_manager = st.session_state.database_manager
    
    # Connection status
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.session_state.db_connected:
            st.success("✅ Database Connected")
        else:
            st.error("❌ Database Not Connected")
    
    with col2:
        if st.session_state.db_connected and st.button("Disconnect"):
            db_manager.close()
            st.session_state.db_connected = False
            st.session_state.database_manager = DatabaseManager()
            st.rerun()
    
    # Database connection interface
    st.subheader("🔗 Database Connection")
    
    # Connection method selection
    connection_method = st.radio(
        "Connection Method",
        ["New Connection", "Saved Configuration", "Upload CSV/Database File"]
    )
    
    if connection_method == "New Connection":
        db_type = st.selectbox("Database Type", ["SQLite", "PostgreSQL", "MySQL"])
        
        if db_type == "SQLite":
            db_path = st.text_input("Database File Path", value="knowledge.db")
            
            if st.button("Connect to SQLite"):
                with st.spinner("Connecting to database..."):
                    if db_manager.connect_sqlite(db_path):
                        st.session_state.db_connected = True
                        st.success(f"✅ Connected to SQLite database: {db_path}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to connect to SQLite database")
        
        elif db_type == "PostgreSQL":
            col1, col2 = st.columns(2)
            with col1:
                host = st.text_input("Host", value="localhost")
                database = st.text_input("Database Name")
                username = st.text_input("Username")
            with col2:
                port = st.number_input("Port", value=5432, min_value=1, max_value=65535)
                password = st.text_input("Password", type="password")
            
            if st.button("Connect to PostgreSQL"):
                if all([host, database, username, password]):
                    with st.spinner("Connecting to database..."):
                        if db_manager.connect_postgresql(host, port, database, username, password):
                            st.session_state.db_connected = True
                            st.success(f"✅ Connected to PostgreSQL: {host}:{port}/{database}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to connect to PostgreSQL database")
                else:
                    st.error("Please fill in all required fields")
        
        elif db_type == "MySQL":
            col1, col2 = st.columns(2)
            with col1:
                host = st.text_input("Host", value="localhost")
                database = st.text_input("Database Name")
                username = st.text_input("Username")
            with col2:
                port = st.number_input("Port", value=3306, min_value=1, max_value=65535)
                password = st.text_input("Password", type="password")
            
            if st.button("Connect to MySQL"):
                if all([host, database, username, password]):
                    with st.spinner("Connecting to database..."):
                        if db_manager.connect_mysql(host, port, database, username, password):
                            st.session_state.db_connected = True
                            st.success(f"✅ Connected to MySQL: {host}:{port}/{database}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to connect to MySQL database")
                else:
                    st.error("Please fill in all required fields")
    
    elif connection_method == "Saved Configuration":
        saved_configs = db_manager.get_saved_configs()
        
        if saved_configs:
            config_name = st.selectbox("Select Configuration", saved_configs)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load Configuration"):
                    with st.spinner("Loading configuration..."):
                        if db_manager.load_connection_config(config_name):
                            st.session_state.db_connected = True
                            st.success(f"✅ Loaded configuration: {config_name}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to load configuration")
            
            with col2:
                if st.button("Delete Configuration"):
                    config_path = Path("database_configs") / f"{config_name}.json"
                    if config_path.exists():
                        config_path.unlink()
                        st.success(f"✅ Deleted configuration: {config_name}")
                        st.rerun()
        else:
            st.info("No saved configurations found")
    
    elif connection_method == "Upload CSV/Database File":
        uploaded_file = st.file_uploader(
            "Upload Database File",
            type=['csv', 'db', 'sqlite', 'sqlite3'],
            help="Upload a CSV file or SQLite database file"
        )
        
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            
            if file_type == 'csv':
                # Handle CSV upload
                table_name = st.text_input("Table Name", value="knowledge_data")
                
                if st.button("Upload CSV"):
                    with st.spinner("Uploading CSV..."):
                        # Save uploaded file temporarily
                        temp_path = f"temp_{uploaded_file.name}"
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                        
                        # Create SQLite database and upload
                        db_path = f"{table_name}.db"
                        if db_manager.connect_sqlite(db_path):
                            if db_manager.upload_csv(temp_path, table_name):
                                st.session_state.db_connected = True
                                st.success(f"✅ CSV uploaded to {db_path}")
                                os.remove(temp_path)  # Clean up
                                st.rerun()
                            else:
                                st.error("❌ Failed to upload CSV")
                        else:
                            st.error("❌ Failed to create database")
            
            elif file_type in ['db', 'sqlite', 'sqlite3']:
                # Handle SQLite database upload
                if st.button("Upload SQLite Database"):
                    with st.spinner("Uploading database..."):
                        # Save uploaded file
                        db_path = f"uploaded_{uploaded_file.name}"
                        with open(db_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                        
                        if db_manager.connect_sqlite(db_path):
                            st.session_state.db_connected = True
                            st.success(f"✅ Database uploaded: {db_path}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to connect to uploaded database")
    
    # Database operations (only show if connected)
    if st.session_state.db_connected:
        st.subheader("🗂️ Database Operations")
        
        # Save current configuration
        config_name = st.text_input("Configuration Name", placeholder="Enter name to save current connection")
        if st.button("Save Configuration") and config_name:
            if db_manager.save_connection_config(config_name):
                st.success(f"✅ Configuration saved: {config_name}")
            else:
                st.error("❌ Failed to save configuration")
        
        # Database exploration
        st.subheader("📊 Database Exploration")
        
        # Show tables
        tables = db_manager.get_tables()
        if tables:
            st.write("**Available Tables:**")
            for table in tables:
                st.write(f"- {table}")
            
            # Table selection for operations
            selected_table = st.selectbox("Select Table", tables)
            
            if selected_table:
                # Show table columns
                columns = db_manager.get_table_columns(selected_table)
                if columns:
                    st.write("**Table Columns:**")
                    cols_df = pd.DataFrame(columns)
                    st.dataframe(cols_df)
                
                # Preview data
                if st.button("Preview Data"):
                    query = f"SELECT * FROM {selected_table} LIMIT 10"
                    df = db_manager.execute_query(query)
                    if not df.empty:
                        st.write("**Data Preview:**")
                        st.dataframe(df)
                    else:
                        st.warning("No data found in table")
        else:
            st.info("No tables found in database")
        
        # Custom query interface
        st.subheader("🔍 Custom Query")
        query = st.text_area("SQL Query", placeholder="SELECT * FROM table_name LIMIT 10")
        
        if st.button("Execute Query") and query:
            with st.spinner("Executing query..."):
                df = db_manager.execute_query(query)
                if not df.empty:
                    st.write("**Query Results:**")
                    st.dataframe(df)
                    
                    # Export option
                    if st.button("Export to CSV"):
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning("Query returned no results")
        
        # Knowledge documents extraction
        st.subheader("📚 Knowledge Documents")
        if st.button("Extract Knowledge Documents"):
            with st.spinner("Extracting knowledge documents..."):
                docs_df = db_manager.get_knowledge_documents()
                if not docs_df.empty:
                    st.write("**Knowledge Documents:**")
                    st.dataframe(docs_df)
                    
                    # Export knowledge documents
                    if st.button("Export Knowledge Documents"):
                        csv = docs_df.to_csv(index=False)
                        st.download_button(
                            label="Download Knowledge Documents CSV",
                            data=csv,
                            file_name=f"knowledge_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning("No knowledge documents found")
    
    # Connection tips
    st.subheader("💡 Connection Tips")
    st.info("""
    **Database Connection Tips:**
    - **SQLite**: Perfect for local development and small datasets
    - **PostgreSQL**: Ideal for production environments with concurrent access
    - **MySQL**: Good for web applications and medium-scale deployments
    - **CSV Upload**: Quick way to get started with your data
    
    **Security Notes:**
    - Database credentials are not stored permanently
    - Use saved configurations for frequently used connections
    - Always use secure connections in production
    """)


def main():
    """Main application function."""
    st.title("🤖 AI Support Agent")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Gemini API Key
        gemini_key = st.text_input(
            "Gemini API Key",
            type="password",
            value=st.session_state.get('gemini_api_key', ''),
            help="Enter your Google Gemini API key to enable the chat agent"
        )
        
        if gemini_key:
            st.session_state.gemini_api_key = gemini_key
            st.success("✅ API key configured")
        else:
            st.warning("⚠️ Please enter your Gemini API key to enable AI features")
        
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Dashboard", "Chat Agent", "Enhanced Chat", "Knowledge Base", "Analysis Tools", "Ticket Details", "Database Manager", "Redmine Management"]
        )
        
        # Phoenix Observatory link
        st.header("Observability")
        st.markdown("🔍 **Phoenix Observatory**")
        st.markdown("Monitor agent performance and traces at:")
        st.markdown("[http://localhost:6006](http://localhost:6006)")
        
        # System status
        st.header("System Status")
        if os.path.exists("sample_tickets_template.csv"):
            st.success("✅ Data file found")
        else:
            st.error("❌ Data file missing")
        
        # Phoenix observability status
        if phoenix_available:
            st.success("✅ Phoenix observability active")
        else:
            st.warning("⚠️ Phoenix observability unavailable")
            if phoenix_error:
                st.caption(f"Reason: {phoenix_error}")
        
        # Knowledge base status
        has_vector_index = os.path.exists("knowledge_vector_index.faiss") and os.path.exists("knowledge_documents.pkl")
        has_text_search = os.path.exists("knowledge_text_search.marker")
        
        if has_vector_index:
            st.success("✅ Vector knowledge base ready")
        elif has_text_search:
            st.success("✅ Text knowledge base ready")
        else:
            st.info("ℹ️ Knowledge base not built yet")
    
    # Load data
    processor = load_data()
    if processor is None:
        st.error("❌ Failed to load ticket data")
        st.info("""
        **Troubleshooting:**
        1. Make sure the file `sample_tickets_template.csv` exists in the project directory
        2. Check that the file is properly formatted CSV
        3. Ensure the file is not corrupted or empty
        4. Try refreshing the page
        """)
        
        # Show minimal interface even if data loading fails
        st.subheader("🔧 System Setup")
        st.info("Please fix the data loading issue to access the full application.")
        return
    
    # Initialize agents if API key is provided
    agent = None
    enhanced_agent = None
    if gemini_key:
        if page in ["Chat Agent", "Analysis Tools"]:
            agent = initialize_simple_agent()
        if page in ["Enhanced Chat", "Knowledge Base"]:
            enhanced_agent = initialize_enhanced_agent()
    
    # Page routing
    if page == "Dashboard":
        create_dashboard(processor)
    elif page == "Chat Agent":
        if agent:
            create_chat_interface(agent)
        else:
            st.warning("⚠️ Please enter your Gemini API key in the sidebar to use the chat agent.")
            st.info("The chat agent requires a valid Google Gemini API key to function.")
    elif page == "Enhanced Chat":
        if enhanced_agent:
            create_enhanced_chat_interface(enhanced_agent)
        else:
            st.warning("⚠️ Please enter your Gemini API key in the sidebar to use the enhanced chat agent.")
            st.info("The enhanced chat agent requires a valid Google Gemini API key to function.")
    elif page == "Knowledge Base":
        if enhanced_agent:
            create_knowledge_base_page(enhanced_agent)
        else:
            st.warning("⚠️ Please enter your Gemini API key in the sidebar to access the knowledge base.")
            st.info("The knowledge base requires a valid Google Gemini API key to function.")
    elif page == "Analysis Tools":
        create_analysis_tools(processor, agent)
    elif page == "Ticket Details":
        create_ticket_details(processor)
    elif page == "Database Manager":
        create_database_manager()
    elif page == "Redmine Management":
        create_redmine_configuration()
        create_ticket_management_interface()


if __name__ == "__main__":
    main() 