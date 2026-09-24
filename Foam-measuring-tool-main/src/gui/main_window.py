import sys

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout
)

class MainWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Foam Measure"
        )

        layout = QVBoxLayout()

        button = QPushButton(
            "Load Image"
        )

        layout.addWidget(button)

        self.setLayout(layout)

def start_app():

    app = QApplication(sys.argv)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())