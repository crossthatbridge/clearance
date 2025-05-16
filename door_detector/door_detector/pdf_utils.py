"""Utilities for converting PDFs to images."""

import os
import tempfile
from pathlib import Path
from typing import List, Optional

from pdf2image import convert_from_path


def pdf_to_images(
    pdf_path: Path, 
    output_dir: Optional[Path] = None, 
    dpi: int = 400
) -> List[Path]:
    """
    Convert a PDF to a list of images, one per page.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save images to. If None, uses a temp directory
        dpi: Resolution for the output images
        
    Returns:
        List of paths to the created image files
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="door_detector_"))
    else:
        output_dir.mkdir(exist_ok=True, parents=True)
    
    pages = convert_from_path(pdf_path, dpi=dpi, fmt="png")
    out_paths = []
    
    for i, page in enumerate(pages):
        filename = f"{pdf_path.stem}_page{i}.png"
        out_path = output_dir / filename
        page.save(out_path)
        out_paths.append(out_path)
    
    return out_paths