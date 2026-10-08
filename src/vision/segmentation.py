import cv2

def segment_cells(image):

    _, thresh = cv2.threshold(
        image,
        0,
        255,
        cv2.THRESH_BINARY +
        cv2.THRESH_OTSU
    )

    return thresh