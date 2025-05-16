"""Image preprocessing for door detection."""

from typing import Tuple

import cv2
import numpy as np


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Apply preprocessing to improve door detection.
    
    Args:
        image: OpenCV image
        
    Returns:
        Preprocessed image
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Apply CLAHE for contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    return thresh


def deskew_image(image: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Deskew an image using Hough transform to detect principal axis.
    
    Args:
        image: OpenCV image
        
    Returns:
        Deskewed image and the rotation angle
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Use Hough transform to detect lines
    lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
    
    if lines is None or len(lines) == 0:
        # No rotation needed if no lines detected
        return image, 0.0
    
    # Find the most common angle
    angles = []
    for line in lines:
        rho, theta = line[0]
        # Only consider horizontal and vertical lines
        if (np.abs(theta) < np.pi/6) or (np.abs(theta - np.pi/2) < np.pi/6):
            angles.append(theta)
    
    if not angles:
        # No suitable angles found
        return image, 0.0
    
    # Find the most frequent angle
    angle_bins = np.histogram(angles, bins=180)[0]
    dominant_angle_index = np.argmax(angle_bins)
    dominant_angle = dominant_angle_index * np.pi / 180
    
    # Convert to degrees and adjust
    angle_deg = np.degrees(dominant_angle)
    if angle_deg > 45:
        angle_deg = 90 - angle_deg
    elif angle_deg < -45:
        angle_deg = -90 - angle_deg
    
    # Determine rotation angle
    rotate_angle = angle_deg
    
    # Get image dimensions
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    
    # Create rotation matrix
    M = cv2.getRotationMatrix2D(center, rotate_angle, 1.0)
    
    # Determine new image size
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_width = int((height * sin) + (width * cos))
    new_height = int((height * cos) + (width * sin))
    
    # Update matrix for new dimensions
    M[0, 2] += (new_width / 2) - center[0]
    M[1, 2] += (new_height / 2) - center[1]
    
    # Rotate image
    rotated = cv2.warpAffine(image, M, (new_width, new_height), 
                            flags=cv2.INTER_CUBIC, 
                            borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(255, 255, 255))
    
    return rotated, rotate_angle