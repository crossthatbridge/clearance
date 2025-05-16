# Door Detector

A tool to detect and measure doors in floor plan PDFs for accessibility compliance checking.

## Features

- Converts PDF floor plans to images at high resolution
- Detects the scale of drawings from text and graphical scales
- Identifies door symbols using ML-based detection or template matching
- Measures door widths accurately
- Reports door measurements with compliance status
- Handles various edge cases including:
  - Rotated or skewed scans
  - Mixed scales in one PDF
  - Faded printed scans
  - Various door symbol styles

## Installation

### Prerequisites

- Python 3.10+
- Poppler (for pdf2image)
- Tesseract OCR (for scale detection)

### Install Dependencies

#### macOS

```bash
brew install poppler tesseract
```

#### Ubuntu/Debian

```bash
sudo apt-get install poppler-utils tesseract-ocr
```

### Install Package

```bash
pip install .
```

## Usage

### Command Line

```bash
door-detector /path/to/floorplan.pdf
```

Options:

```
--min-width FLOAT    Minimum acceptable door width in mm (default: 900mm)
--output-dir DIR     Directory to save output files
--dpi INT            Resolution for PDF conversion (default: 400)
--recursive          Process PDFs in subdirectories
--debug              Enable debug mode
```

### Python API

```python
from pathlib import Path
from door_detector.cli import DoorDetectorPipeline

# Initialize pipeline
pipeline = DoorDetectorPipeline(
    min_width_mm=900.0,
    output_dir=Path("./output"),
    dpi=400,
    debug=False
)

# Process a PDF
doors, output_dir = pipeline.process_pdf(Path("floorplan.pdf"))

# Print summary
print(f"Total doors found: {len(doors)}")
compliant = sum(1 for door in doors if door.get('is_compliant', False))
print(f"Compliant doors: {compliant}")
print(f"Non-compliant doors: {len(doors) - compliant}")
```

## How It Works

The system works through these steps:

1. **PDF to Image Conversion**: Converts each page of the PDF to a high-resolution image
2. **Scale Detection**: Finds and parses scale information (e.g., "1:50") or measures graphic scale bars
3. **Door Detection**: Uses YOLOv8 object detection or template matching to locate door symbols
4. **Measurement**: Calculates door width based on bounding box dimensions and drawing scale
5. **Reporting**: Generates CSV/JSON reports and annotated floor plans with door measurements

## Output

For each PDF processed, the system generates:

- Annotated floor plan images showing door measurements and compliance status
- CSV report with door locations and measurements
- JSON report with detailed door information and compliance summary

## Example

Try the included example script:

```bash
python example.py
```

This will process a sample floor plan from the assets directory and generate reports.

## Customization

### Door Detection Models

For best results, fine-tune a YOLOv8 model on your specific floor plan door types:

1. Collect 50-100 floor plan images
2. Label door symbols using a tool like [Roboflow](https://roboflow.com/)
3. Train a custom YOLOv8 model
4. Place the trained model weight file in `door_detector/models/doors_floorplan_yolov8.pt`

### Compliance Standards

The default minimum door width is 900mm, based on common accessibility standards. Adjust this using the `--min-width` parameter to match your local building codes.

## Limitations

- Door thickness measurement requires accurate scale detection
- Performance depends on drawing clarity and consistency
- Unusual door symbols may require custom detection models

## Troubleshooting

- If scale detection fails, ensure your drawings have visible scale text or bars
- For poor quality scans, try increasing the DPI to 600
- If door detection misses doors, consider training a custom model