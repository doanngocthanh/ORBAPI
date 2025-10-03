from service.yolo.YOLODetector import YOLODetector, DetectionConfig
import os
import json
from CardService import CardService, CardSideService

class CCCDDetector:
    # Mapping detected labels to card categories and types
    LABEL_TO_CARD_MAPPING = {
        'cccd_new_front': {'category_id': 5, 'type_id': 0},  # New Citizens Card - Front
        'cccd_new_back': {'category_id': 5, 'type_id': 1},   # New Citizens Card - Back
        'cccd_old_front': {'category_id': 0, 'type_id': 0},  # Citizens Card - Front
        'cccd_old_back': {'category_id': 0, 'type_id': 1},   # Citizens Card - Back
        'cccd_qr_front': {'category_id': 0, 'type_id': 0},   # New Citizens Card - Front (QR detected)
        'cccd_qr_back': {'category_id': 0, 'type_id': 1},    # New Citizens Card - Back (QR detected)
        'gplx_front': {'category_id': 1, 'type_id': 0},      # Driving License - Front
        'gplx_back': {'category_id': 1, 'type_id': 1},       # Driving License - Back
        'bank_card': {'category_id': 3, 'type_id': 0},       # Bank Card
        'cmnd_front': {'category_id': 6, 'type_id': 0},      # ID Card - Front
        'cmnd_back': {'category_id': 6, 'type_id': 1},       # ID Card - Back

    }
    
    def __init__(self, model_path, config, weights_dir='weights'):
        self.detector = YOLODetector(model_path, config)
        self.paddle_ocr_processor = None
        self.weights_dir = weights_dir
        
        self.cccd_new_keywords = ["cancuoc"]
        self.cccd_old_keywords = ["cancuoccongdan", "cuoccongdan", "congdan"]
        self.cccd_back_old_keywords = ["dacdiemnhandang", "notruoi", "cuccanhsat"]
        self.cccd_back_new_keywords = ["noicutru", "noidangkykhaisinh", "bocongan"]
    
    def _init_ocr_processors(self):
        """Lazy initialization of OCR processors"""
        if self.paddle_ocr_processor is None:
            from PaddletOCRApi import PaddleOCRProcessor
            self.paddle_ocr_processor = PaddleOCRProcessor(weights_dir=self.weights_dir)
      
    
    def _convert_bbox(self, bbox):
        """Convert bbox to both paddle and viet formats"""
        if isinstance(bbox[0], (list, tuple)):
            x_coords = [pt[0] for pt in bbox]
            y_coords = [pt[1] for pt in bbox]
            paddle_bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
            viet_bbox = [list(map(float, pt)) for pt in bbox]
            if len(viet_bbox) != 4:
                viet_bbox = [[paddle_bbox[0], paddle_bbox[1]], [paddle_bbox[2], paddle_bbox[1]], 
                            [paddle_bbox[2], paddle_bbox[3]], [paddle_bbox[0], paddle_bbox[3]]]
        else:
            paddle_bbox = bbox
            x1, y1, x2, y2 = map(float, bbox)
            viet_bbox = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        return paddle_bbox, viet_bbox
    
    def _classify_cccd_type(self, full_image_combined):
        """Classify CCCD type based on text"""
        from unidecode import unidecode
        
        if any(kw.replace(" ", "") in full_image_combined for kw in self.cccd_old_keywords):
            return "Old CCCD"
        elif any(kw.replace(" ", "") in full_image_combined for kw in self.cccd_new_keywords):
            return "New CCCD"
        elif any(kw.replace(" ", "") in full_image_combined for kw in self.cccd_back_old_keywords):
            return "Old CCCD Back Side"
        elif any(kw.replace(" ", "") in full_image_combined for kw in self.cccd_back_new_keywords):
            return "New CCCD Back Side"
        else:
            return "Not CCCD"
    
    def _analyze_ocr_features(self, detections_raw):
        """Analyze OCR features from raw detections"""
        features = {
            'has_portrait': None,
            'has_qr_code': None,
            'has_basic_info': None,
            'has_address_info': None,
            'detected_info_types': []
        }
        
        return features
    
    def _determine_card_validity(self, detected_label, ocr_features):
        """Determine if detected card is valid based on features"""
        # Basic validation logic - can be extended
        if detected_label in self.LABEL_TO_CARD_MAPPING:
            # If it's a known card type with some features detected, consider it valid
            return len(ocr_features['detected_info_types']) > 0
        return False
    
    def _calculate_bbox_area(self, bbox):
        """Calculate the area of a bounding box"""
        if isinstance(bbox[0], (list, tuple)):
            x_coords = [pt[0] for pt in bbox]
            y_coords = [pt[1] for pt in bbox]
            width = max(x_coords) - min(x_coords)
            height = max(y_coords) - min(y_coords)
        else:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
        return width * height
    
    def _bboxes_overlap(self, bbox1, bbox2, threshold=0.5):
        """Check if two bounding boxes overlap significantly"""
        # Convert both bboxes to [x1, y1, x2, y2] format
        if isinstance(bbox1[0], (list, tuple)):
            x1_coords = [pt[0] for pt in bbox1]
            y1_coords = [pt[1] for pt in bbox1]
            box1 = [min(x1_coords), min(y1_coords), max(x1_coords), max(y1_coords)]
        else:
            box1 = bbox1
        
        if isinstance(bbox2[0], (list, tuple)):
            x2_coords = [pt[0] for pt in bbox2]
            y2_coords = [pt[1] for pt in bbox2]
            box2 = [min(x2_coords), min(y2_coords), max(x2_coords), max(y2_coords)]
        else:
            box2 = bbox2
        
        # Calculate intersection
        x_left = max(box1[0], box2[0])
        y_top = max(box1[1], box2[1])
        x_right = min(box1[2], box2[2])
        y_bottom = min(box1[3], box2[3])
        
        if x_right < x_left or y_bottom < y_top:
            return False
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        # Calculate IoU (Intersection over Union)
        iou = intersection_area / float(box1_area + box2_area - intersection_area)
        
        return iou >= threshold
    
    def process_image(self, img_path, filter_mode=1, verbose=True, return_json=True):
        """Process a single image and return detections with OCR results"""
        self._init_ocr_processors()
        from unidecode import unidecode
        
        detections_raw = self.detector.detect(img_path, filter_mode=filter_mode)
        
        # Filter to keep only the largest detection if multiple detections found
        
        if verbose:
            print(f"\nProcessing: {os.path.basename(img_path)}")
            print(f"Found {len(detections_raw)} detections:")
        
        if return_json:
            # Return in JSON format as requested
            json_result = {"detections": []}
            
            # Đếm số lượng từng class
            class_counts = self.detector.count_detections_by_class(detections_raw)
            json_result["class_counts"] = class_counts
            
            processed_bboxes = []
            
            for det in detections_raw:
                class_name = getattr(det, 'class_name', None)
                confidence = getattr(det, 'confidence', 0.0)
                current_bbox = det.bbox
                
                # Check if this bbox overlaps significantly with any already processed bbox
                should_skip = False
                for processed_bbox in processed_bboxes:
                    if self._bboxes_overlap(current_bbox, processed_bbox, threshold=0.5):
                        should_skip = True
                        if verbose:
                            print(f"\nSkipping duplicate detection in same region: {class_name}")
                        break
                
                if should_skip:
                    continue
                
                # Add current bbox to processed list
                processed_bboxes.append(current_bbox)
                
                # Get card mapping
                card_mapping = self.LABEL_TO_CARD_MAPPING.get(class_name, None)
                
                if card_mapping and card_mapping['category_id'] is not None:
                    card_category = CardService.get_card_by_id(card_mapping['category_id'])
                    card_type = CardSideService.get_side_by_id(card_mapping['type_id'])
                else:
                    card_category = None
                    card_type = None
                
                # Analyze OCR features
                ocr_features = self._analyze_ocr_features([det])
                
                # Determine validity
                is_valid = self._determine_card_validity(class_name, ocr_features)
                
                # Determine title type if it's a title detection
                title_detected_type = None
                if class_name == 'title':
                    title_detected_type = "unknown"
                
                detection_result = {
                    "confidence": float(confidence),
                    "detected_label": class_name,
                    "card_category": card_category,
                    "card_type": card_type,
                    "is_valid_card": is_valid,
                    "title_detected_type": title_detected_type,
                    "ocr_features": ocr_features
                }
                
                json_result["detections"].append(detection_result)
                
                if verbose:
                    print(f"\nDetection: {class_name} (confidence: {confidence:.4f})")
                    print(f"  Card Category: {card_category['name'] if card_category else 'Unknown'}")
                    print(f"  Card Type: {card_type['name'] if card_type else 'Unknown'}")
                    print(f"  Valid Card: {is_valid}")
                    print(f"  OCR Features: {ocr_features}")
                    
            return json_result
        
        else:
            # Return in original format for backward compatibility
            results = []
            
            for det in detections_raw:
                label = getattr(det, 'label', None)
                class_id = getattr(det, 'class_id', None)
                class_name = getattr(det, 'class_name', None)
                name = getattr(det, 'name', None)
                
                if verbose:
                    print(f"Detection attributes: label={label}, class_id={class_id}, class_name={class_name}, name={name}")
                
                paddle_bbox = self._convert_bbox(det.bbox)
                
                paddle_result = self.paddle_ocr_processor.process_bbox(img_path, paddle_bbox, bbox_format="xyxy")
                
                full_result = self.paddle_ocr_processor.process_full_image(img_path)
                
                full_image_texts = full_result.get('texts', [])
                full_image_combined = unidecode(" ".join(full_image_texts).lower()).replace(" ", "")
                
                cccd_type = self._classify_cccd_type(full_image_combined)
                
                if verbose:
                    print("PaddleOCR Result:", paddle_result)
                    
                    print("Combined Full Image Texts (normalized):", full_image_combined)
                    print(f"=> Detected as {cccd_type}")
                
                results.append({
                    'detection': det,
                    'paddle_result': paddle_result,
                   
                    'full_image_combined': full_image_combined,
                    'cccd_type': cccd_type
                })
            
            return results
    
    def process_directory(self, image_dir, filter_mode=1, verbose=True, return_json=True):
        """Process all images in a directory"""
        all_results = {}
        for fname in os.listdir(image_dir):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                continue
            img_path = os.path.join(image_dir, fname)
            all_results[fname] = self.process_image(img_path, filter_mode, verbose, return_json)
        return all_results


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from config import PtConfig
    
    # Cấu hình
    config = DetectionConfig(
        conf_threshold=0.25,
        iou_threshold=0.3,
        max_positions_per_label=1,
        target_size=640,
        enhance_image=False
    )
    
    model_path = r"C:\Workspace\ORBAPI\models\pt\CCCD_FACE_DETECT_2025_NEW_TITLE.pt"
    image_dir = r"C:\Workspace\ORBAPI\images"
    
    # ['cccd_new_front', 'cccd_new_back', 'cccd_qr_front', 'cccd_qr_back', 'gplx_front', 'gplx_back', 'title']
    # Khởi tạo và sử dụng
    cccd_detector = CCCDDetector(model_path, config)
    
    # Test with a single image first
    result = cccd_detector.process_image(r"C:\Workspace\ORBAPI\images\76_jpg.rf.b1cc66974b0d8696f41ea393a1eb7a69.jpg", return_json=True, verbose=True)

        # Print JSON result
    print("\n" + "="*50)
    print("JSON OUTPUT:")
    print("="*50)
    print(json.dumps(result, indent=4, ensure_ascii=False))
    # Uncomment to process all images
    # results = cccd_detector.process_directory(image_dir, return_json=True)