"""Video processing service for real-time and batch analysis."""
import cv2
import numpy as np
from typing import Optional, Generator, Dict
from pathlib import Path
import time
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import FRAME_SAMPLE_RATE
from detection.detector import CrowdDetector
from analytics.crowd_analyzer import CrowdAnalyzer


class VideoProcessor:
    """Process video streams and files for crowd analysis."""
    
    def __init__(self):
        """Initialize video processor."""
        self.detector = CrowdDetector()
        self.analyzer = None
        self.frame_count = 0
        
    def process_video_file(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        show_preview: bool = False
    ) -> Generator[Dict, None, None]:
        """
        Process a video file frame by frame.
        
        Args:
            video_path: Path to video file
            output_path: Optional path to save annotated video
            show_preview: Whether to display video during processing
            
        Yields:
            Dict with frame analysis results
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
            
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"📹 Video: {width}x{height} @ {fps}fps, {total_frames} frames")
        
        # Initialize analyzer with frame dimensions
        self.analyzer = CrowdAnalyzer((height, width))
        
        # Setup video writer if output path provided
        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
        frame_idx = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Sample frames
            if frame_idx % FRAME_SAMPLE_RATE != 0:
                frame_idx += 1
                continue
                
            # Detect people
            detections = self.detector.detect_people(frame)
            
            # Analyze crowd
            timestamp = datetime.now().isoformat()
            time_delta = 1.0 / fps * FRAME_SAMPLE_RATE
            metrics = self.analyzer.analyze(detections, timestamp, time_delta)
            
            # Create visualization
            annotated = self.detector.draw_detections(frame, detections)
            
            # Add heatmap
            if len(detections) > 0:
                centers = np.array([det["center"] for det in detections])
                heatmap = self.analyzer.create_density_heatmap(centers)
                annotated = self.analyzer.apply_heatmap_overlay(annotated, heatmap, 0.3)
                
            # Draw high-density zones
            for zone in metrics.high_density_zones:
                x1, y1, x2, y2 = zone["bbox"]
                color = (0, 0, 255) if zone["density_level"] == "critical" else (0, 165, 255)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
                cv2.putText(
                    annotated,
                    f"HIGH DENSITY: {zone['person_count']}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2
                )
                
            # Add metrics overlay
            self._draw_metrics_overlay(annotated, metrics)
            
            # Save frame
            if writer:
                writer.write(annotated)
                
            # Show preview
            if show_preview:
                cv2.imshow('CrowdGuard AI', annotated)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            # Yield results
            yield {
                "frame_idx": frame_idx,
                "timestamp": timestamp,
                "detections": detections,
                "metrics": metrics,
                "annotated_frame": annotated
            }
            
            frame_idx += 1
            
        # Cleanup
        cap.release()
        if writer:
            writer.release()
        if show_preview:
            cv2.destroyAllWindows()
            
        elapsed = time.time() - start_time
        processed_frames = frame_idx // FRAME_SAMPLE_RATE
        print(f"✅ Processed {processed_frames} frames in {elapsed:.2f}s ({processed_frames/elapsed:.1f} fps)")
        
    def process_rtsp_stream(
        self,
        rtsp_url: str,
        callback=None
    ) -> None:
        """
        Process RTSP camera stream.
        
        Args:
            rtsp_url: RTSP stream URL
            callback: Optional callback function for each frame result
        """
        cap = cv2.VideoCapture(rtsp_url)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot connect to RTSP stream: {rtsp_url}")
            
        # Get stream properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"📡 Connected to RTSP stream: {width}x{height}")
        
        # Initialize analyzer
        self.analyzer = CrowdAnalyzer((height, width))
        
        frame_idx = 0
        last_process_time = time.time()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("⚠️ Lost connection to stream, reconnecting...")
                    time.sleep(5)
                    cap = cv2.VideoCapture(rtsp_url)
                    continue
                    
                # Sample frames
                if frame_idx % FRAME_SAMPLE_RATE != 0:
                    frame_idx += 1
                    continue
                    
                # Process frame
                current_time = time.time()
                time_delta = current_time - last_process_time
                
                detections = self.detector.detect_people(frame)
                timestamp = datetime.now().isoformat()
                metrics = self.analyzer.analyze(detections, timestamp, time_delta)
                
                # Callback
                if callback:
                    callback({
                        "timestamp": timestamp,
                        "detections": detections,
                        "metrics": metrics,
                        "frame": frame
                    })
                    
                last_process_time = current_time
                frame_idx += 1
                
        except KeyboardInterrupt:
            print("\n⛔ Stream processing stopped")
        finally:
            cap.release()
            
    def _draw_metrics_overlay(self, frame: np.ndarray, metrics) -> None:
        """Draw metrics overlay on frame."""
        # Background panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 50), (400, 250), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Metrics text
        y_offset = 80
        line_height = 30
        
        metrics_text = [
            f"People Count: {metrics.total_count}",
            f"Density Score: {metrics.density_score:.1f}/100",
            f"Risk Level: {metrics.risk_level.value}",
            f"Risk Score: {metrics.risk_score:.1f}/100",
            f"Anomaly: {metrics.anomaly_type.value}",
            f"Velocity: {metrics.avg_velocity:.1f} px/s"
        ]
        
        # Color based on risk
        if metrics.risk_level.value == "CRITICAL":
            color = (0, 0, 255)
        elif metrics.risk_level.value == "HIGH":
            color = (0, 165, 255)
        elif metrics.risk_level.value == "MEDIUM":
            color = (0, 255, 255)
        else:
            color = (0, 255, 0)
            
        for text in metrics_text:
            cv2.putText(
                frame,
                text,
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )
            y_offset += line_height


def main():
    """Test video processing."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python video_processor.py <video_file>")
        print("Example: python video_processor.py crowd_video.mp4")
        return
        
    video_path = sys.argv[1]
    output_path = "output_" + Path(video_path).name
    
    print(f"🎬 Processing video: {video_path}")
    
    processor = VideoProcessor()
    
    # Process video with preview
    for result in processor.process_video_file(
        video_path,
        output_path=output_path,
        show_preview=True
    ):
        metrics = result["metrics"]
        if metrics.risk_level.value in ["HIGH", "CRITICAL"]:
            print(f"⚠️ ALERT at frame {result['frame_idx']}: {metrics.risk_level.value} risk detected!")
            print(f"   Details: {metrics.anomaly_type.value}, {metrics.total_count} people")


if __name__ == "__main__":
    main()
