"""Module for detecting scale in floor plan images."""

import re
from pathlib import Path
from typing import Optional, Tuple, Union

import cv2
import numpy as np
import pytesseract


def find_numeric_scale_text(image: Union[np.ndarray, Path]) -> Optional[float]:
    """
    Find a scale factor from text like '1:50' or 'Scale 1/4" = 1'-0"'.
    
    Args:
        image: OpenCV image or path to image file
        
    Returns:
        Scale factor (drawing units per real-world unit) or None if not found
    """
    # Load image if path is provided
    if isinstance(image, Path):
        image = cv2.imread(str(image))
        if image is None:
            raise FileNotFoundError(f"Could not load image: {image}")
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply preprocessing to improve OCR
    _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Extract text using Tesseract
    text = pytesseract.image_to_string(thresh, config='--psm 6')
    
    # Look for common scale patterns
    # Pattern 1: "1:50" format
    match = re.search(r'1\s*[:]\s*(\d+)', text)
    if match:
        return 1 / float(match.group(1))
    
    # Pattern 2: "1/4" = 1'-0"" format
    match = re.search(r'(\d+)/(\d+)["\']\s*=\s*(\d+)[\'"]', text)
    if match:
        numerator = float(match.group(1))
        denominator = float(match.group(2))
        feet = float(match.group(3))
        # Convert to metric for consistency
        inch_scale = numerator / denominator
        feet_in_drawing_units = feet * 12 / inch_scale
        return 1 / feet_in_drawing_units
    
    # Pattern 3: Simple fraction "1/50"
    match = re.search(r'1\s*/\s*(\d+)', text)
    if match:
        return 1 / float(match.group(1))
    
    return None


def find_graphic_scale_bar(image: Union[np.ndarray, Path]) -> Optional[float]:
    """
    Detect a graphic scale bar in the image and calculate mm per pixel.
    
    Args:
        image: OpenCV image or path to image file
        
    Returns:
        Scale in mm per pixel or None if no scale bar found
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
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Line detection
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, 
                           minLineLength=100, maxLineGap=10)
    
    if lines is None:
        return None
    
    # Find horizontal lines (potential scale bars)
    horizontal_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # Check if the line is horizontal (small y difference)
        if abs(y2 - y1) < 5:
            length = abs(x2 - x1)
            # Save longer lines which are more likely to be scale bars
            if length > 50:
                horizontal_lines.append((x1, y1, x2, y2, length))
    
    if not horizontal_lines:
        return None
    
    # Sort by length (longest first)
    horizontal_lines.sort(key=lambda x: x[4], reverse=True)
    
    # For the longest lines, look for text nearby that might indicate scale
    for x1, y1, x2, y2, length in horizontal_lines[:5]:
        # Get a region slightly below the line where scale text might be
        text_region_y = max(0, y1 - 20)
        text_region_height = 40  # Look 40px down from the line
        text_region_width = length + 40  # Add some margin
        text_region_x = max(0, x1 - 20)
        
        text_region = gray[text_region_y:text_region_y+text_region_height, 
                          text_region_x:text_region_x+text_region_width]
        
        if text_region.size == 0:  # Skip if region is out of bounds
            continue
        
        # OCR on the region to find scale labels
        text = pytesseract.image_to_string(text_region, config='--oem 1 --psm 6')
        
        # Look for numeric values with units
        matches = re.findall(r'(\d+(?:\.\d+)?)\s*(m|mm|cm|ft|\')', text)
        if matches and len(matches) >= 2:
            # Take the first and last value for better accuracy
            first_val, first_unit = matches[0]
            last_val, last_unit = matches[-1]
            
            # Convert values to mm
            first_mm = convert_to_mm(float(first_val), first_unit)
            last_mm = convert_to_mm(float(last_val), last_unit)
            
            if first_mm is None or last_mm is None:
                continue
            
            # Estimate pixel distance between first and last tick
            # This is a simplification - in a real implementation we would detect ticks
            px_distance = length
            mm_distance = abs(last_mm - first_mm)
            
            if mm_distance > 0:
                return mm_distance / px_distance
    
    return None


def convert_to_mm(value: float, unit: str) -> Optional[float]:
    """Convert a value from various units to millimeters."""
    if unit == 'mm':
        return value
    elif unit == 'cm':
        return value * 10
    elif unit == 'm':
        return value * 1000
    elif unit == 'ft' or unit == "'":
        return value * 304.8  # 1 foot = 304.8 mm
    elif unit == 'in' or unit == '"':
        return value * 25.4   # 1 inch = 25.4 mm
    return None


def detect_scale(image: Union[np.ndarray, Path]) -> Optional[float]:
    """
    Detect the scale of a floor plan image using multiple methods.
    
    Args:
        image: OpenCV image or path to image file
        
    Returns:
        Scale in mm per pixel or None if scale can't be determined
    """
    # First try text-based scale detection
    text_scale = find_numeric_scale_text(image)
    if text_scale is not None:
        return text_scale
    
    # If that fails, try graphic scale detection
    graphic_scale = find_graphic_scale_bar(image)
    if graphic_scale is not None:
        return graphic_scale
    
    # If both methods fail, return None
    return None