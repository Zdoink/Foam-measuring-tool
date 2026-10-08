# Foam Measuring Tool

An offline desktop application for measuring foam cell structures from microscope images.

You load a microscope picture of foam, and the tool helps turn it into numbers: how many cells there are, how big they are and how round they are. Everything runs locally on your computer, so no images are uploaded anywhere.

> **Status:** early development. Image loading and the Binary / Circle Crop tool work today. Calibration, cell detection and export are planned and are shown in the window as buttons that don't do anything yet. See the [roadmap](#development-roadmap).

**Quick start:** install [Python 3.11+](https://www.python.org/downloads/), download this repository, then double-click **`run.bat`** on Windows (or run `./run.sh` on macOS / Linux). The full steps are in [Getting Started](#getting-started).

**Use ImageJ or Fiji?** The Binary / Circle Crop tool is also available as an ImageJ / Fiji plugin: drop one `.jar` file into ImageJ's `plugins` folder. See [ImageJ / Fiji Plugin](#imagej--fiji-plugin).

---

## What It Does

### Working now

- **Open microscope images**: PNG, JPG, BMP and TIFF, including very large files.
- **Binary / Circle Crop tool**: turns a picture into pure black and white so the foam cell walls stand out from the background.
  - **Control the amount of black vs. white** with a threshold slider, by typing a target black percentage, or with an automatic setting.
  - **Live readout** of the percentage of the image that is black and white.
  - **Crop to a circle**: draw a circle on the image to keep only that region. This is useful for round microscope fields of view.
  - **Second circle for rings and more complex shapes**: add a second circle and combine it with the first:
    - **Ring**: cut circle 2 out of circle 1. A concentric circle 2 gives a ring, and an off-center one gives a crescent.
    - **Add**: join the two circles together.
    - **Overlap**: keep only the area both circles cover, a lens shape.

    The tool shows the shape's area, and for rings the ring width and how far off-center the circles are.
  - **Save the result** at full resolution. It can be saved with a transparent background outside the circle or shape.

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

The black/white percentages shown in the window are counts of black and white pixels. When a crop circle or two-circle shape is active, only the pixels inside it are counted. The **Target black %** and **Auto** settings also look only at those pixels.

### 3. Circle crop

- You draw the circle with the mouse: press where you want the center and drag outward to set the radius. Drag inside the circle to move it, and use the mouse wheel or the Radius box to resize it.
- The circle is stored in full-resolution image coordinates, so the saved file is exact even though you drew on a scaled-down preview.
- **Second circle:** each circle is turned into a mask, a yes/no map of which pixels it covers, and the two masks are combined:
  - Ring = inside circle 1 **and not** inside circle 2
  - Add = inside circle 1 **or** inside circle 2
  - Overlap = inside circle 1 **and** inside circle 2

  The area is the number of pixels in the combined mask. Ring width is circle 1's radius minus circle 2's radius, and center offset is the distance between the two centers.
- The preview shows circle 1 in red and circle 2 in blue. The circle you're editing has the thicker outline, and mouse actions and the Radius box apply to it.
- When saving, the image is cut to the box around the selected shape. Pixels outside the circle are then either made **transparent** (PNG/TIFF) or filled **white** (JPEG/BMP, which can't store transparency).
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

1. Start the app (see [Getting Started](#getting-started)).
2. Click **Open Image** and choose a microscope picture.
3. Click **Binary / Circle Crop**.
4. Adjust the black/white amount using the slider, **Target black %** with **Apply**, or **Auto (Otsu)**.
5. Optionally tick **Crop to circle** and draw a circle on the image.
   - For a ring or other two-circle shape, also tick **Add a second circle**. It starts as a ring half the size of circle 1.
   - Pick how the circles combine (Ring, Add or Overlap). Use **Edit: Circle 1 / Circle 2** to choose which circle the mouse moves and resizes.
   - **Center Circle 2 on Circle 1** lines them up for a perfect ring.
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
├── run.bat                  ← Windows: double-click to start the app
├── run.sh                   ← macOS / Linux: run to start the app
├── main.py                  ← the app's entry point
├── requirements.txt         ← Python packages the app needs
├── src/
│   ├── gui/
│   │   ├── main_window.py   ← main window and toolbar
│   │   └── image_viewer.py  ← image display (mouse wheel to zoom)
│   ├── plugins/
│   │   └── binary_image/    ← Binary / Circle Crop tool
│   │       ├── processing.py  ← image math (threshold, Otsu, circle and ring shapes)
│   │       └── dialog.py      ← the tool's window and circle drawing
│   ├── vision/              ← preprocessing, segmentation, calibration, measurements
│   ├── reporting/           ← CSV / Excel export (planned)
│   └── database/            ← project storage (planned)
├── tests/                   ← automated tests
└── imagej-plugin/           ← the same tool as an ImageJ / Fiji plugin
    ├── Foam_Binary_Ring.jar ← drop this into ImageJ's plugins folder
    ├── src/                 ← plugin source (Java)
    └── test/                ← plugin tests
```

---

## Getting Started

### 1. Install Python (one time)

You need **Python 3.11 or newer**.

- **Windows:** download it from [python.org/downloads](https://www.python.org/downloads/). During installation, **tick "Add python.exe to PATH"**.
- **macOS:** download it from [python.org/downloads](https://www.python.org/downloads/), or run `brew install python`.
- **Linux:** use your package manager, e.g. `sudo apt install python3 python3-venv`.

### 2. Download the app

Either:

- **Without git:** on the GitHub page, click the green **Code** button → **Download ZIP**, then unzip it anywhere, or
- **With git:**

  ```powershell
  git clone https://github.com/Zdoink/Foam-measuring-tool.git
  ```

### 3. Start the app

- **Windows:** open the folder and **double-click `run.bat`**.
- **macOS / Linux:** open a terminal in the folder and run:

  ```bash
  ./run.sh
  ```

The **first start takes a few minutes**: the launcher creates a private Python environment in a `.venv` folder and downloads the required packages (about 800 MB). After that, the app opens straight away.

> To redo the setup (for example after `requirements.txt` changes), delete the `.venv` folder and start the launcher again.

### Manual setup (alternative)

If you prefer to set things up yourself, run these commands in the project folder:

```powershell
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # macOS / Linux
pip install -r requirements.txt
python main.py
```

### Troubleshooting

| Problem | Fix |
| ------- | --- |
| `run.bat` says Python was not found | Install Python as in step 1, making sure "Add python.exe to PATH" is ticked, then try again. |
| Package installation fails | Check your internet connection, delete the `.venv` folder and start the launcher again. |
| Linux: error about `libEGL`, `libGL` or `xcb` | Install Qt's system libraries: `sudo apt install libegl1 libgl1 libxkbcommon0 libxcb-cursor0` |
| macOS: `permission denied` for `./run.sh` | Run `chmod +x run.sh` once. |

---

## Running the Tests

In the project folder, with the environment set up:

```powershell
.venv\Scripts\python -m pytest tests     # Windows
.venv/bin/python -m pytest tests          # macOS / Linux
```

---

## The Binary / Circle Crop Plugin

### Installing it

The plugin is **built in**: if you downloaded the app as described in [Getting Started](#getting-started), you already have it. The **Binary / Circle Crop** button is in the toolbar, and no extra packages are needed.

If you have an **older copy** of the app (one with a `Foam-measuring-tool-main` subfolder), the project layout has changed since then. The simplest fix is to download the app again, or run `git pull` if you cloned it.

### Using the plugin from your own code

The plugin can also be used without the main window. Run this from the project folder:

```python
import cv2
from src.plugins.binary_image import processing, open_dialog

image = cv2.imread("foam.png")

# Interactive window
open_dialog(image)

# Or call the image functions directly
gray = processing.to_gray(image)
threshold = processing.threshold_for_black_fraction(gray, 0.30)  # 30 % black
binary = processing.binarize(gray, threshold)
cropped = processing.crop_circle(binary, cx=500, cy=400, radius=300)
processing.save_image("foam_binary.png", cropped)

# Ring: outer circle minus inner circle, both as (cx, cy, radius)
ring = processing.shape_mask(binary.shape, (500, 400, 300), (500, 400, 150), processing.SHAPE_RING)
print("Black inside ring:", processing.black_fraction(binary, ring))
processing.save_image("foam_ring.png", processing.crop_to_mask(binary, ring))
```

`open_dialog` needs a running Qt application. Inside the main app, one already exists.

---

## ImageJ / Fiji Plugin

The Binary / Circle Crop tool is also available as a plugin for **ImageJ** and **Fiji**. It doesn't need Python or the rest of this app.

**Install:** download [`imagej-plugin/Foam_Binary_Ring.jar`](imagej-plugin/Foam_Binary_Ring.jar), copy it into ImageJ's `plugins` folder (`Fiji.app/plugins/` for Fiji), and restart. Run it from **Plugins ▸ Foam Tools ▸ Foam Binary / Ring...**

It has the same controls: threshold slider, Target black %, Auto (Otsu), invert, and circle / ring / add / overlap shapes. It also uses ImageJ's own features:

- Draw circles with the **Oval tool**, then click a button to use the selection as circle 1 or circle 2.
- Results are given in **µm** when the image has a scale (**Analyze ▸ Set Scale...**).
- Measurements go into the **Results** table, and the shape can be added to the **ROI Manager**.
- It's **macro recordable**, for batch processing.

Full instructions are in [`imagej-plugin/README.md`](imagej-plugin/README.md).

---

## Development Roadmap

### Phase 1

- [x] Project structure
- [x] GUI window
- [x] Image loading
- [x] Binary conversion and circle / ring crop tool
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
