"""
Redmine API Service for ticket management and updates.
Provides authentication, ticket retrieval, and update functionality.
"""

import requests
import json
from typing import Dict, List, Optional, Any, cast
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RedmineAuthType(Enum):
    """Authentication types for Redmine API."""
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"


@dataclass
class RedmineConfig:
    """Configuration for Redmine API connection."""
    base_url: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    auth_type: RedmineAuthType = RedmineAuthType.API_KEY
    timeout: int = 30


class RedmineAPIError(Exception):
    """Custom exception for Redmine API errors."""
    pass


class RedmineService:
    """Service class for interacting with Redmine API."""
    
    def __init__(self, config: RedmineConfig):
        """Initialize Redmine service with configuration."""
        self.config = config
        self.session = requests.Session()
        self._setup_authentication()
    
    def _setup_authentication(self):
        """Set up authentication headers for API requests."""
        if self.config.auth_type == RedmineAuthType.API_KEY:
            if not self.config.api_key:
                raise RedmineAPIError("API key is required for API key authentication")
            self.session.headers.update({
                'X-Redmine-API-Key': self.config.api_key,
                'Content-Type': 'application/json'
            })
        elif self.config.auth_type == RedmineAuthType.BASIC_AUTH:
            if not self.config.username or not self.config.password:
                raise RedmineAPIError("Username and password are required for basic authentication")
            # Use cast to help type checker understand these are strings after the check
            self.session.auth = (cast(str, self.config.username), cast(str, self.config.password))
            self.session.headers.update({
                'Content-Type': 'application/json'
            })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to Redmine API."""
        url = f"{self.config.base_url.rstrip('/')}/{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Redmine API request failed: {e}")
            raise RedmineAPIError(f"API request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise RedmineAPIError(f"Invalid JSON response: {e}")
    
    def get_issue(self, issue_id: int, include: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get a specific issue by ID."""
        endpoint = f"issues/{issue_id}.json"
        
        if include:
            params = "?include=" + ",".join(include)
            endpoint += params
            
        return self._make_request('GET', endpoint)
    
    def list_issues(self, 
                   project_id: Optional[int] = None,
                   assigned_to_id: Optional[int] = None,
                   status_id: Optional[str] = None,
                   limit: int = 100,
                   offset: int = 0) -> Dict[str, Any]:
        """List issues with optional filters."""
        endpoint = "issues.json"
        params = []
        
        if project_id:
            params.append(f"project_id={project_id}")
        if assigned_to_id:
            params.append(f"assigned_to_id={assigned_to_id}")
        if status_id:
            params.append(f"status_id={status_id}")
        
        params.extend([f"limit={limit}", f"offset={offset}"])
        
        if params:
            endpoint += "?" + "&".join(params)
            
        return self._make_request('GET', endpoint)
    
    def update_issue(self, issue_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an issue with new data."""
        endpoint = f"issues/{issue_id}.json"
        
        # Wrap updates in 'issue' key as required by Redmine API
        data = {"issue": updates}
        
        return self._make_request('PUT', endpoint, data)
    
    def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue."""
        endpoint = "issues.json"
        
        # Wrap issue data in 'issue' key as required by Redmine API
        data = {"issue": issue_data}
        
        return self._make_request('POST', endpoint, data)
    
    def add_issue_note(self, issue_id: int, notes: str, private: bool = False) -> Dict[str, Any]:
        """Add a note to an issue."""
        updates = {
            "notes": notes,
            "private_notes": private
        }
        
        return self.update_issue(issue_id, updates)
    
    def update_issue_status(self, issue_id: int, status_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        """Update the status of an issue."""
        updates = {"status_id": status_id}
        
        if notes:
            updates["notes"] = notes
            
        return self.update_issue(issue_id, updates)
    
    def assign_issue(self, issue_id: int, assigned_to_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        """Assign an issue to a user."""
        updates = {"assigned_to_id": assigned_to_id}
        
        if notes:
            updates["notes"] = notes
            
        return self.update_issue(issue_id, updates)
    
    def close_issue(self, issue_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        """Close an issue (assuming status_id 5 is 'Closed')."""
        return self.update_issue_status(issue_id, 5, notes)
    
    def get_issue_statuses(self) -> Dict[str, Any]:
        """Get all available issue statuses."""
        return self._make_request('GET', 'issue_statuses.json')
    
    def get_trackers(self) -> Dict[str, Any]:
        """Get all available trackers."""
        return self._make_request('GET', 'trackers.json')
    
    def get_priorities(self) -> Dict[str, Any]:
        """Get all available priorities."""
        return self._make_request('GET', 'enumerations/issue_priorities.json')
    
    def get_projects(self) -> Dict[str, Any]:
        """Get all available projects."""
        return self._make_request('GET', 'projects.json')
    
    def get_users(self) -> Dict[str, Any]:
        """Get all users (requires admin privileges)."""
        return self._make_request('GET', 'users.json')
    
    def search_issues(self, query: str, limit: int = 25) -> Dict[str, Any]:
        """Search issues by query."""
        endpoint = f"search.json?q={query}&issues=1&limit={limit}"
        return self._make_request('GET', endpoint)
    
    def add_watcher(self, issue_id: int, user_id: int) -> Dict[str, Any]:
        """Add a watcher to an issue."""
        endpoint = f"issues/{issue_id}/watchers.json"
        data = {"user_id": user_id}
        return self._make_request('POST', endpoint, data)
    
    def remove_watcher(self, issue_id: int, user_id: int) -> Dict[str, Any]:
        """Remove a watcher from an issue."""
        endpoint = f"issues/{issue_id}/watchers/{user_id}.json"
        return self._make_request('DELETE', endpoint)
    
    def upload_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Upload a file to Redmine."""
        upload_url = f"{self.config.base_url.rstrip('/')}/uploads.json"
        
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f, 'application/octet-stream')}
            
            # Use a separate session for file upload
            session = requests.Session()
            if self.config.auth_type == RedmineAuthType.API_KEY:
                session.headers.update({'X-Redmine-API-Key': self.config.api_key})
            else:
                session.auth = (self.config.username, self.config.password)
                
            response = session.post(upload_url, files=files, timeout=self.config.timeout)
            response.raise_for_status()
            
            return response.json()
    
    def test_connection(self) -> bool:
        """Test the connection to Redmine API."""
        try:
            # Try to get the current user info
            self._make_request('GET', 'my/account.json')
            return True
        except RedmineAPIError:
            return False


class RedmineTicketManager:
    """High-level ticket management interface."""
    
    def __init__(self, redmine_service: RedmineService):
        """Initialize with a Redmine service instance."""
        self.redmine = redmine_service
        self._status_cache = None
        self._user_cache = None
    
    def get_statuses(self) -> Dict[str, int]:
        """Get status name to ID mapping."""
        if self._status_cache is None:
            response = self.redmine.get_issue_statuses()
            self._status_cache = {
                status['name']: status['id'] 
                for status in response['issue_statuses']
            }
        return self._status_cache
    
    def get_users(self) -> Dict[str, int]:
        """Get user name to ID mapping."""
        if self._user_cache is None:
            try:
                response = self.redmine.get_users()
                self._user_cache = {
                    f"{user['firstname']} {user['lastname']}": user['id']
                    for user in response['users']
                }
            except RedmineAPIError:
                # Fallback if we don't have admin privileges
                self._user_cache = {}
        return self._user_cache
    
    def update_ticket_from_ai_analysis(self, 
                                     issue_id: int, 
                                     ai_analysis: Dict[str, Any],
                                     auto_update: bool = False) -> Dict[str, Any]:
        """Update a ticket based on AI analysis results."""
        updates = {}
        notes_parts = []
        
        # Process AI analysis results
        if 'priority' in ai_analysis:
            # Map AI priority to Redmine priority
            priority_mapping = {
                'low': 1, 'normal': 2, 'high': 3, 'urgent': 4, 'immediate': 5
            }
            if ai_analysis['priority'].lower() in priority_mapping:
                updates['priority_id'] = priority_mapping[ai_analysis['priority'].lower()]
                notes_parts.append(f"Priority updated based on AI analysis: {ai_analysis['priority']}")
        
        if 'category' in ai_analysis:
            notes_parts.append(f"AI categorized as: {ai_analysis['category']}")
        
        if 'suggested_action' in ai_analysis:
            notes_parts.append(f"AI suggested action: {ai_analysis['suggested_action']}")
        
        if 'confidence' in ai_analysis:
            notes_parts.append(f"AI confidence: {ai_analysis['confidence']}")
        
        # Add AI analysis as notes
        if notes_parts:
            updates['notes'] = "AI Analysis Results:\n" + "\n".join(notes_parts)
        
        # Only update if there are changes and auto_update is enabled
        if updates and auto_update:
            return self.redmine.update_issue(issue_id, updates)
        
        return {'updates': updates, 'notes': notes_parts}
    
    def bulk_update_tickets(self, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update multiple tickets in bulk."""
        results = []
        
        for update in updates:
            try:
                issue_id = update['issue_id']
                issue_updates = update.get('updates', {})
                
                result = self.redmine.update_issue(issue_id, issue_updates)
                results.append({
                    'issue_id': issue_id,
                    'success': True,
                    'result': result
                })
            except RedmineAPIError as e:
                results.append({
                    'issue_id': update.get('issue_id', 'unknown'),
                    'success': False,
                    'error': str(e)
                })
        
        return results 