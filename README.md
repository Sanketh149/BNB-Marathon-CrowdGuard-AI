# 🛡️ CrowdGuard: AI-Powered Crowd Management and Early Warning System

## 🚀 Overview

CrowdGuard is a cutting-edge, serverless application designed to provide **real-time crowd analysis and proactive safety alerts** for public events, transport hubs, or large gatherings. Leveraging computer vision, a multi-agent AI architecture, and Google's Gemini LLM, the system analyzes video feeds to detect high-risk crowd behavior and automatically notifies relevant authorities via email before a stampede event can occur.

The entire application is built on a scalable, cost-effective **Google Cloud Run** architecture, enabling elastic scaling based on video processing load.

## 🌟 Key Features

- **Serverless Video Ingestion:** Publicly accessible React frontend hosted on Cloud Run for easy video upload.
- **Crowd Analysis ML:** A dedicated FastAPI backend with a machine learning model for high-accuracy crowd density and flow statistics.
- **Intelligent Multi-Agent Orchestration:** A sophisticated agent system runs parallel data gathering and sequential reasoning to produce a high-confidence stampede prediction.
- **Hybrid AI Integration:** Uses the **Gemini API** for context extraction in video processing and for professional, clear natural language generation when drafting official email alerts.
- **Proactive Alerting:** Automatically calls external news sources and sends a final, data-backed email to authorities upon high-risk prediction.

## 🛠️ Architecture and Components

The CrowdGuard system is a fully serverless, event-driven architecture hosted on Google Cloud.

### Core Architecture Summary

| Layer          | Component        | Technology / Service                | Role in CrowdGuard                                                                                                        |
| :------------- | :--------------- | :---------------------------------- | :------------------------------------------------------------------------------------------------------------------------ |
| **Frontend**   | User Interface   | React / **Cloud Run**               | Handles video upload and user interaction.                                                                                |
| **Backend**    | Video Processing | FastAPI / ML Model / **Cloud Run**  | Processes raw video, performs crowd analysis, calls Gemini for context, and generates crowd statistics.                   |
| **Storage**    | Data Lake        | **Cloud Storage (GCS)**             | Stores raw video files and output files (Crowd Statistics, Prediction Reports). Acts as the primary event trigger source. |
| **Agents**     | Orchestrator     | Python / **Cloud Run**              | Manages the parallel and sequential execution of all analytical agents.                                                   |
| **Core AI**    | LLM Services     | **Gemini API**                      | Used by the Backend for initial context and by the Email Agent for drafting alert communications.                         |
| **Deployment** | CI/CD            | **Cloud Build / Artifact Registry** | Manages container image building and deployment to Cloud Run.                                                             |

### 🧠 Multi-Agent Orchestration Flow

The intelligence of CrowdGuard lies in its coordinated multi-agent system, triggered by the `Crowd Statistics` file uploaded to GCS.

1.  **Parallel Data Gathering:**
    - **ML Stats Analyzer Agent:** Reads the latest `Crowd Statistics` from GCS (e.g., density, flow, sudden acceleration).
    - **News Agent:** Calls external news APIs and social media clients to gather real-time event context (e.g., local emergencies, event status, weather changes).
2.  **Sequential Reasoning:**
    - **Stampede Predictor Agent:** Takes the combined data from the News Agent and ML Analyzer Agent. It runs a final risk model to synthesize the contextual and quantitative data, outputting a definitive **Prediction Report**.
3.  **Action and Alerting:**
    - **Email Agent:** Receives the **Prediction Report**. It calls the **Gemini API** to generate a clear, professional, and actionable email draft and then sends the final alert to designated emergency/authority email addresses.

## 📁 Project Structure
```
CrowdGuard/
├── frontend/                    # 🌐 React Frontend Service (Cloud Run)
│   ├── dist/                    # Compiled production assets
│   ├── node_modules/
│   ├── public/
│   ├── src/                     # Source code (React/TypeScript)
│   │   └── ...
│   ├── Dockerfile               # Frontend container configuration
│   ├── package.json             # Node dependencies
│   ├── vite.config.ts           # Frontend build configuration
│   └── ...                      # (other config files)
│
├── ml-module/                   # 🧠 Video Processing / ML Backend Service (Cloud Run)
│   ├── analytics/               # Logic for generating crowd stats (post-detection)
│   ├── detection/               # Core ML model inference and object detection
│   ├── models/                  # Stored model weights/artifacts
│   ├── processing/              # Video decoding/pre-processing logic
│   ├── temp/
│   ├── config.py                # ML-specific configuration
│   ├── Dockerfile               # ML service container configuration
│   ├── download_model.py        # Script to fetch models during build/startup
│   ├── main.py                  # FastAPI entry point for ML processing
│   └── requirements.txt         # Python dependencies (incl. FastAPI, ML frameworks)
│
└── all-my-agents/               # 🤖 Multi-Agent Orchestration Service (Cloud Run)
    ├── .venv/
    ├── orchestrator_agent/      # Core multi-agent logic (Agent Development Kit equivalent)
    │   ├── news_agent.py        # 📰 Fetches external news/context
    │   ├── ml_analyzer_agent.py # 📊 Processes ML stats from GCS
    │   ├── predictor_agent.py   # 🔮 Combines data for prediction
    │   └── email_agent.py       # 📧 Drafts and sends alerts via Gemini
    ├── .env                     # Environment variables for agents
    ├── Dockerfile               # Agent service container configuration
    ├── main.py                  # FastAPI/Uvicorn entry point for agents
    └── requirements.txt         # Python dependencies (incl. Gemini SDK, agent framework)
```

## ⚙️ Setup and Deployment

This project relies entirely on Google Cloud services for deployment.

### Prerequisites

1.  A Google Cloud Project with Billing Enabled.
2.  The following APIs enabled: **Cloud Run, Cloud Build, Artifact Registry, Cloud Storage, Gemini API**.
3.  The **Gemini API Key** must be provided as a secret to the Cloud Run services.

### Environment Variables

GOOGLE_CLOUD_PROJECT=
GCS_BUCKET_NAME=
GCS_STATS_FILE=
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
ALERT_EMAIL=
NEWS_API_KEY=
BACKEND_API_HOST=
BACKEND_API_PORT=

### Deployment Steps

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/Sanketh149/BNB-Marathon-CrowdGuard-AI](https://github.com/Sanketh149/BNB-Marathon-CrowdGuard-AI.git)
    cd CrowdGuard
    ```
2.  **Build and Push Containers:**
    Use `cloud build` to build and push the separate services (Frontend, Backend, Agent Orchestrator) to Artifact Registry:
    ```bash
    # Example for one service (repeat for all three: frontend, backend, agent-orchestrator)
    gcloud builds submit --tag gcr.io/[PROJECT-ID]/crowdguard-backend ./backend-service
    ```
3.  **Deploy to Cloud Run:**
    Deploy each container image as a separate Cloud Run service. Ensure the Backend and Agent Orchestrator services are configured to accept traffic triggered by GCS (e.g., via Eventarc or internal service-to-service calls).

    ```bash
    # Deploying the Video Processing Backend
    gcloud run deploy crowdguard-backend \
        --image gcr.io/[PROJECT-ID]/crowdguard-backend \
        --platform managed \
        --region [REGION] \
        --set-env-vars GEMINI_API_KEY=[SECRET_KEY_REF]
    ```

## 📝 License

MIT License

## 🤝 Contribution

Contributions welcome! Please read our contributing guidelines first.

## 📧 Support

For issues and questions, please feel free to open a GitHub issue.
