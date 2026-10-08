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


#
# Two-circle shapes
#

SHAPE_SINGLE = "single"
SHAPE_RING = "ring"            # circle 1 with circle 2 cut out
SHAPE_UNION = "union"          # circle 1 plus circle 2
SHAPE_INTERSECT = "intersect"  # only where circle 1 and circle 2 overlap


def shape_mask(shape, circle1, circle2=None, mode=SHAPE_SINGLE):
    """
    Boolean mask for one circle, or two circles combined with `mode`.

    Circles are (cx, cy, radius) tuples. With a concentric smaller second
    circle, SHAPE_RING gives a ring; off-centre it gives a crescent, and
    SHAPE_INTERSECT gives a lens.
    """

    mask = circle_mask(shape, *circle1)

    if circle2 is None or mode == SHAPE_SINGLE:
        return mask

    second = circle_mask(shape, *circle2)

    if mode == SHAPE_RING:
        return mask & ~second
    if mode == SHAPE_UNION:
        return mask | second
    if mode == SHAPE_INTERSECT:
        return mask & second

    raise ValueError(f"Unknown shape mode: {mode}")


def ring_geometry(circle1, circle2):
    """Width (outer minus inner radius) and centre offset of two circles."""

    (x1, y1, r1), (x2, y2, r2) = circle1, circle2

    return {
        "width": abs(r1 - r2),
        "offset": float(np.hypot(x2 - x1, y2 - y1)),
    }


def crop_circle(image, cx, cy, radius, transparent=True, fill=255):
    """
    Crop `image` to the square around a circle and blank out the corners.

    Returns a BGRA image (outside of the circle transparent) when
    `transparent` is True, otherwise the original channel layout with
    the outside painted with `fill`.
    """

    return crop_to_mask(
        image,
        circle_mask(image.shape, cx, cy, radius),
        transparent,
        fill,
    )


def crop_to_mask(image, mask, transparent=True, fill=255):
    """
    Crop `image` to the bounding box of `mask` and blank out everything
    outside it (transparent, or painted with `fill`).
    """

    ys, xs = np.nonzero(mask)

    if ys.size == 0:
        raise ValueError("The selected shape does not overlap the image.")

    y0, y1 = ys.min(), ys.max() + 1
    x0, x1 = xs.min(), xs.max() + 1

    cropped = image[y0:y1, x0:x1].copy()
    mask = mask[y0:y1, x0:x1]

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
