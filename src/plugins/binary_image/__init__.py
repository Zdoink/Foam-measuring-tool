"""
Binary image plugin.

Converts a picture to black and white, lets the user control how much
of the image is black vs. white, and crops the image to a circle, or to
a ring or other shape made from two circles.
"""

from .processing import (
    to_gray,
    binarize,
    otsu_threshold,
    threshold_for_black_fraction,
    black_fraction,
    circle_mask,
    crop_circle,
    crop_to_mask,
    shape_mask,
    ring_geometry,
    SHAPE_SINGLE,
    SHAPE_RING,
    SHAPE_UNION,
    SHAPE_INTERSECT,
)


def open_dialog(image, parent=None):
    """Open the interactive binary / circle crop dialog for a BGR image."""

    from .dialog import BinaryImageDialog

    dialog = BinaryImageDialog(image, parent)
    dialog.exec()
    return dialog
