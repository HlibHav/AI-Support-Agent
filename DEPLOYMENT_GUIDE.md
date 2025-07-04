# AI Support Agent - Deployment Guide

## 🚀 Quick Deployment Steps

### Prerequisites
- Ubuntu 18.04+ or similar Linux distribution
- Python 3.9+ installed
- 4GB+ RAM (8GB+ recommended)
- Stable internet connection

### 1. System Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3 python3-pip python3-venv build-essential -y
```

### 2. Application Installation
```bash
# Create application directory
sudo mkdir -p /opt/ai-support-agent
sudo chown $USER:$USER /opt/ai-support-agent
cd /opt/ai-support-agent

# Extract application files here
# (Upload your project files)

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. ⚠️ CRITICAL: API Key Configuration

**BEFORE DEPLOYMENT**, you MUST configure your API keys:

#### Step 1: Create Environment File
```bash
# Copy the template
cp env.template .env

# Edit the configuration
nano .env
```

#### Step 2: Configure Required API Keys

**🔑 Google Gemini API Key (REQUIRED)**
```env
GOOGLE_API_KEY=your_actual_gemini_api_key_here
```

**How to get your Gemini API key:**
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (starts with "AIzaSy...")
5. Paste it in your `.env` file

**🔑 SendPulse API Credentials (REQUIRED for Live Chat)**
```env
SENDPULSE_API_ID=your_sendpulse_api_id
SENDPULSE_API_SECRET=your_sendpulse_api_secret
SENDPULSE_LIVE_CHAT_ID=your_live_chat_id
```

**How to get SendPulse credentials:**
1. Log in to [SendPulse](https://login.sendpulse.com/)
2. Go to Settings → API
3. Create new API credentials
4. Copy API ID and API Secret
5. Go to Messengers → Live Chat
6. Copy your Chat ID from widget settings

**🔑 Redmine API Key (OPTIONAL)**
```env
REDMINE_URL=https://your-redmine-instance.com
REDMINE_API_KEY=your_redmine_api_key_here
```

#### Step 3: Complete Configuration Example
```env
# Google Gemini API Configuration
GOOGLE_API_KEY=youe API key
GEMINI_MODEL=models/gemini-1.5-flash

# SendPulse Configuration
SENDPULSE_API_ID=1234567
SENDPULSE_API_SECRET=abc123def456ghi789
SENDPULSE_LIVE_CHAT_ID=chat_12345

# Redmine Configuration (Optional)
REDMINE_URL=https://redmine.company.com
REDMINE_API_KEY=def456ghi789abc123

# Application Configuration
APP_PORT=8502
API_PORT=8000
DEBUG_MODE=false
```

### 4. Test Configuration
```bash
# Test the setup
source venv/bin/activate
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

# Test API keys
api_key = os.getenv('GOOGLE_API_KEY')
if api_key:
    print('✅ Gemini API key configured')
else:
    print('❌ Gemini API key missing')

sendpulse_id = os.getenv('SENDPULSE_API_ID')
if sendpulse_id:
    print('✅ SendPulse API configured')
else:
    print('❌ SendPulse API missing')
"
```

### 5. Start the Application
```bash
# Start the main application
streamlit run streamlit_app.py --server.port 8502 --server.address 0.0.0.0 &

# Start the Knowledge Base API
python -m uvicorn src.knowledge_api:app --host 0.0.0.0 --port 8000 &
```

### 6. Start SendPulse Integration
```bash
# Create SendPulse service script
cat > start_sendpulse.py << 'EOF'
import os
import asyncio
from dotenv import load_dotenv
from src.sendpulse_integration import create_sendpulse_integration
from src.enhanced_ticket_agent import EnhancedTicketAgent

# Load environment variables
load_dotenv()

# Initialize AI agent
ai_agent = EnhancedTicketAgent(os.getenv('GOOGLE_API_KEY'))

# Create SendPulse integration
integration = create_sendpulse_integration(
    api_id=os.getenv('SENDPULSE_API_ID'),
    api_secret=os.getenv('SENDPULSE_API_SECRET'),
    live_chat_id=os.getenv('SENDPULSE_LIVE_CHAT_ID'),
    ai_agent=ai_agent
)

# Start polling
asyncio.run(integration.start_polling())
EOF

# Start SendPulse integration
python start_sendpulse.py &
```

### 7. Verify Deployment
```bash
# Check if services are running
curl http://localhost:8502  # Should return HTML
curl http://localhost:8000/health  # Should return {"status": "healthy"}

# Check processes
ps aux | grep streamlit
ps aux | grep uvicorn
ps aux | grep sendpulse
```

## 🔧 Production Deployment (Systemd)

### 1. Create Systemd Services

**Main Application Service:**
```bash
sudo tee /etc/systemd/system/ai-support-agent.service > /dev/null << 'EOF'
[Unit]
Description=AI Support Agent
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/ai-support-agent
Environment=PATH=/opt/ai-support-agent/venv/bin
ExecStart=/opt/ai-support-agent/venv/bin/streamlit run streamlit_app.py --server.port 8502 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

**Knowledge Base API Service:**
```bash
sudo tee /etc/systemd/system/ai-support-api.service > /dev/null << 'EOF'
[Unit]
Description=AI Support Agent API
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/ai-support-agent
Environment=PATH=/opt/ai-support-agent/venv/bin
ExecStart=/opt/ai-support-agent/venv/bin/python -m uvicorn src.knowledge_api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

**SendPulse Integration Service:**
```bash
sudo tee /etc/systemd/system/ai-support-sendpulse.service > /dev/null << 'EOF'
[Unit]
Description=AI Support Agent SendPulse Integration
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/ai-support-agent
Environment=PATH=/opt/ai-support-agent/venv/bin
ExecStart=/opt/ai-support-agent/venv/bin/python start_sendpulse.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 2. Enable and Start Services
```bash
# Replace YOUR_USERNAME with your actual username
sudo sed -i 's/YOUR_USERNAME/'$USER'/g' /etc/systemd/system/ai-support-*.service

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable ai-support-agent
sudo systemctl enable ai-support-api
sudo systemctl enable ai-support-sendpulse

# Start services
sudo systemctl start ai-support-agent
sudo systemctl start ai-support-api
sudo systemctl start ai-support-sendpulse

# Check status
sudo systemctl status ai-support-agent
sudo systemctl status ai-support-api
sudo systemctl status ai-support-sendpulse
```

## 🌐 Nginx Reverse Proxy (Optional)

### 1. Install Nginx
```bash
sudo apt install nginx -y
```

### 2. Configure Nginx
```bash
sudo tee /etc/nginx/sites-available/ai-support-agent > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # Change this to your domain

    location / {
        proxy_pass http://127.0.0.1:8502;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/ai-support-agent /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

## 📝 SendPulse Live Chat Setup

### 1. Configure SendPulse Dashboard
1. Log in to [SendPulse](https://login.sendpulse.com/messengers/connect/live-chat/)
2. Go to **Messengers** → **Live Chat**
3. Create or select your chat widget
4. Configure automation rules:
   - Set AI response triggers
   - Configure handoff conditions
   - Set working hours

### 2. Widget Integration
Add the SendPulse chat widget to your website:
```html
<!-- SendPulse Live Chat Widget -->
<script>
  (function(d,u,ac){
    var s=d.createElement('script');
    s.type='text/javascript';
    s.src='https://w.sendpulse.com/js/push/CHAT_ID.js';
    s.async=true;
    s.onload=s.onreadystatechange=function(){
      var rs=this.readyState;
      if(rs && rs!='complete' && rs!='loaded')return;
      try{
        ac.initLiveChat();
      }catch(e){}
    };
    d.getElementsByTagName('head')[0].appendChild(s);
  })(document,'https://w.sendpulse.com/js/push/CHAT_ID.js',{
    initLiveChat:function(){
      if(typeof ac_add_track!=='undefined'){
        ac_add_track(CHAT_ID,'your-tracking-id');
      }
    }
  });
</script>
```

## 🔍 Monitoring and Logs

### View Service Logs
```bash
# Application logs
sudo journalctl -u ai-support-agent -f

# API logs
sudo journalctl -u ai-support-api -f

# SendPulse integration logs
sudo journalctl -u ai-support-sendpulse -f
```

### Health Checks
```bash
# Check all services
sudo systemctl status ai-support-agent ai-support-api ai-support-sendpulse

# Test endpoints
curl http://localhost:8502/_stcore/health
curl http://localhost:8000/health
```

## 🚨 Important Security Notes

### 1. API Key Security
- **NEVER** commit `.env` files to version control
- Use proper file permissions: `chmod 600 .env`
- Rotate API keys regularly
- Monitor API usage and quotas

### 2. Firewall Configuration
```bash
# Allow required ports
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw allow 8502  # Streamlit (if not using Nginx)
sudo ufw allow 8000  # API (if not using Nginx)
sudo ufw enable
```

### 3. SSL Certificate (Production)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

## 🎯 Final Checklist

Before going live, verify:

- [ ] All API keys are configured in `.env`
- [ ] Google Gemini API key is valid and has quota
- [ ] SendPulse API credentials are working
- [ ] All services are running (`systemctl status`)
- [ ] Web interface is accessible
- [ ] Knowledge base API is responding
- [ ] SendPulse integration is polling
- [ ] Logs show no errors
- [ ] Firewall is configured
- [ ] SSL certificate is installed (production)

## 🆘 Quick Troubleshooting

**Application won't start:**
```bash
# Check logs
sudo journalctl -u ai-support-agent -n 50

# Check Python environment
source venv/bin/activate
python -c "import streamlit; print('OK')"
```

**API key errors:**
```bash
# Verify environment variables
source venv/bin/activate
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Gemini API:', os.getenv('GOOGLE_API_KEY')[:10] + '...' if os.getenv('GOOGLE_API_KEY') else 'Missing')
print('SendPulse ID:', os.getenv('SENDPULSE_API_ID') or 'Missing')
"
```

**SendPulse not responding:**
```bash
# Check SendPulse integration
sudo journalctl -u ai-support-sendpulse -n 20
```

Your AI Support Agent is now ready for deployment with SendPulse integration! 
