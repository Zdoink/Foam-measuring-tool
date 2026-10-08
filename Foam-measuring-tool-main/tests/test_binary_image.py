import numpy as np
import pytest

from src.plugins.binary_image import processing


def gradient():
    # 16 x 16 image containing every gray value 0..255 exactly once
    return np.arange(256, dtype=np.uint8).reshape(16, 16)


def test_binarize_threshold_controls_black_amount():
    gray = gradient()

    assert processing.black_fraction(processing.binarize(gray, 0)) == 0.0
    assert processing.black_fraction(processing.binarize(gray, 128)) == 0.5
    assert processing.black_fraction(processing.binarize(gray, 255)) == pytest.approx(255 / 256)


def test_invert_swaps_black_and_white():
    gray = gradient()
    binary = processing.binarize(gray, 64, invert=True)

    assert processing.black_fraction(binary) == 0.75


def test_threshold_for_black_fraction():
    gray = gradient()

    for target in (0.0, 0.1, 0.25, 0.5, 0.9):
        t = processing.threshold_for_black_fraction(gray, target)
        actual = processing.black_fraction(processing.binarize(gray, t))
        assert actual == pytest.approx(target, abs=1 / 256)


def test_otsu_splits_two_levels():
    gray = np.zeros((10, 10), np.uint8)
    gray[:, 5:] = 200

    t = processing.otsu_threshold(gray)

    assert processing.black_fraction(processing.binarize(gray, t)) == 0.5


def test_circle_mask_and_crop():
    image = np.full((100, 100, 3), 50, np.uint8)

    mask = processing.circle_mask(image.shape, 50, 50, 20)
    assert mask[50, 50] and not mask[0, 0]
    assert mask.sum() == pytest.approx(np.pi * 20 ** 2, rel=0.05)

    cropped = processing.crop_circle(image, 50, 50, 20)
    assert cropped.shape == (41, 41, 4)
    assert cropped[20, 20, 3] == 255  # centre opaque
    assert cropped[0, 0, 3] == 0      # corner transparent

    filled = processing.crop_circle(image, 50, 50, 20, transparent=False)
    assert filled.shape == (41, 41, 3)
    assert (filled[0, 0] == 255).all()
    assert (filled[20, 20] == 50).all()


def test_crop_circle_outside_image_raises():
    with pytest.raises(ValueError):
        processing.crop_circle(np.zeros((10, 10), np.uint8), 100, 100, 5)


def test_save_image_roundtrip(tmp_path):
    import cv2

    path = tmp_path / "out.png"
    image = processing.crop_circle(np.zeros((20, 20), np.uint8), 10, 10, 8)
    processing.save_image(str(path), image)

    loaded = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert loaded.shape == image.shape
