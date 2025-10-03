from service.yolo.YOLODetector import YOLODetector, DetectionConfig
from config import PtConfig, ImageBaseConfig
from VietOCRApi import VietOCRProcessor
import json
import numpy as np

class OCR_CCCD_QR:
    def __init__(self,face=None):
        self.config = DetectionConfig(
            conf_threshold=0.25,
            iou_threshold=0.3,
            max_positions_per_label=2,
            target_size=640,
            enhance_image=False
        )
        self.ptconfig = PtConfig()
        self.image_base_config = ImageBaseConfig()
        self.viet_ocr_processor = VietOCRProcessor()
        self.model = YOLODetector(self.ptconfig.get_model("OCR_QR_CCCD"), self.config)
        
        if face=="cccd_qr_back":
            self.image_front = self.image_base_config.get_image("base_qr_cccd_back")
        self.image_front = self.image_base_config.get_image("base_qr_cccd")
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
            if class_name not in ['portrait', 'qr_code']:
                citizens_card_data[class_name] = self.viet_ocr_processor.process_bbox(
                    final_image_for_ocr, detection.bbox
                ).get("text", "")
        
        return citizens_card_data

if __name__ == "__main__":
    ocr_processor = OCR_CCCD_QR()
    image = r"C:\Users\dntdo\Downloads\6ea2c189-978c-486b-8503-85f3ef114eef.jpg"
    result = ocr_processor.process_image(image)
    print(json.dumps(result, indent=4, ensure_ascii=False))
