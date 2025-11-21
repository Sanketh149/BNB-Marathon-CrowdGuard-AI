"""Advanced crowd analytics: density, heatmaps, anomalies."""
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import DBSCAN
from dataclasses import dataclass, asdict
from enum import Enum
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import (
    DENSITY_GRID_SIZE,
    HIGH_DENSITY_THRESHOLD,
    ANOMALY_MOVEMENT_THRESHOLD,
    CLUSTERING_EPS,
    MIN_CLUSTER_SIZE
)


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyType(str, Enum):
    """Types of crowd anomalies."""
    SUDDEN_MOVEMENT = "sudden_movement"
    HIGH_DENSITY = "high_density"
    CLUSTERING = "clustering"
    RUSH_BEHAVIOR = "rush_behavior"
    NORMAL = "normal"


@dataclass
class CrowdMetrics:
    """Crowd analysis metrics."""
    total_count: int
    density_score: float  # 0-100
    risk_level: RiskLevel
    risk_score: float  # 0-100
    anomaly_type: AnomalyType
    high_density_zones: List[Dict]
    clusters: List[Dict]
    avg_velocity: float
    frame_area: int
    timestamp: str


class CrowdAnalyzer:
    """Analyzes crowd behavior and generates insights."""
    
    def __init__(self, frame_shape: Tuple[int, int]):
        """
        Initialize analyzer.
        
        Args:
            frame_shape: (height, width) of video frames
        """
        self.frame_height, self.frame_width = frame_shape
        self.frame_area = self.frame_height * self.frame_width
        self.grid_size = DENSITY_GRID_SIZE
        
        # History for tracking changes
        self.previous_positions = None
        self.previous_timestamp = None
        
    def calculate_density_score(self, person_count: int) -> float:
        """
        Calculate crowd density score (0-100).
        
        Formula: (people / area) * normalization_factor
        """
        if self.frame_area == 0:
            return 0.0
            
        # Assume 1 person per 2m² is normal, 1 person per 0.5m² is critical
        # Frame area in pixels, normalized to square meters (rough estimate)
        pixels_per_sqm = 10000  # Approximate
        frame_area_sqm = self.frame_area / pixels_per_sqm
        
        density = person_count / max(frame_area_sqm, 1)
        
        # Normalize to 0-100 scale
        # 0.5 people/m² = 50, 2 people/m² = 100 (critical)
        density_score = min(density / 2 * 100, 100)
        
        return round(density_score, 2)
    
    def create_density_heatmap(
        self,
        centers: np.ndarray,
        sigma: int = 30
    ) -> np.ndarray:
        """
        Create a density heatmap using Gaussian kernels.
        
        Args:
            centers: Array of (x, y) coordinates
            sigma: Standard deviation for Gaussian blur
            
        Returns:
            Heatmap as numpy array
        """
        heatmap = np.zeros((self.frame_height, self.frame_width), dtype=np.float32)
        
        if len(centers) == 0:
            return heatmap
            
        for x, y in centers:
            if 0 <= x < self.frame_width and 0 <= y < self.frame_height:
                heatmap[int(y), int(x)] += 1
                
        # Apply Gaussian blur for smooth heatmap
        heatmap = cv2.GaussianBlur(heatmap, (0, 0), sigma)
        
        # Normalize to 0-255
        if heatmap.max() > 0:
            heatmap = (heatmap / heatmap.max() * 255).astype(np.uint8)
            
        return heatmap
    
    def apply_heatmap_overlay(
        self,
        frame: np.ndarray,
        heatmap: np.ndarray,
        alpha: float = 0.5
    ) -> np.ndarray:
        """
        Overlay heatmap on original frame.
        
        Args:
            frame: Original BGR frame
            heatmap: Grayscale heatmap
            alpha: Transparency (0-1)
            
        Returns:
            Frame with heatmap overlay
        """
        # Apply colormap (red = high density)
        heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        
        # Blend with original frame
        overlay = cv2.addWeighted(frame, 1 - alpha, heatmap_colored, alpha, 0)
        
        return overlay
    
    def detect_high_density_zones(
        self,
        centers: np.ndarray
    ) -> List[Dict]:
        """
        Identify zones with dangerously high density.
        
        Args:
            centers: Array of person centers
            
        Returns:
            List of high-density zones with locations and counts
        """
        if len(centers) == 0:
            return []
            
        # Create grid
        grid_h = self.frame_height // self.grid_size
        grid_w = self.frame_width // self.grid_size
        
        # Count people per grid cell
        grid_counts = np.zeros((grid_h, grid_w), dtype=np.int32)
        
        for x, y in centers:
            grid_x = min(int(x / self.grid_size), grid_w - 1)
            grid_y = min(int(y / self.grid_size), grid_h - 1)
            grid_counts[grid_y, grid_x] += 1
            
        # Find high-density zones
        high_density_zones = []
        for i in range(grid_h):
            for j in range(grid_w):
                count = grid_counts[i, j]
                if count >= HIGH_DENSITY_THRESHOLD:
                    zone = {
                        "grid_position": [j, i],
                        "bbox": [
                            j * self.grid_size,
                            i * self.grid_size,
                            (j + 1) * self.grid_size,
                            (i + 1) * self.grid_size
                        ],
                        "person_count": int(count),
                        "density_level": "critical" if count > HIGH_DENSITY_THRESHOLD * 2 else "high"
                    }
                    high_density_zones.append(zone)
                    
        return high_density_zones
    
    def detect_clusters(self, centers: np.ndarray) -> List[Dict]:
        """
        Detect crowd clusters using DBSCAN.
        
        Args:
            centers: Array of person centers
            
        Returns:
            List of clusters with metadata
        """
        if len(centers) < MIN_CLUSTER_SIZE:
            return []
            
        # Run DBSCAN clustering
        clustering = DBSCAN(eps=CLUSTERING_EPS, min_samples=MIN_CLUSTER_SIZE)
        labels = clustering.fit_predict(centers)
        
        # Analyze clusters
        clusters = []
        unique_labels = set(labels)
        
        for label in unique_labels:
            if label == -1:  # Noise points
                continue
                
            cluster_points = centers[labels == label]
            cluster_center = cluster_points.mean(axis=0)
            
            # Calculate bounding box
            x_min, y_min = cluster_points.min(axis=0)
            x_max, y_max = cluster_points.max(axis=0)
            
            cluster = {
                "cluster_id": int(label),
                "size": len(cluster_points),
                "center": cluster_center.tolist(),
                "bbox": [int(x_min), int(y_min), int(x_max), int(y_max)],
                "area": int((x_max - x_min) * (y_max - y_min))
            }
            clusters.append(cluster)
            
        # Sort by size (largest first)
        clusters.sort(key=lambda x: x["size"], reverse=True)
        
        return clusters
    
    def calculate_movement(
        self,
        current_positions: np.ndarray,
        time_delta: float
    ) -> float:
        """
        Calculate average movement velocity.
        
        Args:
            current_positions: Current person positions
            time_delta: Time since last frame (seconds)
            
        Returns:
            Average velocity in pixels/second
        """
        if self.previous_positions is None or len(current_positions) == 0:
            self.previous_positions = current_positions
            return 0.0
            
        # Match closest points (simple nearest neighbor)
        if len(self.previous_positions) == 0:
            self.previous_positions = current_positions
            return 0.0
            
        velocities = []
        for curr_pos in current_positions:
            # Find closest previous position
            distances = np.linalg.norm(self.previous_positions - curr_pos, axis=1)
            min_dist = distances.min()
            
            if min_dist < 200:  # Only consider if within reasonable range
                velocity = min_dist / max(time_delta, 0.001)
                velocities.append(velocity)
                
        self.previous_positions = current_positions
        
        if velocities:
            return float(np.mean(velocities))
        return 0.0
    
    def classify_risk(
        self,
        person_count: int,
        density_score: float,
        high_density_zones: List[Dict],
        avg_velocity: float
    ) -> Tuple[RiskLevel, float, AnomalyType]:
        """
        Classify overall risk level and type.
        
        Args:
            person_count: Total people count
            density_score: Density score (0-100)
            high_density_zones: List of high-density zones
            avg_velocity: Average movement velocity
            
        Returns:
            (risk_level, risk_score, anomaly_type)
        """
        # Calculate risk score
        risk_score = 0.0
        
        # Factor 1: Density (40% weight)
        risk_score += density_score * 0.4
        
        # Factor 2: High-density zones (30% weight)
        zone_factor = min(len(high_density_zones) * 10, 30)
        risk_score += zone_factor
        
        # Factor 3: Movement velocity (20% weight)
        velocity_factor = min(avg_velocity / ANOMALY_MOVEMENT_THRESHOLD * 20, 20)
        risk_score += velocity_factor
        
        # Factor 4: Absolute count (10% weight)
        count_factor = min(person_count / 100 * 10, 10)
        risk_score += count_factor
        
        risk_score = min(risk_score, 100)
        
        # Classify risk level
        if risk_score < 25:
            risk_level = RiskLevel.LOW
        elif risk_score < 50:
            risk_level = RiskLevel.MEDIUM
        elif risk_score < 75:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL
            
        # Detect anomaly type
        anomaly_type = AnomalyType.NORMAL
        
        if avg_velocity > ANOMALY_MOVEMENT_THRESHOLD:
            anomaly_type = AnomalyType.SUDDEN_MOVEMENT
        elif len(high_density_zones) > 3:
            anomaly_type = AnomalyType.HIGH_DENSITY
        elif density_score > 70:
            anomaly_type = AnomalyType.CLUSTERING
            
        if risk_level == RiskLevel.CRITICAL:
            anomaly_type = AnomalyType.RUSH_BEHAVIOR
            
        return risk_level, round(risk_score, 2), anomaly_type
    
    def analyze(
        self,
        detections: List[Dict],
        timestamp: str,
        time_delta: float = 0.33
    ) -> CrowdMetrics:
        """
        Perform comprehensive crowd analysis.
        
        Args:
            detections: List of person detections
            timestamp: Current timestamp
            time_delta: Time since last frame (seconds)
            
        Returns:
            CrowdMetrics object with all analysis results
        """
        person_count = len(detections)
        
        # Extract centers
        if person_count > 0:
            centers = np.array([det["center"] for det in detections])
        else:
            centers = np.array([])
            
        # Calculate metrics
        density_score = self.calculate_density_score(person_count)
        high_density_zones = self.detect_high_density_zones(centers)
        clusters = self.detect_clusters(centers)
        avg_velocity = self.calculate_movement(centers, time_delta)
        
        # Classify risk
        risk_level, risk_score, anomaly_type = self.classify_risk(
            person_count,
            density_score,
            high_density_zones,
            avg_velocity
        )
        
        return CrowdMetrics(
            total_count=person_count,
            density_score=density_score,
            risk_level=risk_level,
            risk_score=risk_score,
            anomaly_type=anomaly_type,
            high_density_zones=high_density_zones,
            clusters=clusters,
            avg_velocity=round(avg_velocity, 2),
            frame_area=self.frame_area,
            timestamp=timestamp
        )


def test_analyzer():
    """Test the crowd analyzer."""
    print("🧪 Testing CrowdAnalyzer...")
    
    # Simulate detections
    frame_shape = (720, 1280)
    analyzer = CrowdAnalyzer(frame_shape)
    
    # Create fake detections
    fake_detections = [
        {"center": [100, 100], "bbox": [90, 90, 110, 110]},
        {"center": [120, 105], "bbox": [110, 95, 130, 115]},
        {"center": [105, 120], "bbox": [95, 110, 115, 130]},
        {"center": [600, 400], "bbox": [590, 390, 610, 410]},
        {"center": [605, 405], "bbox": [595, 395, 615, 415]},
    ]
    
    metrics = analyzer.analyze(fake_detections, "2025-11-20T10:00:00")
    
    print(f"✅ Analysis complete:")
    print(f"  - People: {metrics.total_count}")
    print(f"  - Density Score: {metrics.density_score}")
    print(f"  - Risk Level: {metrics.risk_level}")
    print(f"  - Risk Score: {metrics.risk_score}")
    print(f"  - Anomaly: {metrics.anomaly_type}")
    print(f"  - Clusters: {len(metrics.clusters)}")
    print(f"  - High Density Zones: {len(metrics.high_density_zones)}")


if __name__ == "__main__":
    test_analyzer()
