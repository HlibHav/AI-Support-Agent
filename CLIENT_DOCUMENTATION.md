# AI Support Agent - Client Documentation

## Overview

The AI Support Agent is a comprehensive support system that integrates artificial intelligence with live chat capabilities, ticket management, and knowledge base functionality. This system provides intelligent responses to customer queries, manages support tickets through Redmine integration, and offers extensive knowledge base management.

## 🎯 Key Features

### 1. AI-Powered Support
- **Intelligent Response Generation**: Uses Google Gemini 1.5 Flash for fast, accurate responses
- **Context-Aware Conversations**: Maintains conversation history and context
- **Multi-Language Support**: Handles queries in multiple languages
- **Fallback Responses**: Provides helpful responses even when AI is unavailable

### 2. SendPulse Live Chat Integration
- **Real-Time Chat Processing**: Integrates with SendPulse live chat system
- **Automatic Response Handling**: AI responds to customer queries automatically
- **Human Handoff Capability**: Seamlessly transfers complex issues to human agents
- **Session Management**: Tracks conversation history and user context

### 3. Redmine Ticket Management
- **Ticket CRUD Operations**: Create, read, update, and delete tickets
- **Status Management**: Update ticket statuses and priorities
- **Assignment Management**: Assign tickets to appropriate team members
- **Note Addition**: Add public and private notes to tickets
- **Bulk Operations**: Handle multiple tickets simultaneously

### 4. Knowledge Base Management
- **Document Processing**: Processes Word documents (.docx) for knowledge extraction
- **Vector Search**: Advanced semantic search capabilities
- **Text Search**: Traditional keyword-based search
- **RESTful API**: Complete API for knowledge base operations
- **Automatic Updates**: Rebuilds knowledge base when documents are updated

### 5. Web Interface
- **Streamlit-Based UI**: Modern, responsive web interface
- **Multiple Analysis Tools**: Ticket analysis, pattern recognition, clustering
- **Interactive Dashboards**: Visual data representation with charts and graphs
- **Real-Time Monitoring**: Live system status and performance metrics

## 🚀 System Architecture

### Components

1. **Streamlit Application** (`streamlit_app.py`)
   - Main web interface
   - User authentication and session management
   - Chat interface and ticket management UI

2. **AI Processing Engine** (`src/enhanced_ticket_agent.py`)
   - Core AI functionality
   - Natural language processing
   - Response generation

3. **SendPulse Integration** (`src/sendpulse_integration.py`)
   - Live chat API integration
   - Message processing and routing
   - Session management

4. **Redmine Service** (`src/redmine_service.py`)
   - Ticket management API
   - CRUD operations
   - Status and assignment management

5. **Knowledge Base API** (`src/knowledge_api.py`)
   - Document processing
   - Vector and text search
   - Knowledge base management

6. **Data Processing Layer** (`src/data_processor.py`)
   - CSV data analysis
   - Pattern recognition
   - Statistical analysis

## 🛠️ Technical Requirements

### Server Requirements
- **Operating System**: Linux/Unix (Ubuntu 18.04+ recommended)
- **RAM**: Minimum 4GB (8GB+ recommended for large knowledge bases)
- **Storage**: 10GB+ available space
- **Network**: Stable internet connection for API calls

### Software Dependencies
- **Python**: 3.9+ (3.10+ recommended)
- **pip**: Latest version
- **Virtual Environment**: venv or conda

### API Requirements
- **Google Gemini API**: For AI functionality
- **SendPulse API**: For live chat integration
- **Redmine API**: For ticket management (optional)

## 📋 Installation Guide

### 1. System Preparation
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install system dependencies
sudo apt install build-essential libssl-dev libffi-dev python3-dev -y
```

### 2. Application Setup
```bash
# Clone or extract the application
cd /opt
sudo mkdir ai-support-agent
sudo chown $USER:$USER ai-support-agent
cd ai-support-agent

# Extract your application files here
# (Upload via SCP, FTP, or extract from archive)

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configuration Setup
```bash
# Copy environment template
cp env.template .env

# Edit configuration file
nano .env
```

### 4. Required Environment Variables

Edit the `.env` file with your specific values:

```env
# Google Gemini API Configuration
GOOGLE_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=models/gemini-1.5-flash

# SendPulse Configuration
SENDPULSE_API_ID=your_sendpulse_api_id
SENDPULSE_API_SECRET=your_sendpulse_api_secret
SENDPULSE_LIVE_CHAT_ID=your_live_chat_id

# Redmine Configuration (Optional)
REDMINE_URL=https://your-redmine-instance.com
REDMINE_API_KEY=your_redmine_api_key_here

# Application Configuration
APP_PORT=8502
API_PORT=8000
DEBUG_MODE=false
```

## 🔑 API Key Configuration

### 1. Google Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key and add it to your `.env` file as `GOOGLE_API_KEY`

### 2. SendPulse API Credentials
1. Log in to your SendPulse account
2. Go to **Settings** → **API**
3. Create new API credentials
4. Copy the API ID and API Secret
5. Add them to your `.env` file as `SENDPULSE_API_ID` and `SENDPULSE_API_SECRET`

### 3. SendPulse Live Chat ID
1. In SendPulse, go to **Messengers** → **Live Chat**
2. Find your live chat widget
3. Copy the Chat ID from the widget settings
4. Add it to your `.env` file as `SENDPULSE_LIVE_CHAT_ID`

### 4. Redmine API Key (Optional)
1. Log in to your Redmine instance
2. Go to **My Account** → **API access key**
3. Generate or copy your API key
4. Add your Redmine URL and API key to the `.env` file

## 🚀 Deployment Steps

### 1. Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Verify installation
python -c "import streamlit; print('Streamlit installed successfully')"
python -c "import google.generativeai; print('Gemini API available')"
```

### 2. Knowledge Base Preparation
```bash
# Build knowledge base (if you have documents)
python build_knowledge_base.py

# Or use the text-based knowledge builder
python build_text_search_knowledge.py
```

### 3. Start the Application
```bash
# Start the main Streamlit application
streamlit run streamlit_app.py --server.port 8502 --server.address 0.0.0.0

# In a separate terminal, start the Knowledge Base API
source venv/bin/activate
python -m uvicorn src.knowledge_api:app --host 0.0.0.0 --port 8000
```

### 4. Process Manager Setup (Production)
For production deployment, use a process manager like systemd:

```bash
# Create systemd service file
sudo nano /etc/systemd/system/ai-support-agent.service
```

Add the following content:
```ini
[Unit]
Description=AI Support Agent
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/opt/ai-support-agent
Environment=PATH=/opt/ai-support-agent/venv/bin
ExecStart=/opt/ai-support-agent/venv/bin/streamlit run streamlit_app.py --server.port 8502 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-support-agent
sudo systemctl start ai-support-agent
```

### 5. Reverse Proxy Setup (Optional)
For production, use Nginx as a reverse proxy:

```bash
# Install Nginx
sudo apt install nginx -y

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/ai-support-agent
```

Add the following configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8502;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/ai-support-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔧 SendPulse Integration Setup

### 1. Configure SendPulse Live Chat
1. **Access SendPulse Dashboard**
   - Go to https://login.sendpulse.com/
   - Log in with your credentials

2. **Navigate to Live Chat**
   - Click on "Messengers" in the left sidebar
   - Select "Live Chat"

3. **Create/Configure Chat Widget**
   - Click "Create Live Chat" or select existing widget
   - Configure appearance and behavior settings
   - Note the Chat ID for configuration

4. **API Integration**
   - Go to Settings → API
   - Generate API credentials
   - Configure webhook URL: `https://your-domain.com/api/webhook/sendpulse`

### 2. Start SendPulse Integration
```bash
# In the application directory
source venv/bin/activate

# Start the SendPulse integration
python -c "
from src.sendpulse_integration import create_sendpulse_integration
from src.enhanced_ticket_agent import EnhancedTicketAgent
import os

# Initialize AI agent
ai_agent = EnhancedTicketAgent(os.getenv('GOOGLE_API_KEY'))

# Create SendPulse integration
integration = create_sendpulse_integration(
    api_id=os.getenv('SENDPULSE_API_ID'),
    api_secret=os.getenv('SENDPULSE_API_SECRET'),
    live_chat_id=os.getenv('SENDPULSE_LIVE_CHAT_ID'),
    ai_agent=ai_agent
)

# Start polling (this will run continuously)
import asyncio
asyncio.run(integration.start_polling())
"
```

## 🎮 Usage Guide

### 1. Accessing the Application
- Open your web browser
- Navigate to `http://your-server-ip:8502` or your configured domain
- The application will load with the main dashboard

### 2. Initial Setup
1. **Enter API Keys** in the sidebar configuration
2. **Build Knowledge Base** if you have documents to process
3. **Configure Redmine** connection if using ticket management

### 3. Using the Chat Interface
- Click on "Chat Agent" in the navigation
- Enter your support queries
- The AI will analyze and respond based on your knowledge base

### 4. Ticket Management
- Navigate to "Redmine Management"
- View, create, and update support tickets
- Use bulk operations for multiple tickets

### 5. Knowledge Base Management
- Use the "Knowledge Base" tab to search documentation
- Upload new documents through the API
- Rebuild the knowledge base when content changes

## 🔍 Monitoring and Maintenance

### 1. System Health Checks
```bash
# Check application status
sudo systemctl status ai-support-agent

# View logs
sudo journalctl -u ai-support-agent -f

# Check API health
curl http://localhost:8000/health
```

### 2. Performance Monitoring
- Monitor CPU and memory usage
- Check response times for API calls
- Monitor SendPulse integration statistics

### 3. Regular Maintenance
- Update dependencies monthly
- Rebuild knowledge base when documents change
- Monitor API usage limits
- Review and archive old conversation logs

## 🛡️ Security Considerations

### 1. API Key Security
- Never commit API keys to version control
- Use environment variables for all sensitive data
- Rotate API keys regularly
- Implement rate limiting for API endpoints

### 2. Network Security
- Use HTTPS in production
- Implement firewall rules
- Restrict API access to authorized IPs
- Use VPN for administrative access

### 3. Data Protection
- Encrypt sensitive data at rest
- Implement proper backup procedures
- Follow GDPR/privacy regulations
- Regular security audits

## 🆘 Troubleshooting

### Common Issues

1. **Application Won't Start**
   - Check Python version and dependencies
   - Verify virtual environment activation
   - Check port availability

2. **API Key Errors**
   - Verify API keys are correct
   - Check API quotas and limits
   - Ensure proper environment variable setup

3. **SendPulse Integration Issues**
   - Verify API credentials
   - Check network connectivity
   - Review webhook configuration

4. **Knowledge Base Problems**
   - Check document formats (.docx supported)
   - Verify sufficient memory for processing
   - Check file permissions

### Support Contacts
- **Technical Issues**: Contact your system administrator
- **API Problems**: Refer to respective API documentation
- **Integration Issues**: Review integration logs and configuration

## 📊 Performance Optimization

### 1. System Optimization
- Increase RAM for large knowledge bases
- Use SSD storage for better performance
- Implement caching for frequently accessed data

### 2. Application Optimization
- Adjust chunk sizes for document processing
- Optimize vector search parameters
- Implement connection pooling for APIs

### 3. Monitoring Setup
- Use system monitoring tools (htop, iostat)
- Implement application performance monitoring
- Set up alerts for critical issues

## 🔄 Updates and Upgrades

### 1. Regular Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### 2. Application Updates
- Test updates in staging environment
- Backup configuration and data
- Follow semantic versioning guidelines
- Document changes and new features

### 3. Migration Procedures
- Export existing data before upgrades
- Test all integrations after updates
- Verify API compatibility
- Update documentation as needed

This completes the comprehensive client documentation for the AI Support Agent system. The system is now ready for production deployment with SendPulse integration. 