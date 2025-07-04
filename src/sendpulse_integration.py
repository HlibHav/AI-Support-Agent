"""
SendPulse Live Chat Integration for AI Support Agent
Integrates the AI support agent with SendPulse live chat system.
"""

import os
import json
import asyncio
import logging
import hashlib
import hmac
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SendPulseConfig:
    """Configuration for SendPulse integration."""
    api_id: str
    api_secret: str
    live_chat_id: str
    base_url: str = "https://api.sendpulse.com"
    
    
class SendPulseAPI:
    """SendPulse API client for live chat integration."""
    
    def __init__(self, config: SendPulseConfig):
        """Initialize SendPulse API client."""
        self.config = config
        self.access_token = None
        self.token_expires = 0
        self.session = requests.Session()
    
    def _get_access_token(self) -> str:
        """Get or refresh access token."""
        if self.access_token and time.time() < self.token_expires:
            return self.access_token
        
        url = f"{self.config.base_url}/oauth/access_token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.config.api_id,
            'client_secret': self.config.api_secret
        }
        
        try:
            response = self.session.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expires = time.time() + token_data['expires_in'] - 60  # 1 minute buffer
            
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get SendPulse access token: {e}")
            raise
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated request to SendPulse API."""
        token = self._get_access_token()
        
        url = f"{self.config.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json() if response.content else {}
            
        except Exception as e:
            logger.error(f"SendPulse API request failed: {e}")
            raise
    
    def get_chat_messages(self, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages from a chat conversation."""
        endpoint = f"/messenger/v2/chats/{chat_id}/messages"
        params = f"?limit={limit}"
        
        try:
            response = self._make_request('GET', endpoint + params)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get chat messages: {e}")
            return []
    
    def send_message(self, chat_id: str, message: str, message_type: str = "text") -> bool:
        """Send a message to a chat."""
        endpoint = f"/messenger/v2/chats/{chat_id}/messages"
        
        data = {
            "message": {
                "type": message_type,
                "text": message
            }
        }
        
        try:
            response = self._make_request('POST', endpoint, data)
            return response.get('result', False)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def get_active_chats(self) -> List[Dict[str, Any]]:
        """Get list of active chats."""
        endpoint = f"/messenger/v2/chats?status=active"
        
        try:
            response = self._make_request('GET', endpoint)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get active chats: {e}")
            return []
    
    def set_chat_assignee(self, chat_id: str, operator_id: str) -> bool:
        """Assign chat to an operator."""
        endpoint = f"/messenger/v2/chats/{chat_id}/assignee"
        
        data = {
            "operator_id": operator_id
        }
        
        try:
            response = self._make_request('PUT', endpoint, data)
            return response.get('result', False)
        except Exception as e:
            logger.error(f"Failed to assign chat: {e}")
            return False


class AIAgentIntegration:
    """Integration between AI Support Agent and SendPulse Live Chat."""
    
    def __init__(self, sendpulse_api: SendPulseAPI, ai_agent=None):
        """Initialize AI agent integration."""
        self.sendpulse = sendpulse_api
        self.ai_agent = ai_agent
        self.active_sessions = {}
        self.message_history = {}
    
    def process_incoming_message(self, chat_id: str, message: str, user_info: Dict[str, Any]) -> str:
        """Process incoming message from SendPulse chat."""
        try:
            # Initialize session if new
            if chat_id not in self.active_sessions:
                self.active_sessions[chat_id] = {
                    'user_info': user_info,
                    'started_at': datetime.now(),
                    'message_count': 0,
                    'context': []
                }
            
            session = self.active_sessions[chat_id]
            session['message_count'] += 1
            
            # Add message to history
            if chat_id not in self.message_history:
                self.message_history[chat_id] = []
            
            self.message_history[chat_id].append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now()
            })
            
            # Generate AI response
            ai_response = self._generate_ai_response(message, session)
            
            # Add AI response to history
            self.message_history[chat_id].append({
                'role': 'assistant',
                'content': ai_response,
                'timestamp': datetime.now()
            })
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again or contact a human agent."
    
    def _generate_ai_response(self, message: str, session: Dict[str, Any]) -> str:
        """Generate AI response using the enhanced agent."""
        try:
            if not self.ai_agent:
                return self._get_fallback_response(message)
            
            # Build context from session
            context = self._build_context(session)
            
            # Use the enhanced agent to generate response
            if hasattr(self.ai_agent, 'process_query'):
                response = self.ai_agent.process_query(message, context=context)
            elif hasattr(self.ai_agent, 'analyze_query'):
                response = self.ai_agent.analyze_query(message)
            else:
                return self._get_fallback_response(message)
            
            # Format response for chat
            return self._format_chat_response(response)
            
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return self._get_fallback_response(message)
    
    def _build_context(self, session: Dict[str, Any]) -> str:
        """Build context string from session information."""
        context_parts = []
        
        # User information
        user_info = session.get('user_info', {})
        if user_info.get('name'):
            context_parts.append(f"User: {user_info['name']}")
        
        # Session information
        context_parts.append(f"Session started: {session['started_at']}")
        context_parts.append(f"Messages in conversation: {session['message_count']}")
        
        # Previous context
        if session.get('context'):
            context_parts.extend(session['context'])
        
        return "\n".join(context_parts)
    
    def _format_chat_response(self, response: str) -> str:
        """Format AI response for live chat."""
        # Remove excessive formatting for chat
        response = response.replace('**', '')
        response = response.replace('##', '')
        
        # Limit response length for chat
        max_length = 1000
        if len(response) > max_length:
            response = response[:max_length] + "...\n\nWould you like me to continue with more details?"
        
        return response
    
    def _get_fallback_response(self, message: str) -> str:
        """Generate fallback response when AI agent is unavailable."""
        message_lower = message.lower()
        
        # Simple keyword-based responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return "Hello! I'm your AI support assistant. How can I help you today?"
        
        elif any(word in message_lower for word in ['help', 'support']):
            return "I'm here to help you with support tickets and technical questions. What specific issue can I assist you with?"
        
        elif any(word in message_lower for word in ['ticket', 'issue', 'problem']):
            return "I can help you analyze support tickets and find solutions. Could you provide more details about the specific ticket or issue?"
        
        elif any(word in message_lower for word in ['thank', 'thanks']):
            return "You're welcome! Is there anything else I can help you with?"
        
        else:
            return "I understand you're looking for assistance. Could you please provide more details about what you need help with? I can help with support ticket analysis, troubleshooting, and finding relevant documentation."
    
    def handle_chat_handoff(self, chat_id: str, operator_id: str) -> bool:
        """Hand off chat to human operator."""
        try:
            # Send handoff message
            handoff_message = "I'm transferring you to a human agent who can provide more specialized assistance."
            self.sendpulse.send_message(chat_id, handoff_message)
            
            # Assign to operator
            success = self.sendpulse.set_chat_assignee(chat_id, operator_id)
            
            if success:
                # Archive session
                if chat_id in self.active_sessions:
                    session = self.active_sessions[chat_id]
                    session['handed_off_at'] = datetime.now()
                    session['operator_id'] = operator_id
                
                logger.info(f"Chat {chat_id} handed off to operator {operator_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to hand off chat: {e}")
            return False
    
    def get_session_summary(self, chat_id: str) -> Dict[str, Any]:
        """Get summary of chat session."""
        if chat_id not in self.active_sessions:
            return {}
        
        session = self.active_sessions[chat_id]
        messages = self.message_history.get(chat_id, [])
        
        return {
            'chat_id': chat_id,
            'user_info': session.get('user_info', {}),
            'started_at': session.get('started_at'),
            'message_count': session.get('message_count', 0),
            'total_messages': len(messages),
            'last_activity': messages[-1]['timestamp'] if messages else None,
            'status': 'active' if chat_id in self.active_sessions else 'archived'
        }


class SendPulseChatBot:
    """Complete SendPulse chat bot implementation."""
    
    def __init__(self, config: SendPulseConfig, ai_agent=None):
        """Initialize the chat bot."""
        self.config = config
        self.api = SendPulseAPI(config)
        self.integration = AIAgentIntegration(self.api, ai_agent)
        self.running = False
    
    async def start_polling(self, poll_interval: int = 5):
        """Start polling for new messages."""
        self.running = True
        logger.info("Starting SendPulse chat bot polling...")
        
        while self.running:
            try:
                await self._poll_messages()
                await asyncio.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(poll_interval * 2)  # Backoff on error
    
    async def _poll_messages(self):
        """Poll for new messages from active chats."""
        try:
            active_chats = self.api.get_active_chats()
            
            for chat in active_chats:
                chat_id = chat.get('id')
                if not chat_id:
                    continue
                
                # Get recent messages
                messages = self.api.get_chat_messages(chat_id, limit=10)
                
                # Process unhandled messages
                for message in messages:
                    if self._should_process_message(message):
                        await self._handle_message(chat_id, message, chat)
                        
        except Exception as e:
            logger.error(f"Error polling messages: {e}")
    
    def _should_process_message(self, message: Dict[str, Any]) -> bool:
        """Check if message should be processed by AI."""
        # Don't process bot's own messages
        if message.get('from_operator'):
            return False
        
        # Check if message is recent (within last 5 minutes)
        message_time = message.get('created_at')
        if message_time:
            # Add logic to check message timestamp
            pass
        
        return True
    
    async def _handle_message(self, chat_id: str, message: Dict[str, Any], chat_info: Dict[str, Any]):
        """Handle a single message."""
        try:
            message_text = message.get('text', '').strip()
            if not message_text:
                return
            
            user_info = {
                'name': chat_info.get('contact', {}).get('name'),
                'email': chat_info.get('contact', {}).get('email'),
                'id': chat_info.get('contact', {}).get('id')
            }
            
            # Generate AI response
            ai_response = self.integration.process_incoming_message(
                chat_id, message_text, user_info
            )
            
            # Send response
            if ai_response:
                success = self.api.send_message(chat_id, ai_response)
                if success:
                    logger.info(f"Sent AI response to chat {chat_id}")
                else:
                    logger.error(f"Failed to send response to chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def stop(self):
        """Stop the chat bot."""
        self.running = False
        logger.info("SendPulse chat bot stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        return {
            'active_sessions': len(self.integration.active_sessions),
            'total_messages': sum(
                len(messages) for messages in self.integration.message_history.values()
            ),
            'running': self.running
        }


# Integration functions for the main application
def create_sendpulse_integration(api_id: str, api_secret: str, live_chat_id: str, ai_agent=None):
    """Create SendPulse integration instance."""
    config = SendPulseConfig(
        api_id=api_id,
        api_secret=api_secret,
        live_chat_id=live_chat_id
    )
    
    return SendPulseChatBot(config, ai_agent)


def setup_sendpulse_webhook(webhook_url: str, sendpulse_api: SendPulseAPI) -> bool:
    """Setup webhook for real-time message handling."""
    try:
        # Configure webhook endpoint
        endpoint = "/messenger/v2/webhooks"
        data = {
            "url": webhook_url,
            "events": ["message_received", "chat_started", "chat_closed"]
        }
        
        response = sendpulse_api._make_request('POST', endpoint, data)
        return response.get('result', False)
        
    except Exception as e:
        logger.error(f"Failed to setup webhook: {e}")
        return False 