#!/bin/bash

# AI Support Agent - Quick Deployment Script
# This script automates the deployment process

set -e

echo "🚀 AI Support Agent - Deployment Script"
echo "========================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp env.template .env
    echo "✅ Created .env file from template"
    echo "⚠️  Please edit .env file with your API keys before continuing"
    echo "   Required: GOOGLE_API_KEY"
    echo "   Optional: REDMINE_URL, REDMINE_API_KEY, SENDPULSE_* variables"
    echo ""
    read -p "Press Enter when you have configured your .env file..."
fi

# Validate required environment variables
echo "🔍 Validating environment variables..."
source .env

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "❌ GOOGLE_API_KEY is required in .env file"
    exit 1
fi

if [ "$GOOGLE_API_KEY" = "your_gemini_api_key_here" ]; then
    echo "❌ Please set a real GOOGLE_API_KEY in .env file"
    exit 1
fi

echo "✅ Environment variables validated"

# Check if data file exists
if [ ! -f "issues (10).csv" ]; then
    echo "⚠️  Data file 'issues (10).csv' not found"
    echo "   Please ensure your ticket data CSV file is named 'issues (10).csv'"
    echo "   Or update the volume mapping in docker-compose.yml"
fi

# Check if Knowledge directory exists
if [ ! -d "Knowledge" ]; then
    echo "⚠️  Knowledge directory not found"
    echo "   The knowledge base will be empty without this directory"
fi

# Build and deploy
echo "🏗️  Building and deploying services..."
docker-compose down --remove-orphans
docker-compose build --no-cache
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check Streamlit app
if curl -f http://localhost:8502 >/dev/null 2>&1; then
    echo "✅ Streamlit app is running at http://localhost:8502"
else
    echo "❌ Streamlit app is not responding"
    echo "   Check logs: docker-compose logs ai-support-agent"
fi

# Check Knowledge API
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ Knowledge API is running at http://localhost:8000"
else
    echo "❌ Knowledge API is not responding"
    echo "   Check logs: docker-compose logs knowledge-api"
fi

# Show final status
echo ""
echo "🎉 Deployment complete!"
echo "========================================"
echo "📊 Streamlit App: http://localhost:8502"
echo "🔧 Knowledge API: http://localhost:8000/docs"
echo "🔍 Phoenix Observability: http://localhost:6006"
echo ""
echo "📋 Useful commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo "   Update app: git pull && docker-compose up -d --build"
echo ""
echo "🛠️  If you encounter issues, check the logs and ensure:"
echo "   - Your API keys are correctly set in .env"
echo "   - Ports 8502, 8000, and 6006 are available"
echo "   - You have sufficient memory (4GB+ recommended)"
echo ""
echo "Happy analyzing! 🤖" 