# Foam Measuring Tool

An offline desktop application for measuring foam cell structures from microscope images.

## Features

- Import microscope images
- Manual image calibration (µm/pixel)
- Image preprocessing
- Foam cell segmentation
- Cell measurement and analysis
- CSV export
- Excel export (planned)
- PDF reports (planned)
- Batch processing (planned)

---

## Project Goals

This project aims to provide an accurate and repeatable method for measuring foam cell characteristics from microscope images.

Measurements include:

- Cell area
- Cell perimeter
- Equivalent diameter
- Circularity
- Cell count
- Statistical summaries

---

## Technology Stack

### Language

- Python 3.11+

### Computer Vision

- OpenCV
- NumPy
- SciPy
- scikit-image

### Desktop GUI

- PySide6

### Reporting

- Pandas
- OpenPyXL
- ReportLab

### Testing

- PyTest

---

## Project Structure

```text
Foam-measuring-tool/
│
├── main.py
├── requirements.txt
│
├── src/
│   ├── gui/
│   ├── vision/
│   ├── reporting/
│   └── database/
│
├── tests/
│
└── assets/
```

---

## Installation

Clone the repository:

```powershell
git clone https://github.com/Zdoink/Foam-measuring-tool.git
```

Move into the project folder:

```powershell
cd Foam-measuring-tool
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

---

## Running the Application

From the project root:

```powershell
python main.py
```

---

## Development Roadmap

### Phase 1

- [x] Project structure
- [X] GUI window
- [X] Image loading
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

## Example Workflow

1. Load microscope image
2. Calibrate image using scale bar
3. Run segmentation
4. Review detected cells
5. Export measurements
6. Generate report

---

## License

MIT License
