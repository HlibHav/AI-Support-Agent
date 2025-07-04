# Dockerfile for AI Support Agent (Streamlit + FastAPI)

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose Streamlit port
EXPOSE 8502

# Expose FastAPI port (optional)
EXPOSE 8000

# Set Streamlit config (optional: disables telemetry, sets port)
ENV STREAMLIT_SERVER_PORT=8502
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Create knowledge data directory
RUN mkdir -p /app/knowledge_data

# Default command: run Streamlit app
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8502", "--server.address=0.0.0.0"]

# To run the FastAPI knowledge API instead, comment the above CMD and uncomment below:
# CMD ["python", "src/knowledge_api.py"] 