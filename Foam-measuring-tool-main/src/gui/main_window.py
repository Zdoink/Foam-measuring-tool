import sys

import cv2

from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFrame
)


class MainWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.image_path = None

        self.setWindowTitle(
            "Foam Measure Pro"
        )

        self.resize(
            1000,
            700
        )

        self.build_ui()

    def build_ui(self):

        main_layout = QVBoxLayout()

        #
        # TOOLBAR
        #

        toolbar = QHBoxLayout()

        self.open_button = QPushButton(
            "Open Image"
        )

        self.calibrate_button = QPushButton(
            "Calibrate"
        )

        self.detect_button = QPushButton(
            "Detect Cells"
        )

        self.export_button = QPushButton(
            "Export"
        )

        toolbar.addWidget(
            self.open_button
        )

        toolbar.addWidget(
            self.calibrate_button
        )

        toolbar.addWidget(
            self.detect_button
        )

        toolbar.addWidget(
            self.export_button
        )

        toolbar.addStretch()

        #
        # CONTENT AREA
        #

        content = QHBoxLayout()

        #
        # IMAGE VIEWER
        #

        self.image_viewer = QLabel()

        self.image_viewer.setAlignment(
            Qt.AlignCenter
        )

        self.image_viewer.setFrameShape(
            QFrame.Box
        )

        self.image_viewer.setMinimumSize(
            650,
            500
        )

        #
        # RESULTS PANEL
        #

        results_panel = QVBoxLayout()

        self.cells_label = QLabel(
            "Cells: --"
        )

        self.diameter_label = QLabel(
            "Mean Diameter: --"
        )

        self.scale_label = QLabel(
            "Scale: Not Set"
        )

        self.status_label = QLabel(
            "Ready"
        )

        results_panel.addWidget(
            QLabel("Measurements")
        )

        results_panel.addWidget(
            self.cells_label
        )

        results_panel.addWidget(
            self.diameter_label
        )

        results_panel.addWidget(
            self.scale_label
        )

        results_panel.addWidget(
            self.status_label
        )

        results_panel.addStretch()

        content.addWidget(
            self.image_viewer
        )

        content.addLayout(
            results_panel
        )

        #
        # FOOTER
        #

        self.footer = QLabel(
            "Status: Ready"
        )

        #
        # CONNECTIONS
        #

        self.open_button.clicked.connect(
            self.open_image
        )

        #
        # BUILD WINDOW
        #

        main_layout.addLayout(
            toolbar
        )

        main_layout.addLayout(
            content
        )

        main_layout.addWidget(
            self.footer
        )

        self.setLayout(
            main_layout
        )

    def open_image(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )

        if not filename:
            return

        self.image_path = filename

        #
        # Load original image with OpenCV
        #

        image = cv2.imread(filename)

        if image is None:

            self.footer.setText(
                "Failed to load image."
            )

            return

        #
        # Get dimensions
        #

        height, width = image.shape[:2]

        #
        # Create UI preview
        #

        max_dimension = 1000

        scale = min(
            max_dimension / width,
            max_dimension / height
        )

        scale = min(scale, 1.0)

        preview = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale
        )

        #
        # OpenCV uses BGR
        # Qt uses RGB
        #

        preview = cv2.cvtColor(
            preview,
            cv2.COLOR_BGR2RGB
        )

        #
        # Convert to QImage
        #

        from PySide6.QtGui import QImage

        h, w, ch = preview.shape

        bytes_per_line = ch * w

        qimage = QImage(
            preview.data,
            w,
            h,
            bytes_per_line,
            QImage.Format_RGB888
        )

        #
        # Display
        #

        pixmap = QPixmap.fromImage(
            qimage
        )

        self.image_viewer.setPixmap(
            pixmap
        )

        self.footer.setText(
            f"Loaded: {width} x {height}"
        )


def start_app():

    app = QApplication(
        sys.argv
    )

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )
