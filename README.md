# Foam Measuring Tool

An offline desktop application for measuring foam cell structures from microscope images.

You load a microscope picture of foam, and the tool helps turn it into numbers: how many cells there are, how big they are and how round they are. Everything runs locally on your computer, so no images are uploaded anywhere.

> **Status:** early development. Image loading and the Binary / Circle Crop tool work today. Calibration, cell detection and export are planned and are shown in the window as buttons that don't do anything yet. See the [roadmap](#development-roadmap).

---

## What It Does

### Working now

- **Open microscope images**: PNG, JPG, BMP and TIFF, including very large files.
- **Binary / Circle Crop tool**: turns a picture into pure black and white so the foam cell walls stand out from the background.
  - **Control the amount of black vs. white** with a threshold slider, by typing a target black percentage, or with an automatic setting.
  - **Live readout** of the percentage of the image that is black and white.
  - **Crop to a circle**: draw a circle on the image to keep only that region. This is useful for round microscope fields of view.
  - **Save the result** at full resolution. It can be saved with a transparent background outside the circle.

### Planned

- Manual calibration of the image scale (µm per pixel) using a scale bar
- Automatic foam cell detection (segmentation)
- Measurement of each cell: area, perimeter, equivalent diameter and circularity, plus cell count and summary statistics
- CSV, Excel and PDF reports
- Batch processing of many images

---

## How It Works

### 1. Loading an image

The image is read with OpenCV (`cv2.imread`) and kept at full resolution in memory. For display, a smaller preview is made (at most 1000 px on its longest side), so even huge microscope images stay responsive on screen.

### 2. Converting to black and white (binarization)

1. The color image is converted to **grayscale**, so each pixel becomes one brightness value from 0 (black) to 255 (white).
2. Every pixel is compared with a **threshold**:
   - brightness **below** the threshold → **black**
   - brightness **at or above** the threshold → **white**

   So **raising the threshold makes more of the image black**, and lowering it makes more of the image white.
3. There are three ways to pick the threshold:
   - **Slider (0–255)**: set it by hand and watch the preview update live.
   - **Target black %**: the tool builds a histogram, a count of how many pixels have each brightness. It then picks the threshold that makes your requested percentage of pixels black. For example, if you ask for 30 %, it finds the brightness that 30 % of the pixels fall below.
   - **Auto (Otsu)**: [Otsu's method](https://en.wikipedia.org/wiki/Otsu%27s_method) looks at the histogram and picks the threshold that best separates the image into two groups, dark and light. This usually gives a good split between cell walls and background with no manual tuning.
4. **Invert** swaps black and white, for images where the cell walls are lighter than the background.

The black/white percentages shown in the window are counts of black and white pixels. When a crop circle is active, only the pixels inside the circle are counted.

### 3. Circle crop

- You draw the circle with the mouse: press where you want the center and drag outward to set the radius. Drag inside the circle to move it, and use the mouse wheel or the Radius box to resize it.
- The circle is stored in full-resolution image coordinates, so the saved file is exact even though you drew on a scaled-down preview.
- When saving, the image is cut to the square around the circle. Pixels outside the circle are then either made **transparent** (PNG/TIFF) or filled **white** (JPEG/BMP, which can't store transparency).
- Files are written with `cv2.imencode`, so saving works in folders with non-English characters in the path, such as OneDrive folders on Windows.

### 4. Measuring cells (planned)

The intended pipeline, with early pieces already in `src/vision/`:

1. **Preprocess** (`preprocessing.py`): convert to grayscale and apply a Gaussian blur to reduce noise.
2. **Segment** (`segmentation.py`): apply an Otsu threshold to separate cells from cell walls.
3. **Calibrate** (`calibration.py`): convert pixels to micrometres from a known length, where µm/pixel = known length in µm ÷ length in pixels.
4. **Measure** (`measurements.py`): compute the size and shape of each detected cell.
5. **Export** (`src/reporting/`): write the results to CSV or Excel.

---

## Using the App

1. Start the app (see [Running the Application](#running-the-application)).
2. Click **Open Image** and choose a microscope picture.
3. Click **Binary / Circle Crop**.
4. Adjust the black/white amount using the slider, **Target black %** with **Apply**, or **Auto (Otsu)**.
5. Optionally tick **Crop to circle** and draw a circle on the image.
6. Click **Save Image...** to save the result.

---

## Technology Stack

| Area            | Libraries                     |
| --------------- | ----------------------------- |
| Language        | Python 3.11+                  |
| Computer vision | OpenCV, NumPy, SciPy, scikit-image |
| Desktop GUI     | PySide6 (Qt)                  |
| Reporting       | Pandas, OpenPyXL, ReportLab   |
| Testing         | PyTest                        |

---

## Project Structure

```text
Foam-measuring-tool/
├── README.md
└── Foam-measuring-tool-main/        ← the application lives here
    ├── main.py                      ← start the app with this
    ├── requirements.txt
    ├── src/
    │   ├── gui/
    │   │   ├── main_window.py       ← main window and toolbar
    │   │   └── image_viewer.py      ← image display
    │   ├── plugins/
    │   │   └── binary_image/        ← Binary / Circle Crop tool
    │   │       ├── processing.py    ← image math (threshold, Otsu, circle crop)
    │   │       └── dialog.py        ← the tool's window and circle drawing
    │   ├── vision/                  ← preprocessing, segmentation, calibration, measurements
    │   ├── reporting/               ← CSV / Excel export (planned)
    │   └── database/                ← project storage (planned)
    └── tests/                       ← automated tests
```

---

## Installation

Clone the repository:

```powershell
git clone https://github.com/Zdoink/Foam-measuring-tool.git
cd Foam-measuring-tool\Foam-measuring-tool-main
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

---

## Running the Application

From the `Foam-measuring-tool-main` folder:

```powershell
python main.py
```

## Running the Tests

From the `Foam-measuring-tool-main` folder:

```powershell
python -m pytest tests
```

---

## Development Roadmap

### Phase 1

- [x] Project structure
- [x] GUI window
- [x] Image loading
- [x] Binary conversion and circle crop tool
- [ ] Manual calibration
- [ ] Basic segmentation

### Phase 2

- [ ] Measurement engine
- [ ] CSV export
- [ ] Overlay visualization
- [ ] Statistics panel

### Phase 3

- [ ] Excel export
- [ ] PDF reporting
- [ ] SQLite storage
- [ ] Batch processing

### Phase 4

- [ ] Automatic scale bar detection
- [ ] Machine learning segmentation
- [ ] Standalone Windows executable

---

## License

MIT License
