from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Tuple
import cv2
import numpy as np
import os
@dataclass
class DetectionConfig:
    """Configuration cho detection"""
    conf_threshold: float = 0.33
    iou_threshold: float = 0.25
    max_size: int = 1280
    min_size: int = 640
    enhance_image: bool = True
    
@dataclass 
class Detection:
    """Standard detection result"""
    class_name: str
    class_id: int
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    
    @property
    def center(self) -> Tuple[int, int]:
        return ((self.bbox[0] + self.bbox[2]) // 2, 
                (self.bbox[1] + self.bbox[3]) // 2)
    
    @property
    def area(self) -> int:
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])

class ImageProcessor:
    """Separate class cho image processing"""
    
    @staticmethod
    def resize_for_yolo(image: np.ndarray, target_size: int = 640) -> Tuple[np.ndarray, float]:
        """Resize image optimally for YOLO"""
        h, w = image.shape[:2]
        scale = min(target_size / w, target_size / h)
        
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Ensure multiples of 32
        new_w = ((new_w + 31) // 32) * 32
        new_h = ((new_h + 31) // 32) * 32
        
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale
    
    @staticmethod
    def enhance_image(image: np.ndarray) -> np.ndarray:
        """Apply enhancement pipeline"""
        # CLAHE
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l_enhanced = clahe.apply(l)
        enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # Bilateral filter + sharpening
        enhanced = cv2.bilateralFilter(enhanced, 9, 75, 75)
        kernel = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        return cv2.addWeighted(enhanced, 0.7, sharpened, 0.3, 0)

class DetectionFilter:
    """Separate class cho filtering strategies"""
    
    @staticmethod
    def calculate_iou(box1: List[int], box2: List[int]) -> float:
        """Calculate IoU between two boxes"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
            
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    @classmethod
    def apply_nms(cls, detections: List[Detection], iou_threshold: float = 0.5) -> List[Detection]:
        """Apply Non-Maximum Suppression"""
        if not detections:
            return []
            
        # Group by class
        class_groups = {}
        for det in detections:
            if det.class_name not in class_groups:
                class_groups[det.class_name] = []
            class_groups[det.class_name].append(det)
        
        final_detections = []
        for class_detections in class_groups.values():
            # Sort by confidence
            class_detections.sort(key=lambda x: x.confidence, reverse=True)
            
            keep = []
            for det in class_detections:
                should_keep = True
                for kept_det in keep:
                    if cls.calculate_iou(det.bbox, kept_det.bbox) > iou_threshold:
                        should_keep = False
                        break
                if should_keep:
                    keep.append(det)
            
            final_detections.extend(keep)
        
        return final_detections
    
    @classmethod
    def best_per_class(cls, detections: List[Detection]) -> List[Detection]:
        """Get best detection per class"""
        best_detections = {}
        for det in detections:
            if (det.class_name not in best_detections or 
                det.confidence > best_detections[det.class_name].confidence):
                best_detections[det.class_name] = det
        
        return list(best_detections.values())

class BaseDetector(ABC):
    """Abstract base class for detectors"""
    
    @abstractmethod
    def detect(self, image: Union[str, np.ndarray]) -> List[Detection]:
        pass

class YOLODetector(BaseDetector):
    """Clean YOLO detector implementation"""
    
    def __init__(self, model_path: str, config: DetectionConfig = None):
        self.config = config or DetectionConfig()
        self.model = self._load_model(model_path)
        self.image_processor = ImageProcessor()
        self.filter = DetectionFilter()
    
    def _load_model(self, model_path: str):
        """Load YOLO model"""
        try:
            from ultralytics import YOLO

            model = YOLO(model_path)
            print(f"✓ Loaded YOLO model: {model_path}")
            return model
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
    
    def detect(self, image: Union[str, np.ndarray], 
               filter_strategy: str = "nms") -> List[Detection]:
        """Main detection method"""
        
        # Load image
        if isinstance(image, str):
            img_array = cv2.imread(image)
            if img_array is None:
                raise ValueError(f"Could not load image: {image}")
        else:
            img_array = image.copy()
        
        original_shape = img_array.shape[:2]
        
        # Process image
        if self.config.enhance_image:
            img_array = self.image_processor.enhance_image(img_array)
        
        processed_img, scale = self.image_processor.resize_for_yolo(
            img_array, self.config.max_size
        )
        
        # Run inference
        results = self.model(
            processed_img,
            conf=self.config.conf_threshold,
            iou=self.config.iou_threshold,
            verbose=False
        )
        
        # Parse results
        detections = self._parse_results(results, scale, original_shape)
        
        # Apply filtering
        if filter_strategy == "nms":
            detections = self.filter.apply_nms(detections, self.config.iou_threshold)
        elif filter_strategy == "best_per_class":
            detections = self.filter.best_per_class(detections)
        elif filter_strategy == "no_duplicates":
            # Advanced filtering để loại bỏ duplicate labels
            detections = self._remove_duplicate_labels(detections)
        elif filter_strategy == "smart":
            # Smart filtering kết hợp nhiều tiêu chí
            detections = self._smart_duplicate_removal(detections)
        
        # Sort by confidence
        detections.sort(key=lambda x: x.confidence, reverse=True)
        
        return detections
    
    def _parse_results(self, results, scale: float, 
                      original_shape: Tuple[int, int]) -> List[Detection]:
        """Parse YOLO results into Detection objects"""
        detections = []
        orig_h, orig_w = original_shape
        
        for result in results:
            if result.boxes is None:
                continue
                
            for box in result.boxes:
                # Extract data
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]
                
                # Scale back to original size
                x1, y1, x2, y2 = int(x1 / scale), int(y1 / scale), int(x2 / scale), int(y2 / scale)
                
                # Clamp to image bounds
                x1 = max(0, min(x1, orig_w))
                y1 = max(0, min(y1, orig_h))
                x2 = max(0, min(x2, orig_w))
                y2 = max(0, min(y2, orig_h))
                
                # Skip tiny boxes
                if (x2 - x1) < 10 or (y2 - y1) < 10:
                    continue
                
                detection = Detection(
                    class_name=class_name,
                    class_id=class_id,
                    confidence=confidence,
                    bbox=[x1, y1, x2, y2]
                )
                detections.append(detection)
        
        return detections

# Usage example:
"""
config = DetectionConfig(conf_threshold=0.4, enhance_image=True)
detector = YOLODetector("yolov8n.pt", config)

detections = detector.detect("image.jpg", filter_strategy="nms")
for det in detections:
    print(f"{det.class_name}: {det.confidence:.2f} at {det.bbox}")
"""
if __name__ == "__main__":
    print("YOLODetector module loaded. Use the class in your application.")
    config = DetectionConfig(conf_threshold=0.2, enhance_image=True)
    detector = YOLODetector(r"C:\WorkSpace\GrpcOCR\service\yolo\OCR_QR_CCCD.pt", config)
    print("Running test detection on sample image...")
    image_dir = r"C:\WorkSpace\GrpcOCR\images"
    for fname in os.listdir(image_dir):
        if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            continue
        img_path = os.path.join(image_dir, fname)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Could not read {img_path}")
            continue
        detections = detector.detect(img, filter_strategy="best_per_class")
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{det.class_name} {det.confidence:.2f}"
            cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        out_path = os.path.join(image_dir, f"result_{fname}")
        cv2.imwrite(out_path, img)
        print(f"Processed {fname}, saved to {out_path}")