import cv2
import os
from PySide6.QtWidgets import QLabel

class ImageViewer(QLabel):
    def __init__(self):
        super().__init__()

from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem
)

from PySide6.QtGui import QPixmap

from PySide6.QtCore import Qt


from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem
)

from PySide6.QtGui import QPixmap

from PySide6.QtCore import Qt

class ImageViewer(QGraphicsView):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

    def load_image(self, filename):

        self.scene.clear()

        pixmap = QPixmap(filename)
        self.image_item = QGraphicsPixmapItem(pixmap)

        self.image_item = QGraphicsPixmapItem(pixmap)

        self.scene.addItem(self.image_item)

        self.fitInView(
            self.scene.itemsBoundingRect(),
            Qt.KeepAspectRatio
        )

from PIL import Image
from PySide6.QtGui import QImage, QPixmap

def load_image(self, filename):

    self.scene.clear()

    image = Image.open(filename)
    image = image.convert("RGB")

    width, height = image.size

    qimage = QImage(
        image.tobytes(),
        width,
        height,
        width * 3,
        QImage.Format_RGB888
    )

    pixmap = QPixmap.fromImage(qimage)

    print("Pixmap is null?", pixmap.isNull())

    self.image_item = QGraphicsPixmapItem(pixmap)

    self.scene.addItem(self.image_item)

    self.fitInView(
        self.scene.itemsBoundingRect(),
        Qt.KeepAspectRatio
    )

    def wheelEvent(self, event):

        zoom_factor = 1.15

        if event.angleDelta().y() > 0:

            self.scale(
                zoom_factor,
                zoom_factor
            )

        else:

            self.scale(
                1 / zoom_factor,
                1 / zoom_factor
            )