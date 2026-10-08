"""
Image processing for the binary image plugin.

Convention used throughout: a pixel is BLACK when its gray value is
strictly below the threshold, otherwise it is WHITE. So:

    threshold = 0    -> everything white
    threshold = 255  -> almost everything black
    higher threshold -> more black
"""

import cv2
import numpy as np


def to_gray(image):
    """Return a single channel uint8 image from a gray, BGR or BGRA image."""

    if image.ndim == 2:
        gray = image
    elif image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if gray.dtype != np.uint8:
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    return gray


def binarize(gray, threshold, invert=False):
    """Return a 0/255 image: black where gray < threshold, white elsewhere."""

    binary = np.where(gray < threshold, 0, 255).astype(np.uint8)

    if invert:
        binary = 255 - binary

    return binary


def otsu_threshold(gray, mask=None):
    """Automatic threshold (Otsu) in this module's convention."""

    pixels = gray if mask is None else gray[mask]

    if pixels.size == 0:
        return 128

    value, _ = cv2.threshold(
        pixels.reshape(-1, 1),
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # OpenCV makes pixels > value white; we make pixels < threshold black.
    return int(min(value + 1, 255))


def threshold_for_black_fraction(gray, fraction, mask=None):
    """Threshold whose result is as close as possible to `fraction` black."""

    pixels = gray if mask is None else gray[mask]

    if pixels.size == 0:
        return 0

    fraction = float(np.clip(fraction, 0.0, 1.0))

    hist = np.bincount(pixels.ravel(), minlength=256)

    # below[t] = number of pixels with value < t, for t = 0..256
    below = np.concatenate(([0], np.cumsum(hist)))
    fractions = below / pixels.size

    best = int(np.argmin(np.abs(fractions - fraction)))

    return min(best, 255)


def black_fraction(binary, mask=None):
    """Fraction (0..1) of black pixels, optionally only inside a mask."""

    pixels = binary if mask is None else binary[mask]

    if pixels.size == 0:
        return 0.0

    return float(np.count_nonzero(pixels == 0)) / pixels.size


def circle_mask(shape, cx, cy, radius):
    """Boolean mask of `shape[:2]` that is True inside the circle."""

    height, width = shape[:2]

    ys, xs = np.ogrid[:height, :width]

    return (xs - cx) ** 2 + (ys - cy) ** 2 <= radius ** 2


def crop_circle(image, cx, cy, radius, transparent=True, fill=255):
    """
    Crop `image` to the square around a circle and blank out the corners.

    Returns a BGRA image (outside of the circle transparent) when
    `transparent` is True, otherwise the original channel layout with
    the outside painted with `fill`.
    """

    height, width = image.shape[:2]

    x0 = max(int(np.floor(cx - radius)), 0)
    y0 = max(int(np.floor(cy - radius)), 0)
    x1 = min(int(np.ceil(cx + radius)) + 1, width)
    y1 = min(int(np.ceil(cy + radius)) + 1, height)

    if x1 <= x0 or y1 <= y0:
        raise ValueError("Circle does not overlap the image.")

    cropped = image[y0:y1, x0:x1].copy()

    mask = circle_mask(cropped.shape, cx - x0, cy - y0, radius)

    if transparent:
        if cropped.ndim == 2:
            cropped = cv2.cvtColor(cropped, cv2.COLOR_GRAY2BGRA)
        elif cropped.shape[2] == 3:
            cropped = cv2.cvtColor(cropped, cv2.COLOR_BGR2BGRA)

        cropped[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
    else:
        cropped[~mask] = fill

    return cropped


def save_image(path, image):
    """Write an image; works with non-ASCII paths (e.g. OneDrive on Windows)."""

    extension = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ".png"

    ok, data = cv2.imencode(extension, image)

    if not ok:
        raise IOError(f"Could not encode image as {extension}")

    data.tofile(path)
