"""Module for detecting door symbols in floor plan images."""

import os
from pathlib import Path
from typing import List, Optional, Tuple, Union, Dict, Any

import cv2
import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


class DoorDetector:
    """Base class for door detection."""
    
    def detect(self, image: Union[np.ndarray, Path]) -> List[Dict[str, Any]]:
        """
        Detect doors in an image.
        
        Args:
            image: OpenCV image or path to image file
            
        Returns:
            List of door information dictionaries with keys:
            - bbox: (x1, y1, x2, y2) bounding box
            - confidence: detection confidence
        """
        raise NotImplementedError("Subclasses must implement detect()")


class YOLODoorDetector(DoorDetector):
    """Door detector using YOLOv8."""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize YOLO door detector.
        
        Args:
            model_path: Path to YOLO model weights. If None, will use a pre-trained model
                        or download from Roboflow if not available.
        """
        if not YOLO_AVAILABLE:
            raise ImportError("YOLOv8 is not available. Install with 'pip install ultralytics'")
        
        # Use specified model or default
        if model_path is None:
            # First check if we have a local copy of the model
            model_dir = Path(__file__).parent / "models"
            model_dir.mkdir(exist_ok=True, parents=True)
            default_model = model_dir / "doors_floorplan_yolov8.pt"
            
            if default_model.exists():
                model_path = str(default_model)
            else:
                # If no local model, use a small YOLOv8 model as a placeholder
                # In a real implementation, we would train a model or download a pre-trained one
                model_path = "yolov8n.pt"
                print(f"No specific door detection model found. Using {model_path} as a placeholder.")
                print("For best results, train a custom model on floor plan door data.")
        
        self.model = YOLO(model_path)
    
    def detect(self, image: Union[np.ndarray, Path]) -> List[Dict[str, Any]]:
        """
        Detect doors using YOLO.
        
        Args:
            image: OpenCV image or path to image file
            
        Returns:
            List of door bounding boxes and confidence scores
        """
        # Load image if path is provided
        if isinstance(image, Path):
            if not os.path.exists(image):
                raise FileNotFoundError(f"Could not find image: {image}")
            image_path = str(image)
        else:
            # Save the numpy array temporarily to use with YOLO
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp:
                temp_path = temp.name
                cv2.imwrite(temp_path, image)
                image_path = temp_path
        
        # Run detection
        results = self.model(image_path)
        
        # Extract door detections
        doors = []
        for result in results:
            boxes = result.boxes
            for i, box in enumerate(boxes):
                # Filter for door class if the model has multiple classes
                # For a dedicated door model, this isn't necessary
                # if box.cls[0].item() != door_class_idx:
                #     continue
                
                # Get bounding box and confidence
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = box.conf[0].item()
                
                doors.append({
                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    "confidence": confidence
                })
        
        # Clean up temp file if we created one
        if isinstance(image, np.ndarray) and os.path.exists(temp_path):
            os.unlink(temp_path)
            
        return doors


class TemplateDoorDetector(DoorDetector):
    """
    Door detector using template matching as a fallback.
    This is useful when ML dependencies are not available.
    """
    
    def __init__(self):
        """Initialize template-based door detector."""
        # Load template images if available
        self.templates = []
        template_dir = Path(__file__).parent / "templates"
        
        if template_dir.exists():
            for template_path in template_dir.glob("*.png"):
                template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    self.templates.append(template)
        
        # If no templates available, use a simple door template
        if not self.templates:
            # Create a simple door template (90-degree arc + rectangle)
            template = np.zeros((50, 50), dtype=np.uint8)
            # Draw rectangle for door frame
            cv2.rectangle(template, (0, 20), (5, 30), 255, 1)
            # Draw arc for door swing
            cv2.ellipse(template, (5, 25), (20, 20), 0, 270, 360, 255, 1)
            self.templates = [template]
    
    def detect(self, image: Union[np.ndarray, Path]) -> List[Dict[str, Any]]:
        """
        Detect doors using template matching.
        
        Args:
            image: OpenCV image or path to image file
            
        Returns:
            List of door bounding boxes and match scores
        """
        # Load image if path is provided
        if isinstance(image, Path):
            image = cv2.imread(str(image))
            if image is None:
                raise FileNotFoundError(f"Could not load image: {image}")
        
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        doors = []
        for template in self.templates:
            # Template matching with multiple scales
            for scale in [0.5, 0.75, 1.0, 1.5, 2.0]:
                # Resize template
                resized_template = cv2.resize(template, None, 
                                             fx=scale, fy=scale, 
                                             interpolation=cv2.INTER_AREA)
                
                if resized_template.shape[0] > edges.shape[0] or resized_template.shape[1] > edges.shape[1]:
                    continue
                
                # Apply template matching
                result = cv2.matchTemplate(edges, resized_template, cv2.TM_CCOEFF_NORMED)
                
                # Find matches above threshold
                threshold = 0.6
                loc = np.where(result >= threshold)
                
                # Extract bounding boxes
                template_h, template_w = resized_template.shape
                for pt in zip(*loc[::-1]):
                    x1, y1 = pt
                    x2, y2 = x1 + template_w, y1 + template_h
                    match_val = result[y1, x1]
                    
                    # Add to list with non-maximum suppression
                    new_box = (x1, y1, x2, y2)
                    overlap = False
                    
                    # Check for overlap with existing detections
                    for existing in doors:
                        if self._box_overlap(new_box, existing["bbox"]):
                            overlap = True
                            # Keep the one with higher score
                            if match_val > existing["confidence"]:
                                existing["bbox"] = new_box
                                existing["confidence"] = float(match_val)
                            break
                    
                    if not overlap:
                        doors.append({
                            "bbox": new_box,
                            "confidence": float(match_val)
                        })
        
        return doors
    
    def _box_overlap(self, box1, box2, threshold=0.5):
        """Check if two bounding boxes overlap significantly."""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Calculate intersection area
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return False
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        # Calculate box areas
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        # Calculate IoU
        iou = intersection_area / float(box1_area + box2_area - intersection_area)
        
        return iou > threshold


def get_door_detector() -> DoorDetector:
    """Factory function to get the best available door detector."""
    if YOLO_AVAILABLE:
        try:
            return YOLODoorDetector()
        except Exception as e:
            print(f"Failed to initialize YOLO detector: {e}")
            print("Falling back to template matching.")
    
    return TemplateDoorDetector()