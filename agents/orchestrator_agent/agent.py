import os
import json
import smtplib
import ssl
from email.message import EmailMessage
from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from newsapi import NewsApiClient
from google.cloud import storage

# --- Existing Helper Functions ---

def read_gcs_file(gcs_path: str) -> dict:
    """Reads a JSON file from Google Cloud Storage."""
    try:
        client = storage.Client()
        # Handle cases where gs:// might be missing or present
        clean_path = gcs_path.replace("gs://", "")
        bucket_name, blob_name = clean_path.split("/", 1)
        
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        file_content = blob.download_as_string()
        return json.loads(file_content)
    except Exception as e:
        return {"error": f"Failed to read GCS file: {str(e)}"}

class RetryingAgent(Agent):
    """An Agent wrapper that adds JSON parsing and retry logic."""
    max_retries: int = 2

    def __init__(self, *args, max_retries: int = 2, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries

    def invoke(self, *args, **kwargs) -> str:
        for attempt in range(self.max_retries + 1):
            try:
                response = super().invoke(*args, **kwargs)
                json.loads(response)
                return response
            except json.JSONDecodeError as e:
                print(f"Warning: Agent '{self.name}' invalid JSON. Retrying...")
                if attempt == self.max_retries:
                    return json.dumps({"error": "Invalid JSON Output", "details": str(e)})

# --- New Email Tool ---

def send_email_alert(subject: str, html_content: str) -> str:
    """
    Sends an HTML email using SMTP settings from environment variables.
    Args:
        subject: The subject line of the email.
        html_content: The HTML body of the email.
    """
    sender_email = os.environ.get("EMAIL_SENDER")
    email_password = os.environ.get("EMAIL_PASSWORD")
    receiver_email = os.environ.get("EMAIL_RECIPIENT")

    if not all([sender_email, email_password, receiver_email]):
        return "Error: Missing EMAIL_SENDER, EMAIL_PASSWORD, or EMAIL_RECIPIENT environment variables."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content("Please enable HTML to view this report.") # Fallback for non-HTML clients
    msg.add_alternative(html_content, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, email_password)
            server.send_message(msg)
        return "Email sent successfully."
    except Exception as e:
        return f"Failed to send email: {str(e)}"

# --- Agents Definitions ---

# 1. News Gatherer
target_location = os.environ.get("TARGET_LOCATION", "Unknown Location")
def search_news(query: str, language: str = "en", page_size: int = 10):
    try:
        newsapi = NewsApiClient(api_key=os.environ.get("NEWS_API_KEY"))
        return newsapi.get_everything(q=query, language=language, sort_by="relevancy", page_size=page_size)
    except Exception as e:
        return {"error": str(e)}

NEWS_INSTRUCTION_TEMPLATE = """You are an expert News Gathering Agent for an early warning system designed to prevent crowd-related incidents like stampedes.
        Your job is to find relevant external context for the following location: {location}.
        You should use your tools to search for information that could indicate a potential for dangerous crowd gatherings or stampedes.
        You should identify:
        1. Scheduled events (concerts, sports, protests, festivals, large public gatherings) that could lead to large crowds.
        2. Social media reports (complaints about overcrowding, sightings of unexpectedly large crowds, discussions of unofficial gatherings).
        3. Weather conditions (sudden changes, extreme weather) that could influence crowd behavior.
        4. Nearby incidents (traffic jams, accidents, public transport disruptions) that could concentrate people in an area.

        Your goal is to provide information that helps in assessing the risk of a stampede or other crowd-related dangers.
        Your output MUST be a single, valid JSON object and nothing else. Do not include any text or markdown formatting like ```json.
        The JSON object should match the following `ExternalContext` structure:

        ```json
        {{
          "scheduled_events": [
            {{
              "name": "Event Name",
              "category": "concert/sports/protest/festival/gathering",
              "location": "Event Location",
              "time": "Event Time",
              "source": "URL or reference"
            }}
          ],
          "social_media_reports": [
            {{
              "platform": "e.g., Twitter, Facebook",
              "report": "Text of the report about overcrowding or large gatherings",
              "user": "Username",
              "timestamp": "Time of report",
              "link": "URL to post"
            }}
          ],
          "weather_conditions": {{
            "summary": "e.g., 'Sudden thunderstorm expected'",
            "alerts": ["Weather warning details"]
          }},
          "nearby_incidents": [
            {{
              "type": "traffic_jam/accident/transport_disruption",
              "description": "Details of the incident"
            }}
          ]
        }}
        ```
"""
formatted_news_instruction = NEWS_INSTRUCTION_TEMPLATE.format(location=target_location)

news_gatherer_agent = RetryingAgent(
    name="news_gatherer",
    model="gemini-2.5-flash",
    tools=[search_news],
    description="Gathers external context from news and social media",
    instruction=formatted_news_instruction,
)

# 2. ML Stats Analyzer
GCS_PATH = os.environ.get("GCS_PATH", "gs://crowdguard-videos/crowd_stats/latest_stats.json")
ML_INSTRUCTION_TEMPLATE = """You are an ML Stats Analyzer Agent for the CrowdGuard AI safety system. Your role is to analyze crowd statistics from an ML model and categorize the risk level.
The ML model's output is located at the following Google Cloud Storage (GCS) path: {gcs_path}.
Analyze the comprehensive statistics paying close attention to `risk_level`, `risk_score`, and `anomaly_type`.
Categorize the risk of a dangerous situation (like a stampede) into one of the following levels: "Low", "Medium", "High", or "Critical".
Provide a brief justification for your assessment.
Your output MUST be a single, valid JSON object and nothing else. Do not include any text or markdown formatting like ```json.
The JSON object should include the original data from the GCS file along with your analysis.
```json
{{ "analysis": {{ "risk_category": "High", "justification": "Density score has spiked..." }}, "original_data": {{ "timestamp": "...", "location": "...", "total_count": "...", "density_score": "...", "flow_rate": "...", "risk_level": "...", "risk_score": "...", "anomaly_type": "...", "high_density_zones": [], "clusters": [] }} }}
```"""
formatted_ml_instruction = ML_INSTRUCTION_TEMPLATE.format(gcs_path=GCS_PATH)

ml_stats_analyzer_agent = RetryingAgent(
    name="ml_stats_analyzer",
    model="gemini-2.5-flash",
    tools=[read_gcs_file],
    description="Analyzes ML crowd statistics",
    instruction=formatted_ml_instruction
)

# 3. Stampede Predictor
STAMPEDE_PREDICTOR_INSTRUCTION = """You are a Stampede Predictor Agent. Your task is to synthesize information from two sources: the ML Stats Analyzer and the News Gatherer.

1.  **Check for Errors**: First, check if the inputs from `ml_stats_analyzer` or `news_gatherer` contain an 'error' key. If so, report the error and stop.
2.  **Analyze the ML Stats**: If the input is valid, review the `analysis` and `original_data` from the `ml_stats_analyzer`. This gives you the on-the-ground reality from sensor data.
3.  **Analyze the External Context**: Review the `scheduled_events`, `social_media_reports`, `weather_conditions`, and `nearby_incidents` from the `news_gatherer`. This provides external context.
4.  **Synthesize and Correlate**:
    -   Does the external context explain the ML stats? (e.g., a concert explains high density).
    -   Does the external context suggest a higher risk than the ML stats alone indicate? (e.g., social media reports of unrest, plus rising density).
    -   Is there a mismatch that is concerning? (e.g., high density with no scheduled event).
5.  **Produce a Final Report**: Based on your synthesis, create a consolidated JSON report.
6.  **Recommend Actions**: Crucially, suggest concrete, actionable steps that can be taken to mitigate the risk based on the consolidated risk level.

If you receive an error from a sub-agent, your output should be a JSON object indicating the source of the failure, like this: `{{ "error": "Failed to get data from ml_stats_analyzer.", "details": "..." }}`.

Your output MUST be a single, valid JSON object and nothing else. Do not include any text or markdown formatting like ```json.
The final JSON should look like this:
```json
{
  "consolidated_risk_level": "Low/Medium/High/Critical",
  "summary": "A brief summary of the overall situation and your reasoning.",
  "correlation_analysis": "Describe the correlation (or lack thereof) between the ML data and external news.",
  "contributing_factors": {
    "ml_stats": { "analysis": { "risk_category": "High", "justification": "Density score has spiked..." }, "original_data": { "timestamp": "...", "location": "...", "total_count": "...", "density_score": "...", "flow_rate": "...", "risk_level": "...", "risk_score": "...", "anomaly_type": "...", "high_density_zones": [], "clusters": [] } },
    "external_context": {
      "scheduled_events": [],
      "social_media_reports": [],
      "weather_conditions": {},
      "nearby_incidents": []
    }
  },
  "recommended_actions": [
    "Divert incoming foot traffic from the main entrance immediately.",
    "Dispatch security personnel to identified high-density zones to create pathways.",
    "Make a public announcement advising attendees to move towards secondary exits."
  ]
}
```
"""

stampede_predictor_agent = RetryingAgent(
    name="stampede_predictor",
    model="gemini-2.5-flash",
    description="Synthesizes ML stats and external news to predict stampede risk.",
    instruction=STAMPEDE_PREDICTOR_INSTRUCTION,
)

# --- 4. New Email Notification Agent ---

EMAIL_AGENT_INSTRUCTION = """You are the Communication Officer for the CrowdGuard system.
Your input is a raw JSON report containing a 'consolidated_risk_level', 'summary', 'correlation_analysis', and 'recommended_actions'.

Your goal is to transform this JSON into a professional, visually appealing HTML email body and send it using the `send_email_alert` tool.

**Formatting Guidelines:**
1.  **Color Coding**: Use inline CSS. If the risk is 'High' or 'Critical', use a Red/Orange theme. If 'Medium', use Yellow. If 'Low', use Green/Blue.
2.  **Header**: Create a prominent header: "CrowdGuard Risk Report: [Risk Level]".
3.  **Structure**:
    * **Executive Summary**: The 'summary' field.
    * **Action Plan**: The 'recommended_actions' as a clean bulleted list (`<ul>`).
    * **Data Correlation**: The 'correlation_analysis'.
    * **Technical Details**: Create a small HTML table showing the 'ml_stats' key metrics (Density Score, Flow Rate).
4.  **Tone**: Professional, urgent, and clear.

**Execution:**
1.  Construct the HTML string.
2.  Call `send_email_alert` with the subject "URGENT: CrowdGuard Risk Assessment - [Risk Level]" and the generated HTML content.
3.  Output a simple confirmation message.
"""

email_notifier_agent = RetryingAgent(
    name="email_notifier",
    model="gemini-2.5-flash-lite",
    tools=[send_email_alert],
    description="Formats the risk report into HTML and sends an email notification.",
    instruction=EMAIL_AGENT_INSTRUCTION
)

# --- Pipeline Assembly ---

# Parallel agent to run data gathering concurrently
parallel_data_gathering_agent = ParallelAgent(
    name="parallel_data_gathering_agent",
    sub_agents=[ml_stats_analyzer_agent, news_gatherer_agent],
    description="Runs the ML Stats Analyzer and News Gatherer in parallel.",
)

# Sequential agent to define the main workflow
# Added email_notifier_agent to the end of the list
sequential_pipeline_agent = SequentialAgent(
    name="stampede_prediction_pipeline",
    sub_agents=[
        parallel_data_gathering_agent, 
        stampede_predictor_agent, 
        email_notifier_agent
    ],
    description="Coordinates data gathering, risk prediction, and email notification.",
)

root_agent = sequential_pipeline_agent