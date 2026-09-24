class Calibration:

    def __init__(self):
        self.um_per_pixel = None

    def set_manual(self, known_length_um, pixel_length):
        self.um_per_pixel = (
            known_length_um / pixel_length
        )