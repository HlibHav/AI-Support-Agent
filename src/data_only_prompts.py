"""
Example prompts that ensure the agent responds only from the dataset.
"""

DATASET_ONLY_EXAMPLES = [
    # Ticket Analysis questions
    "How many urgent tickets are in the dataset?",
    "What are the top 5 most common issues in our tickets?",
    "Which assignee has the most tickets assigned?",
    "Show me all tickets related to payment failures",
    
    # Search and filtering
    "Find all tickets from ProjectA",
    "Show me tickets with status 'New'", 
    "List all tickets assigned to Jane Doe",
    "What tickets mention 'database connection'?",
    
    # Pattern analysis
    "Cluster tickets to identify common themes",
    "What's the average resolution time in our data?",
    "Show me priority distribution of tickets",
    "Which projects have the most support requests?",
    
    # Specific ticket details
    "Show me details for ticket #1",
    "What are all the urgent priority tickets?",
    "Find tickets created in the last 30 days",
    "List all tickets that are still open",
    
    # Trend analysis
    "What status do most tickets have?",
    "How many tickets are closed vs open?",
    "Which tracker type has the most issues?",
    "Show me tickets by creation date",
    
    # SaaS Knowledge Base Questions
    "How do I get started with TaskFlow Pro?",
    "What are the different pricing plans available?",
    "How do I create a new project in TaskFlow Pro?",
    "What user roles are available in the system?",
    "How do I integrate TaskFlow Pro with Slack?",
    "What are the API rate limits?",
    "How do I troubleshoot login issues?",
    "What security features does TaskFlow Pro offer?",
    "How do I export project data?",
    "What mobile apps are available?",
    "How do I set up team notifications?",
    "What integrations are supported?",
]

AVOID_THESE_QUESTIONS = [
    # General advice (not dataset-specific)
    "How should we improve customer support?",
    "What are best practices for ticket management?",
    "How to reduce response times?",
    "What tools should we use for support?",
    
    # External knowledge
    "What is ITIL framework?",
    "How does Zendesk compare to Jira?",
    "What are industry benchmarks?",
    "Tell me about support methodologies",
]

PROMPT_SUGGESTIONS = [
    {
        "category": "📊 Ticket Analysis",
        "prompts": [
            "Show me a summary of all tickets in the dataset",
            "What's the distribution of ticket priorities?",
            "How many tickets does each assignee have?",
        ]
    },
    {
        "category": "🔍 Search & Filter", 
        "prompts": [
            "Find all application crash tickets",
            "Show me urgent tickets that are still open",
            "List tickets assigned to Jane Doe",
        ]
    },
    {
        "category": "📈 Patterns & Trends",
        "prompts": [
            "Cluster tickets to identify common issues",
            "What are the most common ticket subjects?",
            "Show me tickets by project breakdown",
        ]
    },
    {
        "category": "🎫 Specific Tickets",
        "prompts": [
            "Show details for ticket #1",
            "Find all tickets about database issues",
            "List all bug reports",
        ]
    },
    {
        "category": "📚 SaaS Knowledge",
        "prompts": [
            "How do I get started with TaskFlow Pro?",
            "What are the different pricing plans?",
            "How do I create a new project?",
        ]
    },
    {
        "category": "🔧 API & Integration",
        "prompts": [
            "How do I authenticate with the TaskFlow Pro API?",
            "What integrations are available?",
            "How do I set up Slack integration?",
        ]
    },
    {
        "category": "🛠️ Troubleshooting",
        "prompts": [
            "How do I fix login issues?",
            "What should I do if projects aren't loading?",
            "How do I resolve notification problems?",
        ]
    }
]

from typing import Union

def validate_dataset_query(query: str) -> dict[str, Union[str, bool]]:
    """
    Validate if a query is appropriate for dataset-only analysis.
    
    Returns:
        dict: {'is_valid': bool, 'message': str, 'suggestion': str}
    """
    query_lower = query.lower()
    
    # Check for general advice keywords
    general_keywords = [
        'should', 'recommend', 'best practice', 'how to', 'improve',
        'industry', 'benchmark', 'methodology', 'framework', 'compare'
    ]
    
    for keyword in general_keywords:
        if keyword in query_lower:
            return {
                'is_valid': False,
                'message': f"This question asks for general advice ('{keyword}'). I can only analyze your specific ticket dataset.",
                'suggestion': "Try asking about specific data in your tickets, like 'Show me urgent tickets' or 'What are the most common issues?'"
            }
    
    # Check for dataset-specific keywords (good signs)
    dataset_keywords = [
        'ticket', 'show', 'find', 'list', 'how many', 'count', 'search',
        'assignee', 'priority', 'status', 'project', 'cluster', 'analyze'
    ]
    
    has_dataset_keyword = any(keyword in query_lower for keyword in dataset_keywords)
    
    if not has_dataset_keyword:
        return {
            'is_valid': True,  # Allow it but provide guidance
            'message': "I'll analyze this based on your ticket dataset only.",
            'suggestion': "For better results, try questions like 'Show me tickets about...' or 'How many tickets have...'"
        }
    
    return {
        'is_valid': True,
        'message': "Great! This question can be answered using your ticket dataset.",
        'suggestion': ""
    } 