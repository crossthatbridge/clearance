"""Module for measuring door dimensions in floor plan images."""

from typing import Dict, Any, Tuple, Optional, Union

import cv2
import numpy as np


def door_width_mm(
    door: Dict[str, Any], 
    mm_per_px: float, 
    min_width_mm: float = 900.0
) -> Dict[str, Any]:
    """
    Calculate the width of a door in millimeters.
    
    Args:
        door: Dictionary containing door information with 'bbox' key
        mm_per_px: Scale factor in mm per pixel
        min_width_mm: Minimum acceptable door width in mm
        
    Returns:
        Dictionary with original door info plus:
        - width_mm: Estimated door width in mm
        - is_compliant: Boolean indicating if door meets minimum width
    """
    x1, y1, x2, y2 = door["bbox"]
    
    # Calculate width and height in pixels
    width_px = abs(x2 - x1)
    height_px = abs(y2 - y1)
    
    # Door leaf is normally the narrow dimension
    leaf_width_px = min(width_px, height_px)
    
    # Convert to millimeters
    width_mm = leaf_width_px * mm_per_px
    
    # Update door info
    result = door.copy()
    result.update({
        "width_mm": round(width_mm, 1),
        "is_compliant": width_mm >= min_width_mm
    })
    
    return result


def refine_door_measurement(
    image: np.ndarray, 
    door: Dict[str, Any], 
    mm_per_px: float,
    min_width_mm: float = 900.0
) -> Dict[str, Any]:
    """
    Refine door measurement using advanced techniques.
    
    Args:
        image: OpenCV image
        door: Dictionary containing door information with 'bbox' key
        mm_per_px: Scale factor in mm per pixel
        min_width_mm: Minimum acceptable door width in mm
        
    Returns:
        Dictionary with refined measurements
    """
    x1, y1, x2, y2 = door["bbox"]
    
    # Extract the door region
    door_region = image[y1:y2, x1:x2]
    if door_region.size == 0:
        # If extraction fails, fall back to basic measurement
        return door_width_mm(door, mm_per_px, min_width_mm)
    
    # Convert to grayscale if needed
    if len(door_region.shape) == 3:
        door_region = cv2.cvtColor(door_region, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        door_region, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Apply skeletonization to find the door centerline
    # This could be replaced with proper skeletonization algorithm
    kernel = np.ones((3, 3), np.uint8)
    eroded = cv2.erode(thresh, kernel, iterations=1)
    
    # Find orientation using moments
    moments = cv2.moments(eroded)
    if moments["mu20"] + moments["mu02"] == 0:
        # Fall back if moments calculation fails
        return door_width_mm(door, mm_per_px, min_width_mm)
    
    # Calculate orientation angle
    angle = 0.5 * np.arctan2(2 * moments["mu11"], moments["mu20"] - moments["mu02"])
    angle_deg = np.degrees(angle) % 180
    
    # Calculate minimum width perpendicular to door orientation
    if abs(angle_deg - 90) < 45:  # Door is more vertical
        width_px = door_region.shape[1]  # width of bounding box
    else:  # Door is more horizontal
        width_px = door_region.shape[0]  # height of bounding box
    
    # Consider door angle for more accurate width measurement
    # For angled doors, the width is the perpendicular thickness
    if 15 < angle_deg < 75 or 105 < angle_deg < 165:
        # For non-horizontal/vertical doors, find minimum thickness
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # Use the largest contour
            contour = max(contours, key=cv2.contourArea)
            rect = cv2.minAreaRect(contour)
            width_px = min(rect[1])  # use the smaller dimension of the rotated rect
    
    # Convert to millimeters
    width_mm = width_px * mm_per_px
    
    # Update door info
    result = door.copy()
    result.update({
        "width_mm": round(width_mm, 1),
        "is_compliant": width_mm >= min_width_mm,
        "angle_deg": round(angle_deg, 1)
    })
    
    return result