import os
import sys
from typing import List, Tuple, Optional
import cv2
import numpy as np

from .detection import Detection
from .recognition import Recognition
from .classification import Classification
from .utils import sort_polygon, crop_image


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)


class OCRProcessor:
    """
    Main OCR processor class that combines detection, classification and recognition.
    
    This class provides a high-level interface for performing OCR on images using
    PaddleOCR ONNX models.
    
    Example:
        >>> from paddleocr_onnx import OCRProcessor
        >>> ocr = OCRProcessor()
        >>> results = ocr.process_image("path/to/image.jpg")
        >>> print(results)
    """
    
    def __init__(self, 
                 detection_model_path: Optional[str] = None,
                 recognition_model_path: Optional[str] = None,
                 classification_model_path: Optional[str] = None):
        """
        Initialize the OCR processor.
        
        Args:
            detection_model_path: Path to detection ONNX model
            recognition_model_path: Path to recognition ONNX model  
            classification_model_path: Path to classification ONNX model
        """
        # Use default model paths if not provided
        if detection_model_path is None:
            detection_model_path = resource_path('weights/detection.onnx')
        if recognition_model_path is None:
            recognition_model_path = resource_path('weights/recognition.onnx')
        if classification_model_path is None:
            classification_model_path = resource_path('weights/classification.onnx')
            
        # Initialize models
        self.detection = Detection(detection_model_path)
        self.recognition = Recognition(recognition_model_path)
        self.classification = Classification(classification_model_path)
    
    def process_image(self, 
                     image_path: str, 
                     output_path: Optional[str] = None,
                     draw_results: bool = True) -> List[Tuple[str, float]]:
        """
        Process an image and extract text.
        
        Args:
            image_path: Path to input image
            output_path: Path to save output image with annotations
            draw_results: Whether to draw detection boxes and text on image
            
        Returns:
            List of tuples containing (text, confidence) for each detected text region
        """
        # Read image
        frame = cv2.imread(image_path)
        if frame is None:
            raise ValueError(f"Could not read image: {image_path}")
            
        return self.process_frame(frame, output_path, draw_results)
    
    def process_frame(self, 
                     frame: np.ndarray,
                     output_path: Optional[str] = None, 
                     draw_results: bool = True) -> List[Tuple[str, float]]:
        """
        Process a frame/image array and extract text.
        
        Args:
            frame: Input image as numpy array (BGR format)
            output_path: Path to save output image with annotations
            draw_results: Whether to draw detection boxes and text on image
            
        Returns:
            List of tuples containing (text, confidence) for each detected text region
        """
        image = frame.copy()
        
        # Convert BGR to RGB for processing
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect text regions
        points = self.detection(rgb_frame)
        points = sort_polygon(list(points))
        
        if not points:
            return []
        
        # Crop detected regions
        cropped_images = [crop_image(rgb_frame, x) for x in points]
        
        # Classify orientation and rotate if needed
        cropped_images, angles = self.classification(cropped_images)
        
        # Recognize text
        results, confidences = self.recognition(cropped_images)
        
        # Draw results on image if requested
        if draw_results:
            self._draw_results(image, points, results)
        
        # Save output image if path provided
        if output_path:
            cv2.imwrite(output_path, image)
        
        # Return results with confidences
        return list(zip(results, confidences))
    
    def _draw_results(self, image: np.ndarray, points: List, results: List[str]):
        """Draw detection boxes and recognized text on image."""
        for i, result in enumerate(results):
            if i < len(points):
                point = np.array(points[i], dtype=np.int32)
                
                # Draw polygon
                cv2.polylines(image, [point], True, (0, 255, 0), 2)
                
                # Draw text
                x, y, w, h = cv2.boundingRect(point)
                image = cv2.putText(image, result, (int(x), int(y - 2)), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 0), 1, cv2.LINE_AA)
    
    def process_directory(self, 
                         directory_path: str, 
                         output_dir: Optional[str] = None,
                         image_extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')) -> List[Tuple[str, List[Tuple[str, float]]]]:
        """
        Process all images in a directory.
        
        Args:
            directory_path: Path to directory containing images
            output_dir: Directory to save output images (optional)
            image_extensions: Tuple of valid image extensions
            
        Returns:
            List of tuples containing (filename, results) for each processed image
        """
        if not os.path.isdir(directory_path):
            raise ValueError(f"Directory not found: {directory_path}")
        
        # Create output directory if specified
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Get all image files
        image_files = [f for f in os.listdir(directory_path) 
                      if f.lower().endswith(image_extensions)]
        
        all_results = []
        
        for image_file in image_files:
            full_path = os.path.join(directory_path, image_file)
            output_path = None
            
            if output_dir:
                output_filename = f"output_{image_file}"
                output_path = os.path.join(output_dir, output_filename)
            
            try:
                results = self.process_image(full_path, output_path)
                all_results.append((image_file, results))
                print(f"Processed {image_file}: {[r[0] for r in results]}")
            except Exception as e:
                print(f"Error processing {image_file}: {e}")
                all_results.append((image_file, []))
        
        return all_results
