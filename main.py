import os
from argparse import ArgumentParser
from warnings import filterwarnings
import sys

import cv2
import numpy

from nets import nn
from utils import util

filterwarnings("ignore")


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


detection = nn.Detection(resource_path('weights/detection.onnx'))
recognition = nn.Recognition(resource_path('weights/recognition.onnx'))
classification = nn.Classification(resource_path('weights/classification.onnx'))


def main():
    # parser = ArgumentParser()
    # parser.add_argument('filepath', type=str, help='image file path')

    # args = parser.parse_args()

    frame = cv2.imread(r"C:\WorkSpace\2_AI\OCR\Padlet\PaddleOCR-onnx\New folder\z6848230672895_ffa1a25eea1f3fb97c78bd083c74869e.jpg")
    image = frame.copy()

    cv2.cvtColor(frame, cv2.COLOR_BGR2RGB, frame)  # inplace

    points = detection(frame)
    points = util.sort_polygon(list(points))

    # draw detected polygon
    for point in points:
        point = numpy.array(point, dtype=numpy.int32)
        cv2.polylines(image,
                      [point], True,
                      (0, 255, 0), 2)

    cropped_images = [util.crop_image(frame, x) for x in points]
    cropped_images, angles = classification(cropped_images)
    results, confidences = recognition(cropped_images)

    # draw recognized text
    for i, result in enumerate(results):
        point = points[i]
        x, y, w, h = cv2.boundingRect(point)
        image = cv2.putText(image, result, (int(x), int(y - 2)), cv2.FONT_HERSHEY_SIMPLEX,
                            0.4, (200, 200, 0), 1, cv2.LINE_AA)
  
    print(results)


if __name__ == '__main__':
    main()
