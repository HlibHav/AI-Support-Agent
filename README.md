# 🤖 AI Support Agent

A powerful AI-powered support agent with comprehensive database connectivity, Redmine integration, ticket management capabilities, and knowledge base functionality using LangGraph and Phoenix observability. This app provides intelligent insights, pattern recognition, interactive chat capabilities, database management, and direct ticket updates through Redmine's REST API.

## ✨ Key Features

- **🤖 AI-Powered Chat Interface**: Interactive chat with context-aware responses using Google Gemini
- **🗄️ Database Connectivity**: Connect to SQLite, PostgreSQL, MySQL databases with upload/download capabilities
- **📊 Ticket Analytics**: Advanced analytics and pattern recognition for support tickets
- **📚 Knowledge Base Integration**: Vector-based and text-based knowledge base with document processing
- **🔍 Advanced Search**: Vector similarity search and text-based search capabilities
- **📈 Real-time Monitoring**: Phoenix observability for performance tracking and debugging
- **🎫 Redmine Integration**: Direct ticket management and updates through Redmine REST API
- **💬 SendPulse Integration**: Live chat support integration
- **📁 File Upload**: Support for CSV, database files, and document upload
- **🔒 Secure Configuration**: Environment-based configuration with no hardcoded secrets

---

## 🚀 Deployment

### One-Click Deployment (Recommended)

**Quick Start:**
```bash
# Run the automated deployment script
./deploy.sh
```

The deployment script will:
- ✅ Check system requirements (Docker, Docker Compose)
- ✅ Create .env file from template if needed
- ✅ Validate environment variables
- ✅ Build and deploy all services
- ✅ Perform health checks
- ✅ Show access URLs and useful commands

### Manual Docker Compose Deployment

**1. Configure Environment Variables:**
```bash
# Copy environment template
cp env.template .env

# Edit with your API keys
nano .env
```

**2. Deploy with Docker Compose:**
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**3. Access Services:**
- **Streamlit App**: [http://localhost:8502](http://localhost:8502)
- **Knowledge API**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Phoenix Observability**: [http://localhost:6006](http://localhost:6006)

### Manual Docker Deployment

**1. Build and run Streamlit app:**
```bash
docker build -t ai-support-agent .
docker run -p 8502:8502 \
  -e GOOGLE_API_KEY=your_key_here \
  -v $(pwd)/issues\ \(10\).csv:/app/issues\ \(10\).csv:ro \
  -v $(pwd)/Knowledge:/app/Knowledge:ro \
  ai-support-agent
```

**2. Build and run Knowledge API:**
```bash
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your_key_here \
  -v $(pwd)/Knowledge:/app/Knowledge:ro \
  ai-support-agent python src/knowledge_api.py
```

### Production Deployment

**1. Cloud Deployment (AWS/GCP/Azure):**
```bash
# On your cloud instance
git clone <your-repo>
cd ai-support-agent

# Configure environment
cp env.template .env
nano .env  # Add your API keys

# Deploy with Docker Compose
docker-compose up -d

# Setup reverse proxy (nginx example)
sudo apt install nginx
sudo nano /etc/nginx/sites-available/ai-support-agent
```

**2. Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8502;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**3. SSL Certificate (Let's Encrypt):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

**4. Monitoring & Maintenance:**
```bash
# View application logs
docker-compose logs -f

# Update application
git pull
docker-compose down
docker-compose up -d --build

# Monitor system resources
docker stats
```

---

## 🔒 Environment Variables & Security

### Required Environment Variables

```bash
# Google Gemini API (REQUIRED)
GOOGLE_API_KEY=your_gemini_api_key_here

# Redmine Integration (OPTIONAL)
REDMINE_URL=https://your-redmine-instance.com
REDMINE_API_KEY=your_redmine_api_key_here

# SendPulse Integration (OPTIONAL)
SENDPULSE_API_ID=your_sendpulse_api_id
SENDPULSE_API_SECRET=your_sendpulse_api_secret
SENDPULSE_LIVE_CHAT_ID=your_live_chat_id
```

### Security Best Practices

- **Never commit API keys or secrets to version control**
- Use environment variables for all sensitive configuration
- The app does not store secrets in code or logs
- For production, use Docker secrets or a secrets manager
- Enable firewall rules to restrict access to necessary ports only
- Use HTTPS in production with a reverse proxy (nginx/Apache)
- Regularly rotate API keys and credentials

### Getting API Keys

**Google Gemini API Key:**
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (starts with "AIzaSy...")

**Redmine API Key:**
1. Log into your Redmine instance
2. Go to My Account → API access key
3. Click "Show" or "Generate" to get your key

**SendPulse API Credentials:**
1. Log into [SendPulse](https://login.sendpulse.com/)
2. Go to Settings → API
3. Create new API credentials
4. Copy API ID and API Secret

### Database Configuration (Optional)

The application now supports connecting to external databases for knowledge management:

```bash
# Database URLs (choose one)
DATABASE_URL=sqlite:///knowledge.db
DATABASE_URL=postgresql://user:password@host:port/database
DATABASE_URL=mysql://user:password@host:port/database
```

**Supported Database Types:**
- **SQLite**: Perfect for local development and small datasets
- **PostgreSQL**: Ideal for production environments with concurrent access
- **MySQL**: Good for web applications and medium-scale deployments

**Database Features:**
- Connect to existing databases containing knowledge documents
- Upload CSV files to create new databases
- Export query results to CSV
- Save and load database connection configurations
- Automatic knowledge document detection and extraction

---

## 🛠️ Troubleshooting & Production Readiness


### Common Deployment Issues

**1. Container won't start:**
```bash
# Check logs
docker-compose logs ai-support-agent

# Common causes:
# - Missing environment variables
# - Port conflicts
# - Insufficient memory
```

**2. Phoenix observability not working:**
```bash
# Check Phoenix status in the UI sidebar
# Ensure port 6006 is available
# Phoenix will show warning if initialization fails
```

**3. Knowledge base build fails:**
```bash
# Increase Docker memory limit
# Check available disk space
# Monitor container resources: docker stats
```

**4. API key errors:**
```bash
# Verify environment variables are set
docker-compose exec ai-support-agent env | grep API_KEY

# Check API key format and validity
# Ensure no extra spaces or characters
```

### Performance Optimization

- **Memory**: Minimum 4GB RAM, 8GB+ recommended for knowledge base
- **CPU**: 2+ cores recommended for concurrent operations
- **Storage**: 10GB+ free space for knowledge base and logs
- **Network**: Stable internet connection for API calls
- **Data**: Keep CSV files clean and properly encoded (UTF-8)

---

## ✨ Features

- **Interactive Dashboard**: Visual analytics with charts and key metrics
- **AI Chat Agent**: Natural language queries about your ticket data using LangGraph
- **Pattern Analysis**: Automatic clustering and trend identification
- **Advanced Search**: Powerful filtering and search capabilities
- **Observability**: Built-in Phoenix integration for monitoring agent performance
- **Ticket Management**: Detailed ticket viewer and analysis tools
- **Knowledge Base**: RAG integration with documentation files
- **Redmine Integration**: Direct connection to Redmine for ticket updates, status changes, and bulk operations
- **Knowledge Base API**: RESTful API for managing and updating the knowledge base
- **Bulk Operations**: Update multiple tickets at once through Redmine API

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- Your support tickets in CSV format
- Redmine instance with API access (optional, for ticket management)
- Redmine API key or credentials (optional)

### Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare your data**:
   - Ensure your CSV file is named `issues (10).csv` or update the path in the code
   - The CSV should have columns like: `#`, `Subject`, `Description`, `Status`, `Priority`, `Assignee`, etc.

4. **Run the application**:
   ```bash
   streamlit run streamlit_app.py --server.port 8502
   ```

5. **Access the app**:
   - Open your browser to `http://localhost:8502`
   - Your Gemini API key is pre-configured in the app
   - Start exploring your ticket data!

### Knowledge Base API (Optional)

To run the knowledge base API server alongside the main app:

1. **Start the API server**:
   ```bash
   cd src
   python knowledge_api.py
   ```

2. **Access the API**:
   - API Documentation: `http://localhost:8000/docs`
   - API Base URL: `http://localhost:8000`
   - Health Check: `http://localhost:8000/health`

3. **API Endpoints**:
   - `GET /stats` - Knowledge base statistics
   - `POST /build` - Build/rebuild knowledge base
   - `POST /search` - Search knowledge base
   - `POST /upload` - Upload documents
   - `GET /documents` - List documents
   - `DELETE /clear` - Clear knowledge base

## 📊 Application Features

### Dashboard
- **Key Metrics**: Total tickets, urgent tickets, new tickets, average processing time
- **Visual Analytics**: Status distribution, priority breakdown, project distribution
- **Team Performance**: Top assignees and workload distribution

### Chat Agent
- **Natural Language Queries**: Ask questions like "What are the most urgent tickets?" or "Show me payment-related issues"
- **Intelligent Analysis**: The agent uses LangGraph to provide contextual responses
- **Tool Integration**: Automatically uses analysis tools to gather relevant data

### Analysis Tools
- **Advanced Filtering**: Filter by status, priority, assignee, or date ranges
- **Text Search**: Full-text search across ticket descriptions and subjects
- **Clustering Analysis**: Automatically group similar tickets to identify patterns
- **Custom Queries**: Build complex queries for specific insights

### Ticket Details
- **Individual Ticket View**: Complete ticket information including description, notes, and timeline
- **Related Tickets**: Find similar or related tickets
- **Action History**: Track ticket updates and changes

### Redmine Management
- **Connection Management**: Connect to your Redmine instance with API key or basic auth
- **Ticket Operations**: View, update, assign, and change status of tickets
- **Bulk Updates**: Perform bulk operations on multiple tickets
- **Note Management**: Add private or public notes to tickets
- **Status Management**: Change ticket status with optional notes

### Knowledge Base API
- **RESTful Endpoints**: Full API for knowledge base management
- **Document Upload**: Upload new documents to the knowledge base
- **Search API**: Programmatic search through the knowledge base
- **Build Management**: Trigger knowledge base rebuilds via API
- **Statistics**: Get knowledge base metrics and status

### Database Manager
- **Multi-Database Support**: Connect to SQLite, PostgreSQL, and MySQL databases
- **File Upload**: Upload CSV files and database files directly through the interface
- **Query Interface**: Execute custom SQL queries with results export
- **Configuration Management**: Save and load database connection configurations
- **Knowledge Extraction**: Automatically detect and extract knowledge documents from databases
- **Data Export**: Export query results and knowledge documents to CSV format
- **Connection Testing**: Test database connections before saving configurations

## 🔧 Configuration

### Gemini API Key
- Enter your Gemini API key in the sidebar when prompted
- Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- The key is securely stored in your session for the current browser session
- Never commit API keys to version control

### Phoenix Observability

- **Global instrumentation**: Phoenix automatically launches when the application starts and instruments all LangChain-based agents
- **Modern OpenInference**: Uses the latest OpenInference instrumentation instead of legacy Phoenix trace modules
- **All agents monitored**: SimpleTicketAgent, EnhancedTicketAgent, and TicketAnalysisAgent are all automatically instrumented
- **Status indicator**: The sidebar shows Phoenix availability status and any initialization errors
- **Access the Phoenix UI**: Available at `http://localhost:6006` when running
- **Automatic setup**: No manual configuration needed - Phoenix starts globally and instruments all agents

**Phoenix Status Indicators:**
- ✅ **Phoenix observability active**: Phoenix is running and all agents are instrumented
- ⚠️ **Phoenix observability unavailable**: Phoenix failed to initialize (see reason below)

**Requirements:**
- `arize-phoenix>=3.0.0`
- `openinference-instrumentation-langchain>=0.1.43`

If Phoenix fails to initialize, the application will continue to work normally but without observability features.

## 💡 Usage Examples

### Example Queries for the Chat Agent

1. **General Analytics**:
   - "Give me a summary of all support tickets"
   - "What are the current trends in our support tickets?"
   - "How many tickets do we have by priority?"

2. **Specific Searches**:
   - "Show me all payment-related issues"
   - "Find tickets assigned to Anna Tinna"
   - "What urgent tickets are still open?"

3. **Pattern Analysis**:
   - "Cluster tickets to identify common themes"
   - "What types of issues are most common?"
   - "Which projects have the most support requests?"

4. **Specific Tickets**:
   - "Show me details for ticket #14398"
   - "Find all tickets similar to #14389"

### Knowledge Base Queries (after building)
- "How do I configure GDS hotel matching?"
- "What's the process for handling refunds?"
- "Show me the pricing setup guide"

### Combined Queries
- "Show me booking issues and explain the booking process"
- "Find payment tickets and the payment configuration docs"

## 🏗️ Architecture

### Components

1. **Data Processor** (`src/data_processor.py`):
   - Loads and cleans CSV data
   - Performs pattern analysis and clustering
   - Provides search and filtering capabilities

2. **Ticket Agent** (`src/ticket_agent.py`):
   - LangGraph-based intelligent agent
   - Multiple analysis tools
   - Phoenix integration for observability

3. **Streamlit App** (`streamlit_app.py`):
   - Web interface
   - Interactive dashboard
   - Chat interface

### Technology Stack

- **LangGraph**: Agent orchestration and workflow management
- **Phoenix**: LLM observability and monitoring ([Arize Phoenix](https://github.com/Arize-ai/phoenix))
- **Streamlit**: Web application framework
- **Google Gemini 1.5 Flash**: Fast and capable language model for analysis
- **Plotly**: Interactive visualizations
- **Pandas**: Data processing and analysis
- **Scikit-learn**: Machine learning for clustering

## 🔍 Data Format

Your CSV file should contain the following columns (adjust column names in the code if needed):

- `#`: Ticket ID
- `Subject`: Brief description
- `Description`: Detailed description
- `Status`: Current status (New, Open, Closed, etc.)
- `Priority`: Priority level (Low, Normal, High, Urgent, Immediate)
- `Assignee`: Person assigned to the ticket
- `Author`: Person who created the ticket
- `Created`: Creation date
- `Updated`: Last update date
- `Project`: Project or category
- `Last notes`: Recent updates or comments

## 🛠️ Customization

### Adding New Analysis Tools

To add new analysis capabilities:

1. Add a new tool method to the `TicketAnalysisAgent` class
2. Decorate it with `@tool`
3. Add it to the `self.tools` list
4. The agent will automatically discover and use the new tool

### Modifying Visualizations

Charts and visualizations are created using Plotly. Modify the chart creation functions in `streamlit_app.py` to customize:

- Chart types
- Color schemes  
- Layout and styling
- Data aggregations

### Custom Data Sources

To use different data sources:

1. Modify the `TicketDataProcessor` class to handle your data format
2. Update column mappings in the processing methods
3. Adjust the CSV loading logic as needed

## 🐛 Troubleshooting

### Common Issues

1. **"No module named 'phoenix'"**:
   - Install Phoenix: `pip install arize-phoenix`
   - Phoenix is optional; the app will work without it

2. **Gemini API Errors**:
   - Verify your API key is correct
   - Check your Google Cloud account has Gemini API enabled
   - Ensure you have sufficient quota for API calls

3. **CSV Loading Errors**:
   - Check that your CSV file exists and is readable
   - Verify column names match expected format
   - Ensure proper encoding (UTF-8 recommended)

4. **Performance Issues**:
   - Large datasets may take time to process
   - Consider filtering data or using smaller samples for testing
   - Phoenix UI may use additional memory

### Getting Help

- Check the Phoenix documentation: [Phoenix Docs](https://docs.arize.com/phoenix)
- LangGraph documentation: [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- Streamlit documentation: [Streamlit Docs](https://docs.streamlit.io/)

## 📈 Advanced Features

### Custom Clustering
- Adjust clustering parameters in the Analysis Tools
- Experiment with different numbers of clusters
- Use clustering insights to improve support workflows

### Agent Observability
- Monitor agent decision-making in Phoenix
- Track tool usage patterns
- Analyze conversation flows and bottlenecks

### Export Capabilities
- Export filtered data sets
- Save analysis results
- Generate reports for stakeholders

## 🚀 Next Steps

Consider these enhancements:


## Knowledge Base Setup

### Memory Requirements
Building the knowledge base requires significant memory due to:
- Loading SentenceTransformer model (~500MB)
- Creating FAISS embeddings

### Building Options

#### Option 1: Manual Build (Recommended)
1. Start the Streamlit app
2. Go to the "Knowledge Base" tab
3. Click "Build Knowledge Base"
4. Monitor progress and handle any memory issues

#### Option 2: Standalone Script
```bash
python build_knowledge_base.py
```

#### Option 3: Pre-built Indices
If you have pre-built indices, place them in the project root:
- `knowledge_vector_index.faiss`
- `knowledge_documents.pkl`

### Troubleshooting Memory Issues

If the build process gets killed:

1. **Close other applications** to free memory
2. **Use Activity Monitor** to check memory usage
3. **Restart the app** and try again
4. **Consider building offline** using the standalone script

### Memory-Efficient Strategies

1. **Batch processing**: Documents are processed in small batches
2. **Lazy loading**: Knowledge base only loads when needed
3. **Index persistence**: Once built, indices load instantly
4. **Garbage collection**: Memory is freed after each batch

## 🚀 Deployment Verification

After deployment, verify everything is working:

### 1. Service Health Checks
```bash
# Check all services are running
docker-compose ps

# Check service health
curl http://localhost:8502  # Streamlit app
curl http://localhost:8000/health  # Knowledge API
curl http://localhost:6006  # Phoenix (may take a moment)
```

### 2. Application Features
- ✅ **Dashboard**: Access metrics and visualizations
- ✅ **Chat Agent**: Test with sample queries
- ✅ **Redmine Integration**: Connect to your Redmine instance
- ✅ **Knowledge Base**: Build and search documentation
- ✅ **Phoenix Observability**: Monitor agent performance

### 3. Troubleshooting
```bash
# View logs for issues
docker-compose logs -f ai-support-agent
docker-compose logs -f knowledge-api

# Restart services if needed
docker-compose restart

# Check resource usage
docker stats
```

## 📊 Current Status

✅ **Production-ready deployment**  
✅ **Global Phoenix observability**  
✅ **Docker containerization**  
✅ **Environment variable configuration**  
✅ **Health checks and monitoring**  
✅ **Automated deployment script**  

## 📋 Deployment Checklist

Before going live:
- [ ] Configure all required environment variables
- [ ] Test API keys and external connections
- [ ] Verify data files are accessible
- [ ] Check system resources (memory, storage)
- [ ] Set up monitoring and alerting
- [ ] Configure reverse proxy and SSL (production)
- [ ] Set up backup procedures
- [ ] Document operational procedures

---
# AI-support-agent-
