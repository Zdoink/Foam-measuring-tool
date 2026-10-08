"""
Qt dialog for the binary image plugin.

- Threshold slider controls how much of the picture is black vs. white
- "Target black %" picks the threshold that gives a requested amount of black
- Circle crop: drag on the image to draw a circle, drag inside it to move
  it, scroll the mouse wheel to resize it
"""

import math

import cv2
import numpy as np

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QImage, QPainter, QPainterPath, QPen, QColor

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import processing


PREVIEW_MAX_DIMENSION = 1000


def numpy_to_qimage(image):
    """Convert a gray or BGR numpy image to a QImage (owns its memory)."""

    image = np.ascontiguousarray(image)

    if image.ndim == 2:
        h, w = image.shape
        qimage = QImage(image.data, w, h, w, QImage.Format_Grayscale8)
    else:
        rgb = np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        h, w, _ = rgb.shape
        qimage = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)

    return qimage.copy()


class CircleCanvas(QWidget):
    """Shows an image and lets the user draw / move / resize a circle on it."""

    circleChanged = Signal()

    def __init__(self, image_size, parent=None):
        super().__init__(parent)

        # Full resolution image size (width, height); the circle is kept in
        # full resolution coordinates so saving is exact.
        self.image_width, self.image_height = image_size

        self.qimage = None
        self.circle_enabled = False
        self.circle = None  # (cx, cy, radius) in image pixels

        self._drag_mode = None
        self._drag_start = None
        self._circle_start = None

        self.setMinimumSize(500, 400)
        self.setMouseTracking(True)

    #
    # Public API
    #

    def set_image(self, qimage):
        self.qimage = qimage
        self.update()

    def set_circle_enabled(self, enabled):
        self.circle_enabled = enabled

        if enabled and self.circle is None:
            self.reset_circle()

        self.update()

    def reset_circle(self):
        self.circle = (
            self.image_width / 2,
            self.image_height / 2,
            min(self.image_width, self.image_height) / 2,
        )
        self.update()
        self.circleChanged.emit()

    def set_radius(self, radius):
        if self.circle is None:
            return

        cx, cy, _ = self.circle
        self.circle = (cx, cy, max(1.0, radius))
        self.update()
        self.circleChanged.emit()

    #
    # Coordinate mapping
    #

    def _image_rect(self):
        """Rectangle (widget coordinates) where the image is drawn."""

        if self.image_width == 0 or self.image_height == 0:
            return QRectF()

        scale = min(
            self.width() / self.image_width,
            self.height() / self.image_height,
        )

        w = self.image_width * scale
        h = self.image_height * scale

        return QRectF(
            (self.width() - w) / 2,
            (self.height() - h) / 2,
            w,
            h,
        )

    def _scale(self):
        rect = self._image_rect()
        return rect.width() / self.image_width if self.image_width else 1.0

    def _to_image(self, point):
        rect = self._image_rect()
        scale = self._scale()
        return (
            (point.x() - rect.x()) / scale,
            (point.y() - rect.y()) / scale,
        )

    #
    # Painting
    #

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        painter.fillRect(self.rect(), QColor(60, 60, 60))

        if self.qimage is None:
            return

        rect = self._image_rect()
        painter.drawImage(rect, self.qimage)

        if not (self.circle_enabled and self.circle):
            return

        cx, cy, radius = self.circle
        scale = self._scale()

        center = QPointF(rect.x() + cx * scale, rect.y() + cy * scale)
        r = radius * scale

        # Dim everything outside the circle
        outside = QPainterPath()
        outside.addRect(rect)
        inside = QPainterPath()
        inside.addEllipse(center, r, r)

        painter.fillPath(outside.subtracted(inside), QColor(0, 0, 0, 150))

        painter.setPen(QPen(QColor(255, 60, 60), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, r, r)

    #
    # Mouse interaction
    #

    def mousePressEvent(self, event):
        if not self.circle_enabled or event.button() != Qt.LeftButton:
            return

        x, y = self._to_image(event.position())

        self._drag_start = (x, y)
        self._circle_start = self.circle

        if self.circle and math.hypot(x - self.circle[0], y - self.circle[1]) <= self.circle[2]:
            self._drag_mode = "move"
        else:
            self._drag_mode = "draw"
            self.circle = (x, y, 1.0)
            self.update()

    def mouseMoveEvent(self, event):
        if self._drag_mode is None:
            return

        x, y = self._to_image(event.position())
        sx, sy = self._drag_start

        if self._drag_mode == "move":
            cx, cy, radius = self._circle_start
            self.circle = (cx + x - sx, cy + y - sy, radius)
        else:
            self.circle = (sx, sy, max(1.0, math.hypot(x - sx, y - sy)))

        self.update()
        self.circleChanged.emit()

    def mouseReleaseEvent(self, event):
        if self._drag_mode is not None:
            self._drag_mode = None
            self.circleChanged.emit()

    def wheelEvent(self, event):
        if not (self.circle_enabled and self.circle):
            return

        factor = 1.05 if event.angleDelta().y() > 0 else 1 / 1.05
        self.set_radius(self.circle[2] * factor)


class BinaryImageDialog(QDialog):
    """Convert an image to black/white and optionally crop it to a circle."""

    def __init__(self, image, parent=None):
        super().__init__(parent)

        if image is None:
            raise ValueError("No image to convert.")

        self.setWindowTitle("Binary Image / Circle Crop")
        self.resize(1200, 800)

        self.original = image
        self.gray = processing.to_gray(image)

        height, width = self.gray.shape

        # Downscaled copies used for the live preview
        self.preview_scale = min(1.0, PREVIEW_MAX_DIMENSION / max(width, height))

        if self.preview_scale < 1.0:
            size = (
                max(1, round(width * self.preview_scale)),
                max(1, round(height * self.preview_scale)),
            )
            self.preview_original = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
            self.preview_gray = cv2.resize(self.gray, size, interpolation=cv2.INTER_AREA)
        else:
            self.preview_original = image
            self.preview_gray = self.gray

        self.build_ui(width, height)

        self.threshold_slider.setValue(processing.otsu_threshold(self.gray))
        self.refresh()

    #
    # UI
    #

    def build_ui(self, width, height):
        layout = QHBoxLayout(self)

        self.canvas = CircleCanvas((width, height))
        layout.addWidget(self.canvas, stretch=1)

        controls = QVBoxLayout()
        layout.addLayout(controls)

        #
        # BLACK / WHITE AMOUNT
        #

        amount_group = QGroupBox("Black / White Amount")
        amount_layout = QVBoxLayout(amount_group)

        amount_layout.addWidget(QLabel("Threshold (higher = more black)"))

        slider_row = QHBoxLayout()

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 255)

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 255)

        slider_row.addWidget(self.threshold_slider)
        slider_row.addWidget(self.threshold_spin)
        amount_layout.addLayout(slider_row)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Target black %"))

        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(0.0, 100.0)
        self.target_spin.setDecimals(1)
        self.target_spin.setSuffix(" %")
        self.target_spin.setValue(50.0)
        target_row.addWidget(self.target_spin)

        self.target_button = QPushButton("Apply")
        target_row.addWidget(self.target_button)
        amount_layout.addLayout(target_row)

        self.auto_button = QPushButton("Auto (Otsu)")
        amount_layout.addWidget(self.auto_button)

        self.invert_check = QCheckBox("Invert black / white")
        amount_layout.addWidget(self.invert_check)

        self.show_original_check = QCheckBox("Show original image")
        amount_layout.addWidget(self.show_original_check)

        self.amount_label = QLabel()
        self.amount_label.setStyleSheet("font-weight: bold;")
        amount_layout.addWidget(self.amount_label)

        controls.addWidget(amount_group)

        #
        # CIRCLE CROP
        #

        crop_group = QGroupBox("Circle Crop")
        crop_layout = QVBoxLayout(crop_group)

        self.crop_check = QCheckBox("Crop to circle")
        crop_layout.addWidget(self.crop_check)

        help_label = QLabel(
            "Drag on the image to draw a circle.\n"
            "Drag inside the circle to move it.\n"
            "Scroll the mouse wheel to resize."
        )
        help_label.setWordWrap(True)
        crop_layout.addWidget(help_label)

        radius_row = QHBoxLayout()
        radius_row.addWidget(QLabel("Radius (px)"))

        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(1, max(width, height))
        radius_row.addWidget(self.radius_spin)
        crop_layout.addLayout(radius_row)

        self.reset_circle_button = QPushButton("Reset Circle")
        crop_layout.addWidget(self.reset_circle_button)

        self.transparent_check = QCheckBox("Transparent outside circle (PNG)")
        self.transparent_check.setChecked(True)
        crop_layout.addWidget(self.transparent_check)

        self.set_crop_controls_enabled(False)

        controls.addWidget(crop_group)

        controls.addStretch()

        #
        # SAVE / CLOSE
        #

        self.save_button = QPushButton("Save Image...")
        self.close_button = QPushButton("Close")

        controls.addWidget(self.save_button)
        controls.addWidget(self.close_button)

        #
        # CONNECTIONS
        #

        self.threshold_slider.valueChanged.connect(self.threshold_spin.setValue)
        self.threshold_spin.valueChanged.connect(self.threshold_slider.setValue)
        self.threshold_slider.valueChanged.connect(self.refresh)

        self.target_button.clicked.connect(self.apply_target)
        self.auto_button.clicked.connect(self.apply_auto)
        self.invert_check.toggled.connect(self.refresh)
        self.show_original_check.toggled.connect(self.refresh)

        self.crop_check.toggled.connect(self.toggle_crop)
        self.canvas.circleChanged.connect(self.on_circle_changed)
        self.radius_spin.valueChanged.connect(self.on_radius_spin)
        self.reset_circle_button.clicked.connect(self.canvas.reset_circle)

        self.save_button.clicked.connect(self.save)
        self.close_button.clicked.connect(self.accept)

    def set_crop_controls_enabled(self, enabled):
        self.radius_spin.setEnabled(enabled)
        self.reset_circle_button.setEnabled(enabled)
        self.transparent_check.setEnabled(enabled)

    #
    # State helpers
    #

    def threshold(self):
        return self.threshold_slider.value()

    def crop_enabled(self):
        return self.crop_check.isChecked() and self.canvas.circle is not None

    def preview_mask(self):
        """Circle mask at preview resolution, or None when not cropping."""

        if not self.crop_enabled():
            return None

        cx, cy, radius = self.canvas.circle
        s = self.preview_scale

        return processing.circle_mask(self.preview_gray.shape, cx * s, cy * s, radius * s)

    #
    # Slots
    #

    def refresh(self):
        binary = processing.binarize(
            self.preview_gray,
            self.threshold(),
            self.invert_check.isChecked(),
        )

        if self.show_original_check.isChecked():
            self.canvas.set_image(numpy_to_qimage(self.preview_original))
        else:
            self.canvas.set_image(numpy_to_qimage(binary))

        black = processing.black_fraction(binary, self.preview_mask()) * 100

        where = " (inside circle)" if self.crop_enabled() else ""

        self.amount_label.setText(
            f"Black: {black:.1f} %   White: {100 - black:.1f} %{where}"
        )

    def apply_target(self):
        fraction = self.target_spin.value() / 100

        # With invert on, black pixels are the ones above the threshold
        if self.invert_check.isChecked():
            fraction = 1 - fraction

        self.threshold_slider.setValue(
            processing.threshold_for_black_fraction(
                self.preview_gray, fraction, self.preview_mask()
            )
        )

    def apply_auto(self):
        self.threshold_slider.setValue(
            processing.otsu_threshold(self.preview_gray, self.preview_mask())
        )

    def toggle_crop(self, enabled):
        self.canvas.set_circle_enabled(enabled)
        self.set_crop_controls_enabled(enabled)
        self.on_circle_changed()

    def on_circle_changed(self):
        if self.canvas.circle is not None:
            self.radius_spin.blockSignals(True)
            self.radius_spin.setValue(round(self.canvas.circle[2]))
            self.radius_spin.blockSignals(False)

        self.refresh()

    def on_radius_spin(self, value):
        self.canvas.set_radius(value)

    #
    # Output
    #

    def result_image(self):
        """Full resolution result (binary, or original if shown), cropped if enabled."""

        if self.show_original_check.isChecked():
            image = self.original
        else:
            image = processing.binarize(
                self.gray,
                self.threshold(),
                self.invert_check.isChecked(),
            )

        if self.crop_enabled():
            cx, cy, radius = self.canvas.circle
            image = processing.crop_circle(
                image,
                cx,
                cy,
                radius,
                transparent=self.transparent_check.isChecked(),
            )

        return image

    def save(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            "binary.png",
            "PNG (*.png);;TIFF (*.tif *.tiff);;BMP (*.bmp);;JPEG (*.jpg *.jpeg)",
        )

        if not filename:
            return

        if "." not in filename.rsplit("/", 1)[-1]:
            filename += ".png"

        try:
            image = self.result_image()

            # JPEG and BMP cannot store transparency: paint the outside white
            if image.ndim == 3 and image.shape[2] == 4 and filename.lower().endswith((".jpg", ".jpeg", ".bmp")):
                alpha = image[..., 3:] / 255.0
                image = (image[..., :3] * alpha + 255 * (1 - alpha)).astype(np.uint8)

            processing.save_image(filename, image)

        except Exception as error:
            QMessageBox.critical(self, "Save Failed", str(error))
            return

        QMessageBox.information(self, "Saved", f"Saved to:\n{filename}")
