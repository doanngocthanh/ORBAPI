"""
PaddleOCR ONNX SDK

A Python SDK for text detection, classification and recognition using PaddleOCR ONNX models.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .ocr import OCRProcessor
from .detection import Detection
from .recognition import Recognition
from .classification import Classification

__all__ = [
    "OCRProcessor",
    "Detection", 
    "Recognition",
    "Classification",
]
