import matplotlib.pyplot as plt
import numpy as np
import cv2
from PIL import Image

from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
import os

class VietOCRProcessor:
    """
    Processor cho VietOCR tương tự PaddletApi.py
    Cung cấp các phương thức process_bbox, process_multiple_bboxes, process_full_image
    """
    def __init__(self, config=None):
        if config is None:
            # Sử dụng proxy nếu cần
            os.environ['http_proxy'] = 'http://thanhdn2:thanhdn2!@116.118.47.171:3128'
            os.environ['https_proxy'] = 'http://thanhdn2:thanhdn2!@116.118.47.171:3128'
            
            config = Cfg.load_config_from_name('vgg_transformer')
            config['cnn']['pretrained'] = False
            config['device'] = 'cpu'
        
        self.predictor = Predictor(config)
        print("✓ VietOCRProcessor initialized successfully!")
    
    def process_bbox(
        self, 
        image, 
        bbox, 
        bbox_format: str = "xyxy"
    ):
        """
        Xử lý một bbox cụ thể trong ảnh và trả về text
        
        Args:
            image: Đường dẫn ảnh hoặc PIL Image hoặc numpy array
            bbox: Bbox coordinates
            bbox_format: Format của bbox ("xyxy", "polygon", "yolo")
            
        Returns:
            Dict chứa:
            - 'text': Text đã nhận dạng
            - 'confidence': Độ tin cậy (luôn 1.0 với VietOCR)
            - 'bbox': Bbox đã normalize thành polygon format
        """
        # Load image if path is provided
        if isinstance(image, str):
            image_pil = Image.open(image)
            img_width, img_height = image_pil.size
        elif isinstance(image, np.ndarray):
            # Convert numpy array to PIL
            if len(image.shape) == 3:
                if image.shape[2] == 3:  # BGR
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                else:  # RGB
                    image_rgb = image
            else:
                image_rgb = image
            
            image_pil = Image.fromarray(image_rgb.astype('uint8'))
            img_width, img_height = image_pil.size
        else:
            image_pil = image
            img_width, img_height = image_pil.size
        
        # Auto-detect bbox format when caller passes a polygon but leaves default
        # (many detectors return polygon points; callers sometimes forget to set bbox_format)
        try:
            bf = bbox_format.lower() if isinstance(bbox_format, str) else ""
        except Exception:
            bf = ""

        # If bbox looks like a polygon (list/tuple of 4 points), treat as polygon
        if bf == "xyxy" and isinstance(bbox, (list, tuple)) and len(bbox) == 4 and isinstance(bbox[0], (list, tuple)):
            bbox_format = "polygon"

        # Normalize bbox to polygon format
        polygon_bbox = self._normalize_bbox(bbox, bbox_format, img_width, img_height)
        
        # Convert polygon to rectangle for cropping
        xs = [point[0] for point in polygon_bbox]
        ys = [point[1] for point in polygon_bbox]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        
        # Ensure coordinates are within image bounds
        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(img_width, int(x2))
        y2 = min(img_height, int(y2))
        
        # Crop image
        try:
            cropped_image = image_pil.crop((x1, y1, x2, y2))
            
            # Recognize text
            text = self.predictor.predict(cropped_image)
            
            return {
                'text': text if text else "",
                'confidence': 1.0,  # VietOCR không trả confidence
                'bbox': polygon_bbox
            }
        
        except Exception as e:
            print(f"Error processing bbox: {e}")
            return {
                'text': "",
                'confidence': 0.0,
                'bbox': polygon_bbox
            }
    
    def _normalize_bbox(self, bbox, bbox_format, img_width, img_height):
        """
        Normalize bbox về polygon format [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        """
        if bbox_format.lower() == "polygon":
            return bbox
        
        elif bbox_format.lower() == "xyxy":
            x1, y1, x2, y2 = bbox
            return [
                [x1, y1],  # top-left
                [x2, y1],  # top-right
                [x2, y2],  # bottom-right
                [x1, y2]   # bottom-left
            ]
        
        elif bbox_format.lower() == "yolo":
            x_center, y_center, width, height = bbox
            
            # Convert normalized to absolute coordinates
            x_center *= img_width
            y_center *= img_height
            width *= img_width
            height *= img_height
            
            # Calculate corners
            x1 = x_center - width / 2
            y1 = y_center - height / 2
            x2 = x_center + width / 2
            y2 = y_center + height / 2
            
            return [
                [x1, y1],  # top-left
                [x2, y1],  # top-right
                [x2, y2],  # bottom-right
                [x1, y2]   # bottom-left
            ]
        
        else:
            raise ValueError(f"Unsupported bbox_format: {bbox_format}")
    
    def process_multiple_bboxes(
        self, 
        image, 
        bboxes, 
        bbox_format: str = "xyxy"
    ):
        """
        Xử lý nhiều bboxes cùng lúc
        
        Args:
            image: Đường dẫn ảnh hoặc PIL Image hoặc numpy array
            bboxes: List các bbox
            bbox_format: Format của bbox
            
        Returns:
            List of dict, mỗi dict chứa kết quả cho một bbox
        """
        results = []
        
        for i, bbox in enumerate(bboxes):
            try:
                result = self.process_bbox(image, bbox, bbox_format)
                result['bbox_index'] = i
                results.append(result)
            except Exception as e:
                print(f"Error processing bbox {i}: {e}")
                results.append({
                    'text': "",
                    'confidence': 0.0,
                    'bbox': bbox,
                    'bbox_index': i
                })
        
        return results
    
    def process_full_image(self, image):
        """
        Xử lý toàn bộ ảnh (chỉ recognition, không có detection)
        
        Args:
            image: Đường dẫn ảnh hoặc PIL Image hoặc numpy array
            
        Returns:
            Dict chứa:
            - 'texts': List text (chỉ 1 text cho toàn ảnh)
            - 'confidences': List confidence
            - 'bboxes': List bbox (empty vì không có detection)
            - 'count': Số text được tìm thấy
        """
        # Load image if path is provided
        if isinstance(image, str):
            image_pil = Image.open(image)
        elif isinstance(image, np.ndarray):
            if len(image.shape) == 3:
                if image.shape[2] == 3:  # BGR
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                else:  # RGB
                    image_rgb = image
            else:
                image_rgb = image
            
            image_pil = Image.fromarray(image_rgb.astype('uint8'))
        else:
            image_pil = image
        
        # Recognize full image
        text = self.predictor.predict(image_pil)
        
        return {
            'texts': [text] if text else [],
            'confidences': [1.0] if text else [],
            'bboxes': [],  # VietOCR không có detection
            'count': 1 if text else 0
        }

class HybridOCR:
    """
    Kết hợp PaddleOCR detection với VietOCR recognition
    """
    def __init__(self, paddleocr_detection, vietocr_processor):
        self.detection = paddleocr_detection
        self.recognition = vietocr_processor
        print("✓ HybridOCR initialized successfully!")
    
    def process_full_image(self, image):
        """
        Detect bằng PaddleOCR, recognize bằng VietOCR
        """
        # Step 1: Detection với PaddleOCR
        if isinstance(image, str):
            image_cv = cv2.imread(image)
            image_pil = Image.open(image)
        elif isinstance(image, np.ndarray):
            image_cv = image
            image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            image_pil = image
            image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Detect bboxes
        bboxes = self.detection.predict(image_cv)
        
        if not bboxes:
            return {
                'texts': [],
                'confidences': [],
                'bboxes': [],
                'count': 0
            }
        
        # Step 2: Recognition với VietOCR
        texts = []
        confidences = []
        
        for bbox in bboxes:
            try:
                # Process với VietOCR
                result = self.recognition.process_bbox(image_pil, bbox, bbox_format="polygon")
                text = result['text']
                confidence = result['confidence']
                
                texts.append(text)
                confidences.append(confidence)
                
            except Exception as e:
                print(f"Error processing bbox: {e}")
                texts.append("")
                confidences.append(0.0)
        
        return {
            'texts': texts,
            'confidences': confidences,
            'bboxes': bboxes,  # Giữ nguyên polygon format từ detection
            'count': len([t for t in texts if t])
        }

# Example usage
if __name__ == "__main__":
    # Khởi tạo VietOCR
    viet_processor = VietOCRProcessor()
    
    # Test với toàn bộ ảnh
    img_path = r"C:\WorkSpace\GrpcOCR\Screenshot 2025-10-03 143551.png"
    
    print("=== Test process_full_image ===")
    result = viet_processor.process_full_image(img_path)
    print("Full image result:", result)
    
    print("\n=== Test process_bbox ===")
    # Test với bbox cụ thể
    test_bboxes = [
        [100, 50, 300, 100],    # xyxy format
        [150, 120, 400, 160]
    ]
    
    for i, bbox in enumerate(test_bboxes):
        bbox_result = viet_processor.process_bbox(img_path, bbox, bbox_format="xyxy")
        print(f"Bbox {i} result:", bbox_result)
    
    print("\n=== Test process_multiple_bboxes ===")
    # Test với nhiều bboxes cùng lúc
    multi_results = viet_processor.process_multiple_bboxes(img_path, test_bboxes, bbox_format="xyxy")
    print("Multiple bboxes results:")
    for result in multi_results:
        print(f"  Bbox {result['bbox_index']}: '{result['text']}' (conf: {result['confidence']})")
    
    print("\n=== Example HybridOCR usage ===")
    print("# Để sử dụng HybridOCR, import PaddleOCR detection:")
    print("# from python import PaddleOCRDetection")
    print("# detection = PaddleOCRDetection('weights/detection.onnx')")
    print("# hybrid_ocr = HybridOCR(detection, viet_processor)")
    print("# hybrid_result = hybrid_ocr.process_full_image(img_path)")
