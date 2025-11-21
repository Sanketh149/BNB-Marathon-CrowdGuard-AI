"""Configuration management for ML module."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
TEMP_DIR = BASE_DIR / "temp"

# Create directories if they don't exist
MODELS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# GCP Configuration
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
GCS_STATS_FILE = os.getenv("GCS_STATS_FILE", "")

# ML Model Configuration
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8m.pt")  # Medium model for better accuracy
YOLO_MODEL_PATH = MODELS_DIR / YOLO_MODEL
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.2"))  # Balanced for accuracy
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.3"))  # Lower to detect overlapping people

# Video Processing Configuration
FRAME_SAMPLE_RATE = int(os.getenv("FRAME_SAMPLE_RATE", "3"))  # Process every Nth frame
MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "500"))

# Crowd Analytics Thresholds
DENSITY_GRID_SIZE = 50  # pixels per grid cell
HIGH_DENSITY_THRESHOLD = 5  # people per grid cell
ANOMALY_MOVEMENT_THRESHOLD = 50  # pixels per second
CLUSTERING_EPS = 100  # DBSCAN clustering distance
MIN_CLUSTER_SIZE = 10  # Minimum people for crowd cluster

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8080"))
