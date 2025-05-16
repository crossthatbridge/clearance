"""Command-line interface for door detection."""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import cv2
import numpy as np

from door_detector.pdf_utils import pdf_to_images
from door_detector.scale_detection import detect_scale
from door_detector.door_detection import get_door_detector
from door_detector.measurement import door_width_mm, refine_door_measurement
from door_detector.preprocessing import preprocess_image, deskew_image
from door_detector.reporting import (
    create_csv_report, 
    create_json_report, 
    create_visual_report,
    create_summary_dataframe
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("door_detector")


class DoorDetectorPipeline:
    """Full pipeline for detecting and measuring doors in floor plans."""
    
    def __init__(
        self, 
        min_width_mm: float = 900.0,
        output_dir: Optional[Path] = None,
        dpi: int = 400,
        debug: bool = False
    ):
        """
        Initialize the door detection pipeline.
        
        Args:
            min_width_mm: Minimum acceptable door width in mm
            output_dir: Directory to save output files
            dpi: Resolution for PDF conversion
            debug: Enable debug mode (more verbose logging and outputs)
        """
        self.min_width_mm = min_width_mm
        self.dpi = dpi
        self.debug = debug
        
        # Set output directory
        if output_dir is None:
            self.output_dir = Path.cwd() / "door_detector_output"
        else:
            self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get detector instance
        self.detector = get_door_detector()
        
        # Set log level
        if debug:
            logger.setLevel(logging.DEBUG)
    
    def process_pdf(self, pdf_path: Path) -> Tuple[List[Dict[str, Any]], Path]:
        """
        Process a PDF and detect doors.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of door information dictionaries and path to the output directory
        """
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Create output directory for this PDF
        pdf_output_dir = self.output_dir / pdf_path.stem
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert PDF to images
        logger.info("Converting PDF to images...")
        image_paths = pdf_to_images(pdf_path, output_dir=pdf_output_dir, dpi=self.dpi)
        logger.info(f"Converted {len(image_paths)} pages")
        
        # Process each page
        all_doors = []
        
        for i, image_path in enumerate(image_paths):
            logger.info(f"Processing page {i+1}/{len(image_paths)}")
            
            try:
                # Load image
                image = cv2.imread(str(image_path))
                if image is None:
                    raise FileNotFoundError(f"Could not load image: {image_path}")
                
                # Deskew image if needed
                deskewed, angle = deskew_image(image)
                if abs(angle) > 1.0:
                    logger.info(f"Deskewed image by {angle:.1f} degrees")
                    if self.debug:
                        deskew_path = pdf_output_dir / f"{image_path.stem}_deskewed.png"
                        cv2.imwrite(str(deskew_path), deskewed)
                
                # Detect scale
                logger.info("Detecting scale...")
                scale = detect_scale(deskewed)
                
                if scale is None:
                    logger.warning(
                        f"Could not detect scale for page {i+1}. Skipping."
                    )
                    continue
                
                logger.info(f"Detected scale: {scale:.5f} mm/px")
                
                # Apply preprocessing
                preprocessed = preprocess_image(deskewed)
                if self.debug:
                    preproc_path = pdf_output_dir / f"{image_path.stem}_preprocessed.png"
                    cv2.imwrite(str(preproc_path), preprocessed)
                
                # Detect doors
                logger.info("Detecting doors...")
                doors = self.detector.detect(deskewed)
                logger.info(f"Detected {len(doors)} doors")
                
                # Measure doors
                logger.info("Measuring doors...")
                measured_doors = []
                for door in doors:
                    # Try refined measurement first
                    measured = refine_door_measurement(
                        deskewed, door, scale, self.min_width_mm
                    )
                    measured["page"] = image_path.name
                    measured["page_number"] = i + 1
                    measured_doors.append(measured)
                
                # Create visual report for this page
                visual_path = pdf_output_dir / f"{image_path.stem}_annotated.png"
                create_visual_report(
                    deskewed, measured_doors, visual_path, self.min_width_mm
                )
                
                # Add to all doors
                all_doors.extend(measured_doors)
            
            except Exception as e:
                logger.error(f"Error processing page {i+1}: {e}")
                if self.debug:
                    import traceback
                    logger.debug(traceback.format_exc())
        
        # Create summary reports
        if all_doors:
            try:
                # CSV report
                csv_path = pdf_output_dir / f"{pdf_path.stem}_doors.csv"
                create_csv_report(all_doors, csv_path, self.min_width_mm)
                logger.info(f"Created CSV report: {csv_path}")
                
                # JSON report
                json_path = pdf_output_dir / f"{pdf_path.stem}_doors.json"
                create_json_report(all_doors, json_path, self.min_width_mm)
                logger.info(f"Created JSON report: {json_path}")
                
                # Summary stats
                df = create_summary_dataframe(all_doors, self.min_width_mm)
                logger.info(f"Door summary:")
                logger.info(f"  Total doors: {len(all_doors)}")
                
                compliant = df['is_compliant'].sum()
                logger.info(f"  Compliant doors: {compliant} ({compliant/len(all_doors)*100:.1f}%)")
                logger.info(f"  Non-compliant doors: {len(all_doors) - compliant}")
                
                if len(all_doors) - compliant > 0:
                    logger.warning(
                        f"Found {len(all_doors) - compliant} non-compliant doors "
                        f"below {self.min_width_mm}mm width"
                    )
            
            except Exception as e:
                logger.error(f"Error creating reports: {e}")
                if self.debug:
                    import traceback
                    logger.debug(traceback.format_exc())
        
        return all_doors, pdf_output_dir


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Detect and measure doors in floor plan PDFs."
    )
    parser.add_argument(
        "pdf_path", 
        type=str, 
        help="Path to the PDF file or directory containing PDFs"
    )
    parser.add_argument(
        "--min-width", 
        type=float, 
        default=900.0, 
        help="Minimum acceptable door width in mm (default: 900mm)"
    )
    parser.add_argument(
        "--output-dir", 
        type=str, 
        help="Directory to save output files"
    )
    parser.add_argument(
        "--dpi", 
        type=int, 
        default=400, 
        help="Resolution for PDF conversion (default: 400)"
    )
    parser.add_argument(
        "--recursive", 
        action="store_true", 
        help="Process PDFs in subdirectories"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode"
    )
    
    args = parser.parse_args()
    
    # Set output directory
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    # Initialize pipeline
    pipeline = DoorDetectorPipeline(
        min_width_mm=args.min_width,
        output_dir=output_dir,
        dpi=args.dpi,
        debug=args.debug
    )
    
    # Process PDF(s)
    pdf_path = Path(args.pdf_path)
    
    if pdf_path.is_file():
        # Process single PDF
        if pdf_path.suffix.lower() != ".pdf":
            logger.error(f"Not a PDF file: {pdf_path}")
            sys.exit(1)
        
        pipeline.process_pdf(pdf_path)
    
    elif pdf_path.is_dir():
        # Process directory of PDFs
        pattern = "**/*.pdf" if args.recursive else "*.pdf"
        pdf_files = list(pdf_path.glob(pattern))
        
        if not pdf_files:
            logger.error(f"No PDF files found in {pdf_path}")
            sys.exit(1)
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        for i, pdf_file in enumerate(pdf_files):
            logger.info(f"Processing {i+1}/{len(pdf_files)}: {pdf_file}")
            try:
                pipeline.process_pdf(pdf_file)
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                if args.debug:
                    import traceback
                    logger.debug(traceback.format_exc())
    
    else:
        logger.error(f"Path not found: {pdf_path}")
        sys.exit(1)
    
    logger.info("Processing complete")


if __name__ == "__main__":
    main()