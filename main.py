import os
import sys

# Large microscope images need more than Qt's default image memory limit
os.environ["QT_IMAGEIO_MAXALLOC"] = "2048"

# Allow running from any folder (e.g. double-clicking main.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.main_window import start_app


if __name__ == "__main__":
    start_app()
