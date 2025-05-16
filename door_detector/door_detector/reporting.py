"""Module for generating reports on door accessibility."""

import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import pandas as pd
import cv2
import numpy as np


def create_csv_report(
    doors: List[Dict[str, Any]], 
    output_path: Path,
    min_width_mm: float = 900.0
) -> Path:
    """
    Create a CSV report of door measurements.
    
    Args:
        doors: List of door information dictionaries
        output_path: Path to save the CSV report
        min_width_mm: Minimum acceptable door width in mm
        
    Returns:
        Path to the created report file
    """
    with open(output_path, 'w', newline='') as csvfile:
        fieldnames = ['page', 'x', 'y', 'width_mm', 'angle_deg', 'is_compliant']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for door in doors:
            writer.writerow({
                'page': door.get('page', ''),
                'x': door['bbox'][0],
                'y': door['bbox'][1],
                'width_mm': door.get('width_mm', 0),
                'angle_deg': door.get('angle_deg', 0),
                'is_compliant': door.get('is_compliant', False)
            })
    
    return output_path


def create_json_report(
    doors: List[Dict[str, Any]], 
    output_path: Path,
    min_width_mm: float = 900.0
) -> Path:
    """
    Create a JSON report of door measurements.
    
    Args:
        doors: List of door information dictionaries
        output_path: Path to save the JSON report
        min_width_mm: Minimum acceptable door width in mm
        
    Returns:
        Path to the created report file
    """
    # Calculate summary statistics
    total_doors = len(doors)
    compliant_doors = sum(1 for door in doors if door.get('is_compliant', False))
    
    report = {
        'summary': {
            'total_doors': total_doors,
            'compliant_doors': compliant_doors,
            'non_compliant_doors': total_doors - compliant_doors,
            'compliance_percentage': 
                round(compliant_doors / total_doors * 100, 1) if total_doors > 0 else 0,
            'min_width_mm': min_width_mm
        },
        'doors': doors
    }
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return output_path


def create_visual_report(
    image: np.ndarray, 
    doors: List[Dict[str, Any]], 
    output_path: Path,
    min_width_mm: float = 900.0
) -> Path:
    """
    Create a visual report with door annotations.
    
    Args:
        image: OpenCV image
        doors: List of door information dictionaries
        output_path: Path to save the annotated image
        min_width_mm: Minimum acceptable door width in mm
        
    Returns:
        Path to the created image file
    """
    # Make a copy to avoid modifying the original
    visual = image.copy()
    
    # Convert to color if grayscale
    if len(visual.shape) == 2:
        visual = cv2.cvtColor(visual, cv2.COLOR_GRAY2BGR)
    
    # Draw bounding boxes and measurements
    for door in doors:
        x1, y1, x2, y2 = door['bbox']
        
        # Determine color based on compliance
        is_compliant = door.get('is_compliant', False)
        color = (0, 255, 0) if is_compliant else (0, 0, 255)  # Green for compliant, red for non-compliant
        
        # Draw rectangle
        cv2.rectangle(visual, (x1, y1), (x2, y2), color, 2)
        
        # Add text with width measurement
        width_mm = door.get('width_mm', 0)
        text = f"{width_mm:.0f}mm"
        
        # Determine text position
        text_x = x1
        text_y = y1 - 10 if y1 > 20 else y1 + 30
        
        # Add text background for better visibility
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(visual, (text_x, text_y - text_h), (text_x + text_w, text_y + 5), (255, 255, 255), -1)
        
        # Add text
        cv2.putText(visual, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Add legend
    cv2.putText(visual, f"Min width: {min_width_mm}mm", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(visual, "Compliant", (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(visual, "Non-compliant", (10, 90), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Save image
    cv2.imwrite(str(output_path), visual)
    
    return output_path


def create_summary_dataframe(
    doors: List[Dict[str, Any]], 
    min_width_mm: float = 900.0
) -> pd.DataFrame:
    """
    Create a pandas DataFrame from door measurements.
    
    Args:
        doors: List of door information dictionaries
        min_width_mm: Minimum acceptable door width in mm
        
    Returns:
        Pandas DataFrame with door measurements
    """
    # Extract relevant fields
    records = []
    for door in doors:
        record = {
            'page': door.get('page', ''),
            'x': door['bbox'][0],
            'y': door['bbox'][1],
            'width_px': abs(door['bbox'][2] - door['bbox'][0]),
            'height_px': abs(door['bbox'][3] - door['bbox'][1]),
            'width_mm': door.get('width_mm', 0),
            'angle_deg': door.get('angle_deg', 0),
            'is_compliant': door.get('is_compliant', False),
            'confidence': door.get('confidence', 1.0)
        }
        records.append(record)
    
    # Create DataFrame
    df = pd.DataFrame(records)
    
    # Add compliance status
    df['compliance_status'] = df['is_compliant'].apply(
        lambda x: 'Compliant' if x else 'Non-compliant'
    )
    
    # Sort by page and position
    if 'page' in df.columns and not df['page'].isna().all():
        df = df.sort_values(['page', 'y', 'x'])
    
    return df