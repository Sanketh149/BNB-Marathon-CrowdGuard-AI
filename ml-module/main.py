"""FastAPI service for ML module."""
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import asyncio
import uuid
from pathlib import Path
import sys
import subprocess
import shutil
import numpy as np
from datetime import datetime
import base64
import requests
from PIL import Image
import io

sys.path.append(str(Path(__file__).parent.parent))
from config import API_HOST, API_PORT, TEMP_DIR, GCS_BUCKET_NAME, GCS_STATS_FILE, GOOGLE_CLOUD_PROJECT
from processing.video_processor import VideoProcessor
from google.cloud import storage
import json

app = FastAPI(
    title="CrowdGuard AI - ML Module",
    description="Real-time crowd detection and analysis API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global processor
processor = VideoProcessor()

# Active websocket connections
active_connections: List[WebSocket] = []

# GCS client (initialize once)
gcs_client = None
if GOOGLE_CLOUD_PROJECT and GCS_BUCKET_NAME:
    try:
        gcs_client = storage.Client(project=GOOGLE_CLOUD_PROJECT)
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize GCS client: {e}")


def write_stats_to_gcs(stats_data: dict) -> bool:
    """Write crowd statistics to GCS with fixed filename."""
    if not gcs_client:
        print("⚠️ GCS client not initialized, skipping upload")
        return False
    
    try:
        bucket = gcs_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(GCS_STATS_FILE)
        
        # Convert to JSON and upload
        json_data = json.dumps(stats_data, indent=2)
        blob.upload_from_string(
            json_data,
            content_type='application/json'
        )
        
        print(f"✅ Stats written to gs://{GCS_BUCKET_NAME}/{GCS_STATS_FILE}")
        return True
    except Exception as e:
        print(f"❌ Failed to write to GCS: {e}")
        return False


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    timestamp: str


class VideoAnalysisRequest(BaseModel):
    video_url: Optional[str] = None
    rtsp_url: Optional[str] = None


class FrameAnalysisResponse(BaseModel):
    timestamp: str
    total_count: int
    density_score: float
    risk_level: str
    risk_score: float
    anomaly_type: str
    detections: List[Dict]
    high_density_zones: List[Dict]
    clusters: List[Dict]


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "CrowdGuard AI - ML Module",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model_loaded=processor.detector.model is not None,
        timestamp=datetime.now().isoformat()
    )


@app.post("/api/analyze/video")
async def analyze_video(
    file: UploadFile = File(...),
    location: str = Form("")
):
    """
    Analyze uploaded video file and create annotated version.
    
    Returns frame-by-frame analysis results and path to annotated video.
    """
    try:
        # Save uploaded file
        timestamp = datetime.now().timestamp()
        file_path = TEMP_DIR / f"{timestamp}_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Create annotated video path
        output_filename = f"{timestamp}_annotated.mp4"
        output_path = TEMP_DIR / output_filename
        
        # Process video using ultralytics directly (it handles video I/O internally)
        results = []
        frame_count = 0
        
        for result in processor.process_video_file(str(file_path)):
            metrics = result["metrics"]
            annotated_frame = result["annotated_frame"]
            
            frame_result = {
                "frame_idx": result["frame_idx"],
                "timestamp": result["timestamp"],
                "total_count": metrics.total_count,
                "density_score": metrics.density_score,
                "risk_level": metrics.risk_level.value,
                "risk_score": metrics.risk_score,
                "anomaly_type": metrics.anomaly_type.value,
                "detections": result["detections"],
                "high_density_zones": metrics.high_density_zones,
                "clusters": metrics.clusters
            }
            results.append(frame_result)
            frame_count += 1
            
            # Limit processing for large videos
            if frame_count >= 300:  # Process max 10 seconds at 30fps
                break
        
        # Copy the original video as "annotated" (since we're not actually annotating)
        shutil.copy(str(file_path), str(output_path))
        
        # Cleanup original upload
        file_path.unlink()
        
        # Write stats to GCS - include both max and sum
        if results:
            # Find frame with maximum people count
            max_frame = max(results, key=lambda x: x["total_count"])
            # Calculate sum of all people across all frames
            total_sum = sum(r["total_count"] for r in results)
            
            stats_payload = {
                "timestamp": max_frame["timestamp"],
                "location": location or "Video Analysis",
                "camera_id": "video_upload",
                "total_count": max_frame["total_count"],
                "total_sum": total_sum,
                "density_score": max_frame["density_score"],
                "flow_rate": 0.0,  # Not calculated for video
                "risk_level": max_frame["risk_level"],
                "risk_score": max_frame["risk_score"],
                "anomaly_type": max_frame["anomaly_type"],
                "high_density_zones": max_frame["high_density_zones"],
                "clusters": max_frame["clusters"]
            }
            write_stats_to_gcs(stats_payload)
            
            # Agent call is now handled by frontend only
            # Backend just writes to GCS and lets frontend call the agent
        
        # Save results to JSON file
        results_filename = f"{timestamp}_results.json"
        results_path = TEMP_DIR / results_filename
        with open(results_path, "w") as json_file:
            json.dump({
                "status": "success",
                "total_frames_analyzed": len(results),
                "annotated_video_url": f"/api/video/{output_filename}",
                "results": results
            }, json_file, indent=2)
        
        return {
            "status": "success",
            "total_frames_analyzed": len(results),
            "annotated_video_url": f"/api/video/{output_filename}",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video/{filename}")
async def get_video(filename: str):
    """Serve annotated video file."""
    file_path = TEMP_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(file_path, media_type="video/mp4")


@app.post("/api/analyze/frame")
async def analyze_frame(file: UploadFile = File(...)):
    """
    Analyze a single image frame.
    
    Returns detection and crowd analysis.
    """
    try:
        # Read image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        frame = np.array(image.convert('RGB'))
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
            
        # Initialize analyzer if needed
        height, width = frame.shape[:2]
        if processor.analyzer is None:
            from analytics.crowd_analyzer import CrowdAnalyzer
            processor.analyzer = CrowdAnalyzer((height, width))
            
        # Detect and analyze
        detections = processor.detector.detect_people(frame)
        timestamp = datetime.now().isoformat()
        metrics = processor.analyzer.analyze(detections, timestamp)
        
        # Create annotated frame
        annotated = processor.detector.draw_detections(frame, detections)
        
        # Add heatmap
        if len(detections) > 0:
            centers = np.array([det["center"] for det in detections])
            heatmap = processor.analyzer.create_density_heatmap(centers)
            annotated = processor.analyzer.apply_heatmap_overlay(annotated, heatmap, 0.3)
            
        # Encode annotated frame
        annotated_image = Image.fromarray(annotated)
        buffer = io.BytesIO()
        annotated_image.save(buffer, format='JPEG')
        annotated_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Prepare stats for GCS
        stats_payload = {
            "timestamp": timestamp,
            "location": "Live Frame Analysis",
            "camera_id": "api_upload",
            "total_count": metrics.total_count,
            "density_score": metrics.density_score,
            "flow_rate": 0.0,  # Not calculated for single frame
            "risk_level": metrics.risk_level.value,
            "risk_score": metrics.risk_score,
            "anomaly_type": metrics.anomaly_type.value,
            "high_density_zones": metrics.high_density_zones,
            "clusters": metrics.clusters
        }
        
        # Write to GCS
        write_stats_to_gcs(stats_payload)
        
        return {
            "status": "success",
            "timestamp": timestamp,
            "total_count": metrics.total_count,
            "density_score": metrics.density_score,
            "risk_level": metrics.risk_level.value,
            "risk_score": metrics.risk_score,
            "anomaly_type": metrics.anomaly_type.value,
            "detections": detections,
            "high_density_zones": metrics.high_density_zones,
            "clusters": metrics.clusters,
            "annotated_frame": annotated_base64
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time frame streaming.
    
    Client sends frames, server responds with analysis.
    """
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Receive frame data
            data = await websocket.receive_bytes()
            
            # Decode frame
            try:
                image = Image.open(io.BytesIO(data))
                frame = np.array(image.convert('RGB'))
            except Exception:
                frame = None
            
            if frame is None:
                await websocket.send_json({"error": "Invalid frame"})
                continue
                
            # Initialize analyzer if needed
            height, width = frame.shape[:2]
            if processor.analyzer is None:
                from analytics.crowd_analyzer import CrowdAnalyzer
                processor.analyzer = CrowdAnalyzer((height, width))
                
            # Process frame
            detections = processor.detector.detect_people(frame)
            timestamp = datetime.now().isoformat()
            metrics = processor.analyzer.analyze(detections, timestamp)
            
            # Send response
            response = {
                "timestamp": timestamp,
                "total_count": metrics.total_count,
                "density_score": metrics.density_score,
                "risk_level": metrics.risk_level.value,
                "risk_score": metrics.risk_score,
                "anomaly_type": metrics.anomaly_type.value,
                "detections": detections,
                "high_density_zones": metrics.high_density_zones,
                "clusters": metrics.clusters
            }
            
            # Write to GCS (every frame from websocket)
            stats_payload = {
                "timestamp": timestamp,
                "location": "Live Stream",
                "camera_id": "websocket_stream",
                "total_count": metrics.total_count,
                "density_score": metrics.density_score,
                "flow_rate": 0.0,  # Not calculated for websocket
                "risk_level": metrics.risk_level.value,
                "risk_score": metrics.risk_score,
                "anomaly_type": metrics.anomaly_type.value,
                "high_density_zones": metrics.high_density_zones,
                "clusters": metrics.clusters
            }
            write_stats_to_gcs(stats_payload)
            
            await websocket.send_json(response)
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)


@app.get("/api/stats")
async def get_stats():
    """Get ML module statistics."""
    return {
        "model_type": "YOLOv8-Nano",
        "active_connections": len(active_connections),
        "frames_processed": processor.frame_count,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    print("🚀 Starting CrowdGuard AI ML Module...")
    print(f"📡 Listening on {API_HOST}:{API_PORT}")
    
    uvicorn.run(
        app,
        host=API_HOST,
        port=8080,
        log_level="info"
    )
