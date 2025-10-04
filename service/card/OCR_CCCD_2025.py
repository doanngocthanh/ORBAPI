from service.yolo.YOLODetector import YOLODetector, DetectionConfig
from config import PtConfig
from service.ocr.VietOCRApi import VietOCRProcessor
import json

class OCR_CCCD_2025:
    def __init__(self):
        self.config = DetectionConfig(
            conf_threshold=0.25,
            iou_threshold=0.3,
            max_positions_per_label=2,
            target_size=640,
            enhance_image=False
        )
        self.ptconfig = PtConfig()
        self.viet_ocr_processor = VietOCRProcessor()
        self.model = YOLODetector(self.ptconfig.get_model("OCR_CCCD_2025"), self.config)
    
    def process_image(self, image_path):
        """
        Process citizen card image and extract text data
        
        Args:
            image_path: Path to image or np.ndarray
            
        Returns:
            dict: Extracted citizen card data
        """
        result = self.model.detect(image_path)
        citizens_card_data = {}
        
        for detection in result:
            print(detection)
            class_name = detection.class_name
            if class_name not in ['portrait', 'top_right', 'bottom_right', 'bottom_left', 'top_left',"Sex","ID","Name","Date_of_birth","Nationality",'Date of expirty','Date of issue',"Place","Place of birth"]:
                citizens_card_data[class_name] = self.viet_ocr_processor.process_bbox(
                    image_path, detection.bbox
                ).get("text", "")
        
        return citizens_card_data

if __name__ == "__main__":
    ocr_processor = OCR_CCCD_2025()
    image = r"C:\Users\dntdo\Downloads\CCCD.v1i.yolov8\train\images\20023680_01JB0HFCW6H8NV4DBEWZ6C2MMN201368_front_jpg.rf.49507e265a22582c81e8ff013451e320.jpg"
    result = ocr_processor.process_image(image)
    print(json.dumps(result, indent=4, ensure_ascii=False))
    image2=r"C:\Users\dntdo\Downloads\CCCD.v1i.yolov8\train\images\20021580_01JARERNB2WRRB85DQ1P0J2XQE379632_back_jpg.rf.76e1bbb66d69493a77a15423d526e635.jpg"
    result2 = ocr_processor.process_image(image2)
    print(json.dumps(result2, indent=4, ensure_ascii=False))