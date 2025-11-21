"""YOLO-based object detection for crowd monitoring."""
import cv2
import numpy as np
from typing import List, Dict, Tuple
from ultralytics import YOLO
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import YOLO_MODEL_PATH, CONFIDENCE_THRESHOLD, IOU_THRESHOLD


class CrowdDetector:
    """Real-time crowd detection using YOLOv8."""
    
    def __init__(self, model_path: str = None):
        """Initialize the detector with YOLO model."""
        self.model_path = model_path or YOLO_MODEL_PATH
        self.model = None
        self.load_model()
        
    def load_model(self):
        """Load YOLOv8 model."""
        try:
            self.model = YOLO(str(self.model_path))
            print(f"✅ Loaded YOLO model from {self.model_path}")
        except Exception as e:
            print(f"❌ Error loading YOLO model: {e}")
            # Try downloading the model
            print("📥 Downloading YOLOv8-Nano model...")
            self.model = YOLO('yolov8n.pt')
            self.model.export(format='pt')
            
    def detect_people(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect people in a frame with crowd-optimized settings.
        
        Args:
            frame: Input image as numpy array (BGR format)
            
        Returns:
            List of detections with bounding boxes and metadata
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        # Get frame dimensions
        height, width = frame.shape[:2]
        
        # Use larger image size for better small person detection
        imgsz = 1280 if max(height, width) > 640 else 640
            
        # Run inference with crowd-optimized parameters
        results = self.model(
            frame,
            conf=CONFIDENCE_THRESHOLD,
            iou=IOU_THRESHOLD,
            classes=[0],  # 0 = person in COCO dataset
            verbose=False,
            imgsz=imgsz,  # Larger image size for better detection
            agnostic_nms=True,  # Better for overlapping objects
            max_det=500  # Allow more detections for crowds
        )
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                
                detection = {
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": confidence,
                    "class": "person",
                    "center": [int((x1 + x2) / 2), int((y1 + y2) / 2)],
                    "area": int((x2 - x1) * (y2 - y1))
                }
                detections.append(detection)
                
        return detections
    
    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Dict],
        show_confidence: bool = True
    ) -> np.ndarray:
        """
        Draw bounding boxes on frame.
        
        Args:
            frame: Input image
            detections: List of detections from detect_people()
            show_confidence: Whether to show confidence scores
            
        Returns:
            Annotated frame
        """
        annotated_frame = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            confidence = det["confidence"]
            
            # Draw bounding box
            color = (0, 255, 0)  # Green
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            if show_confidence:
                label = f"Person {confidence:.2f}"
                cv2.putText(
                    annotated_frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2
                )
                
        # Draw count
        count_text = f"People: {len(detections)}"
        cv2.putText(
            annotated_frame,
            count_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )
        
        return annotated_frame
    
    def get_detection_centers(self, detections: List[Dict]) -> np.ndarray:
        """
        Extract center coordinates of all detections.
        
        Args:
            detections: List of detections
            
        Returns:
            Numpy array of shape (N, 2) with center coordinates
        """
        if not detections:
            return np.array([])
        return np.array([det["center"] for det in detections])


def test_detector():
    """Test the detector with a sample image."""
    import urllib.request
    
    # Create a test image with multiple people
    print("🧪 Testing CrowdDetector...")
    
    # Download a test image
    test_url = "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800"
    test_image_path = "test_crowd.jpg"
    
    try:
        urllib.request.urlretrieve(test_url, test_image_path)
        print("✅ Downloaded test image")
    except Exception as e:
        print(f"❌ Failed to download test image: {e}")
        return
    
    # Load image
    frame = cv2.imread(test_image_path)
    if frame is None:
        print("❌ Failed to load test image")
        return
        
    # Initialize detector
    detector = CrowdDetector()
    
    # Detect people
    detections = detector.detect_people(frame)
    print(f"✅ Detected {len(detections)} people")
    
    # Draw detections
    annotated = detector.draw_detections(frame, detections)
    
    # Save result
    output_path = "test_output.jpg"
    cv2.imwrite(output_path, annotated)
    print(f"✅ Saved annotated image to {output_path}")
    
    # Print detection details
    for i, det in enumerate(detections[:5]):  # Show first 5
        print(f"Person {i+1}: confidence={det['confidence']:.2f}, center={det['center']}")


if __name__ == "__main__":
    test_detector()
