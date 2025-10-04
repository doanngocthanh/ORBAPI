from service.yolo.YOLODetector import YOLODetector, DetectionConfig
from config import PtConfig, ImageBaseConfig, WeightsConfig
from VietOCRApi import VietOCRProcessor
from PaddletOCRApi import PaddleOCRProcessor
import json
import numpy as np
import cv2
from PIL import Image
class OCR_CCCD_2025_NEW:
    def __init__(self,face=None):
        self.config = DetectionConfig(
            conf_threshold=0.25,
            iou_threshold=0.3,
            max_positions_per_label=2,
            target_size=640,
            enhance_image=False
        )
        self.config_mrz = DetectionConfig(
            conf_threshold=0.0,
            iou_threshold=0.0,
            max_positions_per_label=1,
            target_size=640,
            enhance_image=False
        )
        self.ptconfig = PtConfig()
        self.weights_config = WeightsConfig()
        self.image_base_config = ImageBaseConfig()
        self.viet_ocr_processor = VietOCRProcessor()
        self.paddleocr = PaddleOCRProcessor(weights_dir=self.weights_config.getdir())
        self.model = YOLODetector(self.ptconfig.get_model("OCR_CCCD_2025"), self.config)
        self.mrz = YOLODetector(self.ptconfig.get_model("MRZ"), self.config_mrz)      
        self.image_front = self.image_base_config.get_image("base_cccd_new")
        #self.image_back = self.image_base_config.get_image("base_qr_cccd_back")
    
    def crop_black_padding(self, aligned_image):
        """
        Chỉ crop bỏ phần padding đen xung quanh, giữ nguyên nội dung và aspect ratio
        
        Args:
            aligned_image: Ảnh đã align (PIL Image hoặc numpy array)
            
        Returns:
            numpy.ndarray: Ảnh đã crop, giữ nguyên kích thước nội dung thực
        """
        import cv2
        from PIL import Image
        
        # Convert to CV2 format
        if isinstance(aligned_image, Image.Image):
            aligned_cv = cv2.cvtColor(np.array(aligned_image), cv2.COLOR_RGB2BGR)
        else:
            aligned_cv = aligned_image
        
        aligned_h, aligned_w = aligned_cv.shape[:2]
        print(f"📐 Aligned image size (before crop): {aligned_w}x{aligned_h}")
        
        # Tìm vùng nội dung (non-black area) trong aligned image
        gray = cv2.cvtColor(aligned_cv, cv2.COLOR_BGR2GRAY)
        # Tìm các pixel không đen (threshold > 10 để tránh noise)
        _, thresh = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        
        # Tìm contours của vùng nội dung
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Tìm bounding box của vùng nội dung lớn nhất
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Thêm margin nhỏ (2 pixels) để tránh mất viền
            margin = 2
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(aligned_cv.shape[1] - x, w + 2*margin)
            h = min(aligned_cv.shape[0] - y, h + 2*margin)
            
            print(f"✂️ Cropping black padding: from ({aligned_w}x{aligned_h}) to ({w}x{h})")
            print(f"   Removed: left={x}px, top={y}px, right={aligned_w-x-w}px, bottom={aligned_h-y-h}px")
            
            # Crop vùng nội dung - GIỮ NGUYÊN KÍCH THƯỚC NỘI DUNG
            cropped = aligned_cv[y:y+h, x:x+w]
            
            print(f"✅ Final size after crop: {cropped.shape[1]}x{cropped.shape[0]}")
            return cropped
        else:
            print("⚠️ Could not find content area, returning original aligned image")
            return aligned_cv
    def process_mrz(self, image_path):  
        """
        Process MRZ (Machine Readable Zone) from citizen card image
        
        Args:
            image_path: Path to image or np.ndarray
        Returns:
            dict: Extracted MRZ data
        """
        result = self.mrz.detect(image_path)
        mrz_data = {}
        for detection in result:
        # Crop MRZ region and display it
                    
                    # Load image if it's a path
                    if isinstance(image_path, str):
                        img = cv2.imread(image_path)
                    elif isinstance(image_path, Image.Image):
                        img = cv2.cvtColor(np.array(image_path), cv2.COLOR_RGB2BGR)
                    else:
                        img = image_path
                    
                    # Crop MRZ region using bbox (xyxy format)
                    x1, y1, x2, y2 = map(int, detection.bbox)
                    mrz_crop = img[y1:y2, x1:x2]
                    
                    # # Display cropped MRZ
                    # import matplotlib.pyplot as plt
                    # plt.figure(figsize=(12, 4))
                    # plt.imshow(cv2.cvtColor(mrz_crop, cv2.COLOR_BGR2RGB))
                    # plt.title(f"MRZ Detection - Class: {detection.class_name}")
                    # plt.axis('off')
                    # plt.tight_layout()
                    # plt.show()
                    
                    # Enhance MRZ image quality before OCR
                    # 1. Resize to larger size for better OCR (scale up 2x)
                    scale_factor = 2
                    mrz_enhanced = cv2.resize(mrz_crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
                    
                    # 2. Convert to grayscale
                    gray_mrz = cv2.cvtColor(mrz_enhanced, cv2.COLOR_BGR2GRAY)
                    
                    # 3. Apply denoising
                    denoised = cv2.fastNlMeansDenoising(gray_mrz, None, h=10, templateWindowSize=7, searchWindowSize=21)
                    
                    # 4. Apply adaptive thresholding for better contrast
                    adaptive_thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                           cv2.THRESH_BINARY, 11, 2)
                    
                    # 5. Apply sharpening
                    kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                    sharpened = cv2.filter2D(adaptive_thresh, -1, kernel_sharpen)
                    
                    # 6. Convert back to BGR for OCR
                    mrz_final = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
                    
                    # Process MRZ with OCR using enhanced image
                    ocr_result = self.paddleocr.process_full_image(mrz_final)
                   
                    
                    # Extract MRZ-specific data
                    mrz_texts = []
                    if ocr_result and 'texts' in ocr_result:
                        mrz_texts = ocr_result['texts']
                    
                    # Combine MRZ lines into single string
                    mrz_string = ''.join(mrz_texts)
                    # Build structured MRZ result
                    mrz_data = {
                        "status": "success" if mrz_texts else "failed",
                        "message": f"Found {len(mrz_texts)} MRZ text lines" if mrz_texts else "No MRZ text found",
                        "texts": mrz_texts,
                        "mrz_string": mrz_string,
                        "mrz_length": len(mrz_string),
                        "total_mrz_regions": 1,
                        "dates_found": ocr_result.get('dates', []) if ocr_result else [],
                        "total_dates": len(ocr_result.get('dates', [])) if ocr_result else 0,
                        "all_ocr_texts": ocr_result.get('texts', []) if ocr_result else []
                    }
                    break  # Giả sử chỉ có một MRZ trên thẻ
        return mrz_data
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
        expected_detections = len(result) # Expected number of labels for a complete citizen card
        print(f"Detections found: {expected_detections}")
        print(f"Total class counts: {self.model.get_total_classes()}")
        
        # Biến để lưu ảnh được sử dụng cuối cùng (có thể là ảnh gốc hoặc aligned)
        final_image_for_ocr = image_path
        
        missing_detections = self.model.get_total_classes() - expected_detections
        if missing_detections > 3:
            # Re-detect using ORB if missing more than 3 fields
            print(f"Missing {missing_detections} detections, re-detecting with ORB...")
            from service.orb.ORBImageAligner import ORBImageAligner
            from PIL import Image
            import cv2
            
            aligner = ORBImageAligner(target_dimension=800, orb_features=5000)
            # Determine if image_path is front or back side and set appropriate template
            template_image = self.image_front
            alignment_result = aligner.align(template_image, image_path)
            aligned_image = alignment_result.get("aligned_image")
            
            # Kiểm tra chất lượng alignment
            inliers = alignment_result.get("inliers", 0)
            good_matches = alignment_result.get("good_matches", 0)
            
            print(f"📊 Alignment quality check:")
            print(f"  - Good matches: {good_matches}")
            print(f"  - Inliers: {inliers}")
            
            # Kiểm tra độ mờ (blur) của aligned image
            if aligned_image is not None:
                if isinstance(aligned_image, Image.Image):
                    aligned_cv = cv2.cvtColor(np.array(aligned_image), cv2.COLOR_RGB2BGR)
                else:
                    aligned_cv = aligned_image
                
                gray = cv2.cvtColor(aligned_cv, cv2.COLOR_BGR2GRAY)
                blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                print(f"  - Blur score: {blur_score:.2f} (higher is sharper)")
                
                # Ngưỡng chất lượng alignment (điều chỉnh dựa trên thực tế)
                # Sử dụng scoring system linh hoạt thay vì hard threshold
                
                # 1. Kiểm tra ngưỡng tối thiểu tuyệt đối (MUST HAVE)
                # Giảm ngưỡng vì algorithm mới có thể cho inliers thấp nhưng vẫn tốt
                min_absolute_inliers = 25  # Tối thiểu 25 inliers
                min_absolute_matches = 50  # Tăng matches vì có nhiều features hơn
                min_blur_score = 50  # Giữ nguyên blur score
                
                if inliers < min_absolute_inliers or good_matches < min_absolute_matches or blur_score < min_blur_score:
                    print(f"❌ Alignment quality below absolute minimum thresholds")
                    print(f"   (inliers={inliers}<{min_absolute_inliers} OR matches={good_matches}<{min_absolute_matches} OR blur={blur_score:.2f}<{min_blur_score})")
                    quality_ok = False
                else:
                    # 2. Đánh giá chất lượng bằng scoring system
                    score = 0
                    
                    # Điểm cho inliers (0-40 điểm) - điều chỉnh tiers
                    if inliers >= 100:
                        score += 40
                    elif inliers >= 60:
                        score += 35
                    elif inliers >= 40:
                        score += 25
                    elif inliers >= 25:
                        score += 15
                    else:
                        score += 5
                    
                    # Điểm cho good matches (0-30 điểm) - tăng ngưỡng do có nhiều features hơn
                    if good_matches >= 300:
                        score += 30
                    elif good_matches >= 150:
                        score += 25
                    elif good_matches >= 80:
                        score += 20
                    elif good_matches >= 50:
                        score += 12
                    else:
                        score += 5
                    
                    # Điểm cho blur score (0-30 điểm)
                    if blur_score >= 300:
                        score += 30
                    elif blur_score >= 200:
                        score += 25
                    elif blur_score >= 100:
                        score += 15
                    else:
                        score += 10
                    
                    # Ngưỡng chấp nhận: >= 50/100 điểm
                    min_total_score = 50
                    quality_ok = score >= min_total_score
                    
                    print(f"  - Quality score: {score}/100 (min: {min_total_score})")
                    print(f"    • Inliers: {inliers} (weight: 40%)")
                    print(f"    • Good matches: {good_matches} (weight: 30%)")
                    print(f"    • Blur score: {blur_score:.2f} (weight: 30%)")
                
                if quality_ok:
                    print("✅ Aligned image quality is acceptable, processing...")
                    
                    # Chỉ crop bỏ padding đen, giữ nguyên kích thước nội dung
                    print("\n🔧 Post-processing aligned image...")
                    processed_aligned = self.crop_black_padding(aligned_image)
                    
                    # Detect trên ảnh đã xử lý
                    result = self.model.detect(processed_aligned)
                
                    # So sánh số lượng detections
                    detections_aligned = len(result)
                    print(f"\n📊 Comparison: Original={expected_detections}, Aligned={detections_aligned}")
                    
                    # Chỉ dùng aligned image nếu detect được nhiều hơn
                    if detections_aligned > expected_detections:
                        print("✅ Aligned image gives better results, using it")
                        final_image_for_ocr = processed_aligned  # Dùng ảnh aligned đã xử lý cho OCR
                        
                        # Optional: Show aligned image
                        # import matplotlib.pyplot as plt
                        # plt.figure(figsize=(12, 6))
                        
                        # # Show original aligned (trước khi crop/resize)
                        # plt.subplot(1, 2, 1)
                        # if isinstance(aligned_image, Image.Image):
                        #     plt.imshow(aligned_image)
                        # else:
                        #     plt.imshow(Image.fromarray(cv2.cvtColor(aligned_cv, cv2.COLOR_BGR2RGB)))
                        # plt.title(f"Aligned (before crop/resize)")
                        # plt.axis('off')
                        
                        # # Show processed aligned (sau khi crop/resize)
                        # plt.subplot(1, 2, 2)
                        # plt.imshow(cv2.cvtColor(processed_aligned, cv2.COLOR_BGR2RGB))
                        # plt.title(f"Processed (Detections: {detections_aligned})")
                        # plt.axis('off')
                        
                        # plt.tight_layout()
                        # plt.show()
                    else:
                        print("⚠️ Aligned image doesn't improve detection count, using original image")
                else:
                    print(f"❌ Aligned image quality is insufficient")
                    print("⚠️ Using original image instead")
            else:
                print("❌ Alignment failed, using original image")
           
          
        # Extract text from detections using the final image
        for detection in result:
            print(detection)
            class_name = detection.class_name
            if class_name not in ['portrait', 'top_right', 'bottom_right', 'bottom_left', 'top_left',"Sex","ID","Name","Date_of_birth","Nationality",'Date of expirty','Date of issue',"Place","Place of birth"]:
                citizens_card_data[class_name] = self.viet_ocr_processor.process_bbox(
                    final_image_for_ocr, detection.bbox
                ).get("text", "")
        
        return citizens_card_data

if __name__ == "__main__":
    ocr_processor = OCR_CCCD_2025_NEW()
    image = r"C:\Users\dntdo\Downloads\DataSetSource\OCR_CCCD.v4i.yolov8 (1)\train\images\20039138_01JCZNF6FBSXV9311RJRX16Q0E743517_back_jpg.rf.45b539b51f9cb527147fdb2ac0889e9d.jpg"
    # Test MRZ detection with debugging
    print("\n=== Testing MRZ Detection ===")
    mrz_result = ocr_processor.process_mrz(image)
    
    # Nối các dòng text MRZ lại thành một chuỗi duy nhất
    if mrz_result and 'texts' in mrz_result:
        mrz_combined = ''.join(mrz_result['texts'])
        mrz_result['mrz_combined'] = mrz_combined
        print(f"\n🔗 Combined MRZ text: {mrz_combined}")
    
    # If MRZ detection fails, try processing as normal card
    
    print(json.dumps(mrz_result, indent=4, ensure_ascii=False))
