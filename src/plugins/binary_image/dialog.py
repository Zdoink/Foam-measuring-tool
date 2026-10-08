"""
Qt dialog for the binary image plugin.

- Threshold slider controls how much of the picture is black vs. white
- "Target black %" picks the threshold that gives a requested amount of black
- Circle crop: drag on the image to draw a circle, drag inside it to move
  it, scroll the mouse wheel to resize it
- Optional second circle, combined with the first as a ring (cut out),
  an added circle, or the overlap only
"""

import math

import cv2
import numpy as np

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QImage, QPainter, QPainterPath, QPen, QColor

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import processing


PREVIEW_MAX_DIMENSION = 1000

CIRCLE_COLORS = (QColor(255, 60, 60), QColor(0, 200, 255))

SHAPE_MODES = (
    ("Ring: cut circle 2 out of circle 1", processing.SHAPE_RING),
    ("Add circle 2 to circle 1", processing.SHAPE_UNION),
    ("Overlap of both circles only", processing.SHAPE_INTERSECT),
)


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
    """
    Shows an image and lets the user draw / move / resize up to two
    circles on it. Mouse actions apply to the active circle.
    """

    circleChanged = Signal()

    def __init__(self, image_size, parent=None):
        super().__init__(parent)

        # Full resolution image size (width, height); circles are kept in
        # full resolution coordinates so saving is exact.
        self.image_width, self.image_height = image_size

        self.qimage = None
        self.circle_enabled = False

        # circles[0] is circle 1, circles[1] is circle 2;
        # each is (cx, cy, radius) in image pixels, or None
        self.circles = [None, None]
        self.second_enabled = False
        self.mode = processing.SHAPE_RING
        self.active = 0

        self._drag_mode = None
        self._drag_start = None
        self._circle_start = None

        self.setMinimumSize(500, 400)
        self.setMouseTracking(True)

    #
    # Public API
    #

    @property
    def circle(self):
        """Circle 1 (kept for code that only uses one circle)."""
        return self.circles[0]

    @circle.setter
    def circle(self, value):
        self.circles[0] = value

    @property
    def active_circle(self):
        return self.circles[self.active]

    def set_image(self, qimage):
        self.qimage = qimage
        self.update()

    def set_circle_enabled(self, enabled):
        self.circle_enabled = enabled

        if enabled and self.circles[0] is None:
            self.reset_circle(0)

        self.update()

    def set_second_enabled(self, enabled):
        self.second_enabled = enabled

        if enabled and self.circles[1] is None:
            self.reset_circle(1)

        if not enabled:
            self.active = 0

        self.update()
        self.circleChanged.emit()

    def set_mode(self, mode):
        self.mode = mode
        self.update()
        self.circleChanged.emit()

    def set_active(self, index):
        self.active = index if self.second_enabled else 0
        self.update()
        self.circleChanged.emit()

    def reset_circle(self, index=None):
        index = self.active if index is None else index

        radius = min(self.image_width, self.image_height) / 2

        if index == 1:
            # Start the second circle concentric and half the size of
            # circle 1, i.e. a ring
            if self.circles[0] is not None:
                cx, cy, r = self.circles[0]
                self.circles[1] = (cx, cy, r / 2)
            else:
                self.circles[1] = (self.image_width / 2, self.image_height / 2, radius / 2)
        else:
            self.circles[0] = (self.image_width / 2, self.image_height / 2, radius)

        self.update()
        self.circleChanged.emit()

    def center_second_on_first(self):
        if self.circles[0] is None or self.circles[1] is None:
            return

        cx, cy, _ = self.circles[0]
        self.circles[1] = (cx, cy, self.circles[1][2])
        self.update()
        self.circleChanged.emit()

    def set_radius(self, radius):
        if self.active_circle is None:
            return

        cx, cy, _ = self.active_circle
        self.circles[self.active] = (cx, cy, max(1.0, radius))
        self.update()
        self.circleChanged.emit()

    def shape(self):
        """(circle1, circle2 or None, mode) describing the selected region."""

        if self.second_enabled and self.circles[1] is not None:
            return self.circles[0], self.circles[1], self.mode

        return self.circles[0], None, processing.SHAPE_SINGLE

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

    def _circle_path(self, circle):
        rect = self._image_rect()
        scale = self._scale()

        cx, cy, radius = circle
        center = QPointF(rect.x() + cx * scale, rect.y() + cy * scale)

        path = QPainterPath()
        path.addEllipse(center, radius * scale, radius * scale)

        return path

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

        if not (self.circle_enabled and self.circles[0]):
            return

        circle1, circle2, mode = self.shape()

        region = self._circle_path(circle1)

        if circle2 is not None:
            second = self._circle_path(circle2)

            if mode == processing.SHAPE_RING:
                region = region.subtracted(second)
            elif mode == processing.SHAPE_UNION:
                region = region.united(second)
            elif mode == processing.SHAPE_INTERSECT:
                region = region.intersected(second)

        # Dim everything outside the selected region
        outside = QPainterPath()
        outside.addRect(rect)

        painter.fillPath(outside.subtracted(region), QColor(0, 0, 0, 150))

        # Outline the circles; the active one is drawn thicker
        painter.setBrush(Qt.NoBrush)

        for index, circle in enumerate((circle1, circle2)):
            if circle is None:
                continue

            width = 3 if index == self.active and circle2 is not None else 2
            painter.setPen(QPen(CIRCLE_COLORS[index], width))
            painter.drawPath(self._circle_path(circle))

    #
    # Mouse interaction (applies to the active circle)
    #

    def mousePressEvent(self, event):
        if not self.circle_enabled or event.button() != Qt.LeftButton:
            return

        x, y = self._to_image(event.position())

        self._drag_start = (x, y)
        self._circle_start = self.active_circle

        circle = self.active_circle

        if circle and math.hypot(x - circle[0], y - circle[1]) <= circle[2]:
            self._drag_mode = "move"
        else:
            self._drag_mode = "draw"
            self.circles[self.active] = (x, y, 1.0)
            self.update()

    def mouseMoveEvent(self, event):
        if self._drag_mode is None:
            return

        x, y = self._to_image(event.position())
        sx, sy = self._drag_start

        if self._drag_mode == "move":
            cx, cy, radius = self._circle_start
            self.circles[self.active] = (cx + x - sx, cy + y - sy, radius)
        else:
            self.circles[self.active] = (sx, sy, max(1.0, math.hypot(x - sx, y - sy)))

        self.update()
        self.circleChanged.emit()

    def mouseReleaseEvent(self, event):
        if self._drag_mode is not None:
            self._drag_mode = None
            self.circleChanged.emit()

    def wheelEvent(self, event):
        if not (self.circle_enabled and self.active_circle):
            return

        factor = 1.05 if event.angleDelta().y() > 0 else 1 / 1.05
        self.set_radius(self.active_circle[2] * factor)


class BinaryImageDialog(QDialog):
    """Convert an image to black/white and optionally crop it to a circle shape."""

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

        #
        # Second circle
        #

        self.second_check = QCheckBox("Add a second circle (rings / complex shapes)")
        crop_layout.addWidget(self.second_check)

        self.mode_combo = QComboBox()
        for label, mode in SHAPE_MODES:
            self.mode_combo.addItem(label, mode)
        crop_layout.addWidget(self.mode_combo)

        edit_row = QHBoxLayout()
        edit_row.addWidget(QLabel("Edit:"))

        self.edit_first_radio = QRadioButton("Circle 1 (red)")
        self.edit_second_radio = QRadioButton("Circle 2 (blue)")
        self.edit_first_radio.setChecked(True)

        self.edit_group = QButtonGroup(self)
        self.edit_group.addButton(self.edit_first_radio, 0)
        self.edit_group.addButton(self.edit_second_radio, 1)

        edit_row.addWidget(self.edit_first_radio)
        edit_row.addWidget(self.edit_second_radio)
        crop_layout.addLayout(edit_row)

        self.center_button = QPushButton("Center Circle 2 on Circle 1")
        crop_layout.addWidget(self.center_button)

        #
        # Size of the active circle
        #

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

        self.shape_label = QLabel()
        self.shape_label.setWordWrap(True)
        crop_layout.addWidget(self.shape_label)

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
        self.second_check.toggled.connect(self.toggle_second)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.edit_group.idClicked.connect(self.canvas.set_active)
        self.center_button.clicked.connect(self.canvas.center_second_on_first)

        self.canvas.circleChanged.connect(self.on_circle_changed)
        self.radius_spin.valueChanged.connect(self.on_radius_spin)
        self.reset_circle_button.clicked.connect(lambda: self.canvas.reset_circle())

        self.save_button.clicked.connect(self.save)
        self.close_button.clicked.connect(self.accept)

    def set_crop_controls_enabled(self, enabled):
        self.radius_spin.setEnabled(enabled)
        self.reset_circle_button.setEnabled(enabled)
        self.transparent_check.setEnabled(enabled)
        self.second_check.setEnabled(enabled)

        second = enabled and self.second_check.isChecked()

        self.mode_combo.setEnabled(second)
        self.edit_first_radio.setEnabled(second)
        self.edit_second_radio.setEnabled(second)
        self.center_button.setEnabled(second)

    #
    # State helpers
    #

    def threshold(self):
        return self.threshold_slider.value()

    def crop_enabled(self):
        return self.crop_check.isChecked() and self.canvas.circle is not None

    def two_circles(self):
        return self.crop_enabled() and self.canvas.shape()[1] is not None

    def region_mask(self, shape, scale=1.0):
        """Mask of the selected circle shape at the given resolution, or None."""

        if not self.crop_enabled():
            return None

        circle1, circle2, mode = self.canvas.shape()

        def scaled(circle):
            if circle is None:
                return None
            cx, cy, radius = circle
            return (cx * scale, cy * scale, radius * scale)

        return processing.shape_mask(shape, scaled(circle1), scaled(circle2), mode)

    def preview_mask(self):
        """Region mask at preview resolution, or None when not cropping."""

        return self.region_mask(self.preview_gray.shape, self.preview_scale)

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

        mask = self.preview_mask()

        black = processing.black_fraction(binary, mask) * 100

        if self.two_circles():
            where = " (inside shape)"
        elif self.crop_enabled():
            where = " (inside circle)"
        else:
            where = ""

        self.amount_label.setText(
            f"Black: {black:.1f} %   White: {100 - black:.1f} %{where}"
        )

        self.update_shape_label(mask)

    def update_shape_label(self, preview_mask):
        if preview_mask is None:
            self.shape_label.setText("")
            return

        # Area in full resolution pixels, estimated from the preview mask
        area = np.count_nonzero(preview_mask) / (self.preview_scale ** 2)

        lines = [f"Area: {area:,.0f} px²"]

        circle1, circle2, mode = self.canvas.shape()

        if circle2 is not None:
            geometry = processing.ring_geometry(circle1, circle2)

            if mode == processing.SHAPE_RING:
                lines.append(f"Ring width: {geometry['width']:.1f} px")

            lines.append(f"Center offset: {geometry['offset']:.1f} px")

        self.shape_label.setText("\n".join(lines))

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

    def toggle_second(self, enabled):
        if not enabled:
            self.edit_first_radio.setChecked(True)

        self.canvas.set_second_enabled(enabled)
        self.set_crop_controls_enabled(self.crop_check.isChecked())

        if enabled:
            # Jump straight to editing the new circle
            self.edit_second_radio.setChecked(True)
            self.canvas.set_active(1)

    def on_mode_changed(self, index):
        self.canvas.set_mode(self.mode_combo.itemData(index))

    def on_circle_changed(self):
        circle = self.canvas.active_circle

        if circle is not None:
            self.radius_spin.blockSignals(True)
            self.radius_spin.setValue(round(circle[2]))
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
            image = processing.crop_to_mask(
                image,
                self.region_mask(image.shape),
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
