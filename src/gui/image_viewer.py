import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem
)


class ImageViewer(QGraphicsView):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.image_item = None

    def load_image(self, filename):

        self.scene.clear()

        pixmap = QPixmap(filename)

        #
        # Qt can't read some files (e.g. 16-bit TIFF);
        # fall back to OpenCV
        #

        if pixmap.isNull():
            pixmap = self._load_with_opencv(filename)

        if pixmap is None or pixmap.isNull():
            self.image_item = None
            return False

        self.image_item = QGraphicsPixmapItem(pixmap)

        self.scene.addItem(self.image_item)

        self.resetTransform()

        self.fitInView(
            self.scene.itemsBoundingRect(),
            Qt.KeepAspectRatio
        )

        return True

    def _load_with_opencv(self, filename):

        # np.fromfile + imdecode handles non-ASCII paths on Windows
        data = np.fromfile(filename, dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)

        if image is None:
            return None

        rgb = np.ascontiguousarray(
            cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        )

        h, w, ch = rgb.shape

        qimage = QImage(
            rgb.data,
            w,
            h,
            ch * w,
            QImage.Format_RGB888
        )

        return QPixmap.fromImage(qimage.copy())

    def wheelEvent(self, event):

        if self.image_item is None:
            return

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
