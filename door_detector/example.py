#!/usr/bin/env python3
"""Example script demonstrating the door detector package."""

import argparse
import logging
import sys
from pathlib import Path

from door_detector.cli import DoorDetectorPipeline


def main():
    """Process a sample floor plan PDF."""
    parser = argparse.ArgumentParser(
        description="Example for detecting doors in a floor plan PDF."
    )
    parser.add_argument(
        "--pdf", 
        type=str, 
        default=None,
        help="Path to the PDF file to analyze"
    )
    parser.add_argument(
        "--min-width", 
        type=float, 
        default=900.0, 
        help="Minimum acceptable door width in mm (default: 900mm)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if not args.debug else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger("door_detector_example")
    
    # Find a sample PDF if none specified
    if args.pdf is None:
        # Look for PDFs in assets/floorplans
        sample_dirs = [
            Path("assets/floorplans"),
            Path("../assets/floorplans")
        ]
        
        for sample_dir in sample_dirs:
            if sample_dir.exists():
                pdf_files = list(sample_dir.glob("*.pdf"))
                if pdf_files:
                    args.pdf = str(pdf_files[0])
                    logger.info(f"Using sample PDF: {args.pdf}")
                    break
        
        if args.pdf is None:
            logger.error("No PDF file specified and no sample PDFs found")
            logger.error("Please specify a PDF file with --pdf")
            sys.exit(1)
    
    # Create output directory
    output_dir = Path("door_detector_output")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize pipeline
    pipeline = DoorDetectorPipeline(
        min_width_mm=args.min_width,
        output_dir=output_dir,
        debug=args.debug
    )
    
    # Process the PDF
    pdf_path = Path(args.pdf)
    doors, output_dir = pipeline.process_pdf(pdf_path)
    
    # Print summary
    print("\nDoor Detection Results")
    print("=====================")
    print(f"PDF: {pdf_path.name}")
    print(f"Total doors found: {len(doors)}")
    
    compliant = sum(1 for door in doors if door.get('is_compliant', False))
    print(f"Compliant doors: {compliant} ({compliant/len(doors)*100:.1f}% if doors > 0 else 0}%)")
    print(f"Non-compliant doors: {len(doors) - compliant}")
    
    # Suggest next steps
    print("\nNext Steps")
    print("==========")
    print(f"1. Check output reports in: {output_dir}")
    print(f"2. Review annotated floor plans with highlighted doors")
    print(f"3. Address any non-compliant doors that are below {args.min_width}mm in width")


if __name__ == "__main__":
    main()