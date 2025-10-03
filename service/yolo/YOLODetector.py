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
    max_positions_per_label: int = 2  # Số vị trí tốt nhất cho mỗi label
    target_size: int = 640
    enhance_image: bool = False
    
@dataclass 
class Detection:
    """Standard detection result"""
    class_name: str
    class_id: int
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    position_rank: int = 0  # Thứ hạng vị trí (0=tốt nhất, 1=tốt thứ 2,...)
    
    @property
    def center(self) -> Tuple[int, int]:
        return ((self.bbox[0] + self.bbox[2]) // 2, 
                (self.bbox[1] + self.bbox[3]) // 2)
    
    @property
    def area(self) -> int:
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])
    
    def __repr__(self) -> str:
        return f"Detection({self.class_name}, conf={self.confidence:.3f}, pos={self.position_rank}, bbox={self.bbox})"

class ImageProcessor:
    """Class xử lý ảnh"""
    
    @staticmethod
    def smart_resize(image: np.ndarray, target_size: int = 640) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Resize thông minh: giữ tỷ lệ và pad nếu cần
        Returns: (resized_image, scale_factor, (pad_w, pad_h))
        """
        h, w = image.shape[:2]
        
        # Tính scale để fit vào target_size
        scale = min(target_size / w, target_size / h)
        
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Resize
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Tạo canvas và center image
        canvas = np.zeros((target_size, target_size, 3), dtype=np.uint8)
        pad_w = (target_size - new_w) // 2
        pad_h = (target_size - new_h) // 2
        
        canvas[pad_h:pad_h+new_h, pad_w:pad_w+new_w] = resized
        
        return canvas, scale, (pad_w, pad_h)
    
    @staticmethod
    def enhance_image(image: np.ndarray) -> np.ndarray:
        """Apply enhancement pipeline"""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l_enhanced = clahe.apply(l)
        enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        return enhanced

class DetectionFilter:
    """Class lọc và xử lý detections"""
    
    @staticmethod
    def calculate_iou(box1: List[int], box2: List[int]) -> float:
        """Tính IoU giữa 2 boxes"""
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
    def filter_multi_position(cls, detections: List[Detection], 
                             max_per_label: int = 2,
                             iou_threshold: float = 0.5) -> List[Detection]:
        """
        Lọc để lấy nhiều vị trí tốt nhất cho mỗi label
        
        Args:
            detections: Danh sách detections
            max_per_label: Số vị trí tối đa cho mỗi label
            iou_threshold: Ngưỡng IoU để coi là trùng vị trí
        
        Returns:
            Danh sách detections đã lọc với position_rank
        """
        if not detections:
            return []
        
        # Nhóm theo class_name
        class_groups = {}
        for det in detections:
            if det.class_name not in class_groups:
                class_groups[det.class_name] = []
            class_groups[det.class_name].append(det)
        
        final_detections = []
        
        for class_name, class_dets in class_groups.items():
            # Sắp xếp theo confidence giảm dần
            class_dets.sort(key=lambda x: x.confidence, reverse=True)
            
            selected = []
            for det in class_dets:
                # Kiểm tra xem detection này có trùng với các detection đã chọn không
                is_duplicate = False
                for sel_det in selected:
                    iou = cls.calculate_iou(det.bbox, sel_det.bbox)
                    if iou > iou_threshold:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    # Gán position rank
                    det.position_rank = len(selected)
                    selected.append(det)
                    
                    # Dừng khi đủ số lượng
                    if len(selected) >= max_per_label:
                        break
            
            final_detections.extend(selected)
        
        return final_detections
    
    @classmethod
    def no_filter(cls, detections: List[Detection]) -> List[Detection]:
        """Không lọc, trả về tất cả"""
        return detections

class YOLODetector(ABC):
    """YOLO Detector với hỗ trợ multi-position detection"""
    
    def __init__(self, model_path: str, config: DetectionConfig = None):
        self.config = config or DetectionConfig()
        self.model = self._load_model(model_path)
        self.image_processor = ImageProcessor()
        self.filter = DetectionFilter()
        print(f"✓ Initialized YOLODetector")
        print(f"  - Config: conf={self.config.conf_threshold}, max_pos={self.config.max_positions_per_label}")
    
    def _load_model(self, model_path: str):
        """Load YOLO model"""
        try:
            from ultralytics import YOLO
            model = YOLO(model_path)
            print(f"✓ Loaded model: {model_path}")
            print(f"  - Classes: {list(model.names.values())}")
            return model
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
    
    def count_detections_by_class(self, detections: List[Detection]) -> Dict[str, int]:
        """
        Đếm số lượng detection theo từng class
        
        Args:
            detections: List of Detection objects
            
        Returns:
            Dictionary với key là class_name và value là số lượng
        """
        class_counts = {}
        for det in detections:
            class_name = det.class_name
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        return class_counts
    def get_model_classes(self) -> Dict[int, str]:
        """
        Lấy danh sách classes từ model đã được train
        
        Returns:
            Dictionary với key là class_id và value là class_name
        """
        return self.model.names
    
    def get_total_classes(self) -> int:
        """
        Lấy tổng số classes trong model
        
        Returns:
            Số lượng classes
        """
        return len(self.model.names)
    
    def get_class_names(self) -> List[str]:
        """
        Lấy danh sách tên các classes
        
        Returns:
            List các class names
        """
        return list(self.model.names.values())
    
    def detect(self, image: Union[str, np.ndarray], 
               filter_mode: int = 0) -> List[Detection]:
        """
        Phát hiện objects trong ảnh
        
        Args:
            image: Đường dẫn ảnh hoặc numpy array
            filter_mode: 
                0 = No filter (tất cả detections)
                1 = Multi-position filter (lấy top N vị trí cho mỗi label)
        
        Returns:
            List of Detection objects
        """
        # Load ảnh
        if isinstance(image, str):
            img_array = cv2.imread(image)
            if img_array is None:
                raise ValueError(f"Could not load image: {image}")
        else:
            img_array = image.copy()
        
        original_h, original_w = img_array.shape[:2]
        
        # Enhance nếu cần
        if self.config.enhance_image:
            img_array = self.image_processor.enhance_image(img_array)
        
        # Resize ảnh
        processed_img, scale, (pad_w, pad_h) = self.image_processor.smart_resize(
            img_array, self.config.target_size
        )
        
        # Run inference
        results = self.model.predict(
            processed_img,
            conf=self.config.conf_threshold,
            iou=self.config.iou_threshold,
            verbose=False
        )
        
        # Parse results
        detections = self._parse_results(
            results, scale, (pad_w, pad_h), (original_h, original_w)
        )
        
        # Apply filter dựa theo filter_mode
        if filter_mode == 0:
            # No filter
            filtered_detections = self.filter.no_filter(detections)
        elif filter_mode == 1:
            # Multi-position filter
            filtered_detections = self.filter.filter_multi_position(
                detections,
                max_per_label=self.config.max_positions_per_label,
                iou_threshold=self.config.iou_threshold
            )
        else:
            raise ValueError(f"Invalid filter_mode: {filter_mode}. Use 0 or 1.")
        
        # Sort: theo class_name, sau đó theo position_rank
        filtered_detections.sort(key=lambda x: (x.class_name, x.position_rank))
        
        return filtered_detections
    
    def _parse_results(self, results, scale: float, padding: Tuple[int, int],
                      original_shape: Tuple[int, int]) -> List[Detection]:
        """Parse YOLO results thành Detection objects"""
        detections = []
        orig_h, orig_w = original_shape
        pad_w, pad_h = padding
        
        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue
                
            for box in result.boxes:
                # Extract data
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]
                
                # Convert về tọa độ ảnh gốc
                # Bước 1: Bỏ padding
                x1 = x1 - pad_w
                y1 = y1 - pad_h
                x2 = x2 - pad_w
                y2 = y2 - pad_h
                
                # Bước 2: Scale về kích thước gốc
                x1 = int(x1 / scale)
                y1 = int(y1 / scale)
                x2 = int(x2 / scale)
                y2 = int(y2 / scale)
                
                # Clamp về bounds ảnh gốc
                x1 = max(0, min(x1, orig_w))
                y1 = max(0, min(y1, orig_h))
                x2 = max(0, min(x2, orig_w))
                y2 = max(0, min(y2, orig_h))
                
                # Skip boxes quá nhỏ
                if (x2 - x1) < 5 or (y2 - y1) < 5:
                    continue
                
                detection = Detection(
                    class_name=class_name,
                    class_id=class_id,
                    confidence=confidence,
                    bbox=[x1, y1, x2, y2]
                )
                detections.append(detection)
        
        return detections
    
    def visualize(self, image: Union[str, np.ndarray], 
                  detections: List[Detection],
                  output_path: Optional[str] = None) -> np.ndarray:
        """Vẽ kết quả detection lên ảnh"""
        # Load ảnh
        if isinstance(image, str):
            img = cv2.imread(image)
        else:
            img = image.copy()
        
        # Màu cho từng position
        colors = [
            (0, 255, 0),    # Green - Position 0
            (255, 165, 0),  # Orange - Position 1
            (0, 165, 255),  # Light Blue - Position 2
        ]
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = colors[det.position_rank % len(colors)]
            
            # Draw box
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{det.class_name}"
            if det.position_rank > 0:
                label += f" #{det.position_rank+1}"
            label += f" {det.confidence:.2f}"
            
            # Background cho text
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(img, (x1, y1 - text_h - 10), (x1 + text_w, y1), color, -1)
            cv2.putText(img, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        if output_path:
            cv2.imwrite(output_path, img)
            print(f"✓ Saved visualization to: {output_path}")
        
        return img


# === USAGE EXAMPLE ===
if __name__ == "__main__":
    # Cấu hình
    config = DetectionConfig(
        conf_threshold=0.25,
        iou_threshold=0.3,
        max_positions_per_label=2,  # Lấy 2 vị trí tốt nhất cho mỗi label
        target_size=640,
        enhance_image=False
    )
    
    # Khởi tạo detector
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from config import PtConfig
    pt_config = PtConfig()
    model_path =r"C:\Workspace\ORBAPI\models\pt\CCCD_FACE_DETECT_2025_NEW_TITLE.pt"
    detector = YOLODetector(model_path, config)
    
    # Test trên thư mục ảnh
    image_dir = r"C:\Workspace\ORBAPI\images"

    for fname in os.listdir(image_dir):
        if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            continue
        img_path = os.path.join(image_dir, fname)
        detections = detector.detect(img_path, filter_mode=1)
        
        # Đếm số lượng từng class
        class_counts = detector.count_detections_by_class(detections)
        
        print(f"\nProcessing: {fname}")
        print(f"Found {len(detections)} detections:")
        print(f"Class counts: {class_counts}")
        for det in detections:
            print(f"  {det}")
        # print(f"\n{'='*60}")
        # print(f"Processing: {fname}")
        # print(f"{'='*60}")
        
        # # Detect với filter_mode=1 (multi-position)
        # detections = detector.detect(img_path, filter_mode=1)
        # print("số lable defafual của model:", len(detector.model.names))
        # if len(detector.model.names) > len(detector.model.names) - 3:
        #     print("Có thể model chưa load đúng, vui lòng kiểm tra lại!")
        #     from ORBImageAligner import ORBImageAligner
        #     aligner = ORBImageAligner(target_dimension=800, orb_features=2000)
        #     template_img = r"C:\Users\0100644068\Downloads\download_grayscale.jpg"
        #     target_img = img_path
        #     result = aligner.align(template_img, target_img)
        #     # Extract aligned image from result dict
        #     aligned_img = result['aligned'] if isinstance(result, dict) and 'aligned' in result else result
        #     # Detect lại trên ảnh đã align
        #     detections = detector.detect(aligned_img, filter_mode=1)
        #     result_dir = os.path.join(image_dir, "test")
        #     os.makedirs(result_dir, exist_ok=True)
        #     output_path = os.path.join(result_dir, f"result_{fname}")
        #     detector.visualize(aligned_img, detections, output_path)
            
        #     continue
        # print(f"\nFound {len(detections)} detections:")
        # for det in detections:
        #     print(f"  {det}")
        
        # # Visualize
        # # Tạo thư mục nếu chưa có
        # result_dir = os.path.join(image_dir, "test")
        # os.makedirs(result_dir, exist_ok=True)
        # output_path = os.path.join(result_dir, f"result_{fname}")
        # detector.visualize(img_path, detections, output_path)
    
    print("\n✓ Processing complete!")