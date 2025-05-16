Below is a pragmatic outline (with some starter code) that I’ve seen work on real-world drawings. It is deliberately modular so you can swap in better components as you refine detection accuracy.

---

## 1 Convert each PDF page to a clean raster

```python
from pdf2image import convert_from_path   # poppler under the hood
from pathlib import Path

def pdf_to_images(pdf_path: Path, dpi: int = 400) -> list[Path]:
    pages = convert_from_path(pdf_path, dpi=dpi, fmt="png")
    out = []
    for i, page in enumerate(pages):
        p = pdf_path.with_suffix(f".page{i}.png")
        page.save(p)
        out.append(p)
    return out
```

*400 DPI keeps line detail while avoiding absurd file sizes.*

---

## 2 Infer a physical scale for each page

Two fall-backs:

1. **OCR for a ratio**
   Search the whole sheet for a pattern like `1 : 50` or `SCALE 1/4" = 1'-0"` and parse it.
2. **Detect a graphic bar scale**
   Look for a horizontal line with tick marks and numeric labels (`0 1 2 m`).  Measure the pixel length between the first and last tick, read the label with OCR, and get *mm / px*.

```python
import cv2, numpy as np, pytesseract, re

def find_numeric_scale_text(img) -> float | None:
    text = pytesseract.image_to_string(img, config='--psm 6')
    m = re.search(r'1\s*[:/]\s*(\d+)', text)
    if m:
        return 1 / float(m.group(1))   # drawing-unit / real-unit
    return None
```

If both methods fail, raise and log; the program can’t guess dimensions responsibly.

---

## 3 Detect door symbols

A fast, surprisingly robust baseline is a **YOLO-style object detector** trained on floor-plan icons:

```python
from ultralytics import YOLO

model = YOLO("doors_floorplan_yolov8.pt")  # e.g. fine-tuned weights
preds  = model(img)                        # returns bounding boxes for doors
```

* A ready-made public model is hosted on Roboflow (“Detecting Doors From Floor Plan”) ([Roboflow][1]).
* If you want pure-Python and no ML dependency, build a template-matching fallback: threshold → Canny → Hough lines → detect a quarter-circle arc + adjacent rectangle.  It’s brittle but works on very regular CAD exports.

---

## 4 Measure each door leaf

For each detected bounding box:

```python
def door_width_mm(bbox, mm_per_px):
    x1,y1,x2,y2 = bbox.xyxy[0]  # YOLO format
    w_px  = abs(x2 - x1)
    h_px  = abs(y2 - y1)
    leaf  = min(w_px, h_px)     # door leaf is the narrow side
    return leaf * mm_per_px
```

* Rotate the cropped patch so that the swing arc is always in the same quadrant, then skeletonise and take the maximum thickness if you need sub-pixel precision for angled doors.
* Flag anything < 900 mm (typical UK accessibility minimum) or whatever rule set you enforce.

---

## 5 Aggregate and report

```python
import pandas as pd

def evaluate(pdf):
    rows = []
    for page in pdf_to_images(pdf):
        scale = find_numeric_scale_text(cv2.imread(str(page)))
        if scale is None:
            continue
        preds = model(page)
        for box in preds:
            w = door_width_mm(box, mm_per_px=scale)
            rows.append({
                "page": page.name,
                "x":    int(box.xyxy[0][0]),
                "y":    int(box.xyxy[0][1]),
                "width_mm": round(w, 1),
                "pass": w >= 900
            })
    return pd.DataFrame(rows)
```

Export to CSV/Excel or raise exceptions on failures so the pipeline fits your CI.

---

## 6 Edge-case hardening

| Problem                        | Mitigation                                                         |
| ------------------------------ | ------------------------------------------------------------------ |
| Rotated or skewed scans        | Deskew with Hough‐detected principal axis before OCR/ML.           |
| Mixed scales in one PDF        | Cache `mm_per_px` per page, never assume global.                   |
| Faded printed scans            | Adaptive histogram equalisation (CLAHE) before detection.          |
| Unorthodox door graphics       | Keep a small human-review sample; retrain YOLO monthly.            |
| Missing scale text **and** bar | Reject the page — guessing dimensions is professional malpractice. |

---

## 7 Why not rely only on dimension strings?

You could OCR dimension lines (`895`, `910`…) near each opening, but drafters omit them more often than you’d think. Anchoring on the symbol ensures the physical geometry really matches the intent.

---

### References worth skimming

* YOLOv8 floor-plan model on Roboflow ([Roboflow][1])
* LayoutParser (Detectron2 wrappers) for quick Mask R-CNN prototyping ([layout-parser.readthedocs.io][2])
* Example YOLOv8 floor-plan project with training code ([GitHub][3])

