import os

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
app_args = {"agents_dir": AGENT_DIR, "web": True, "allow_origins": ["*"]}

# Create FastAPI app with ADK integration
app: FastAPI = get_fast_api_app(**app_args)

# Update app metadata
app.title = "Production ADK for CrowdGuard"
app.description = "Multi-Agent System for CrowdGuard"
app.version = "1.0.0"

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "production-adk-agent"}

@app.get("/")
def root():
    return {
        "service": "Production ADK for CrowdGuard",
        "description": "Multi-Agent System for CrowdGuard",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")