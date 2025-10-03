import cv2
import numpy as np
import matplotlib.pyplot as plt

class ORBImageAligner:
    """
    Class để thực hiện alignment ảnh sử dụng ORB features với size normalization
    Xử lý hoàn toàn trong bộ nhớ, không lưu file
    """
    
    def __init__(self, target_dimension=800, orb_features=2000):
        """
        Khởi tạo ORB Image Aligner
        
        Args:
            target_dimension (int): Kích thước chuẩn để normalize (default: 800)
            orb_features (int): Số lượng ORB features tối đa (default: 2000)
        """
        self.target_dimension = target_dimension
        self.orb_features = orb_features
        
        # Khởi tạo ORB detector
        self.orb = cv2.ORB_create(
            nfeatures=orb_features,
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=31,
            firstLevel=0,
            WTA_K=2,
            scoreType=cv2.ORB_HARRIS_SCORE,
            patchSize=31,
            fastThreshold=20
        )
        
        # RANSAC configurations for robustness
        self.ransac_configs = [
            {"threshold": 3.0, "maxIters": 3000, "confidence": 0.99},
            {"threshold": 5.0, "maxIters": 2000, "confidence": 0.995},
            {"threshold": 1.5, "maxIters": 5000, "confidence": 0.98},
        ]
        
    def normalize_size(self, base_img, target_img):
        """
        Đồng nhất kích thước 2 ảnh về cùng scale
        
        Args:
            base_img: Ảnh base
            target_img: Ảnh target
            
        Returns:
            tuple: (base_normalized, target_normalized, base_scale, target_scale)
        """
        # Tính scale cho base image
        base_h, base_w = base_img.shape[:2]
        base_max_dim = max(base_h, base_w)
        base_scale = self.target_dimension / base_max_dim
        
        # Resize base image
        base_new_w = int(base_w * base_scale)
        base_new_h = int(base_h * base_scale)
        base_normalized = cv2.resize(base_img, (base_new_w, base_new_h))
        
        # Tính scale cho target image
        target_h, target_w = target_img.shape[:2]
        target_max_dim = max(target_h, target_w)
        target_scale = self.target_dimension / target_max_dim
        
        # Resize target image
        target_new_w = int(target_w * target_scale)
        target_new_h = int(target_h * target_scale)
        target_normalized = cv2.resize(target_img, (target_new_w, target_new_h))
        
        print(f"🔧 Normalized sizes - Base: {base_normalized.shape}, Target: {target_normalized.shape}")
        
        return base_normalized, target_normalized, base_scale, target_scale
    
    def enhanced_preprocessing(self, img):
        """
        Preprocessing để tăng chất lượng features
        
        Args:
            img: Ảnh input
            
        Returns:
            numpy.ndarray: Ảnh đã được preprocessing
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # CLAHE để enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Gaussian blur nhẹ để giảm noise
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        return blurred
    
    def detect_and_match_features(self, base_processed, target_processed):
        """
        Detect và match ORB features
        
        Args:
            base_processed: Ảnh base đã preprocessing
            target_processed: Ảnh target đã preprocessing
            
        Returns:
            tuple: (good_matches, keypoints1, keypoints2) hoặc None nếu thất bại
        """
        # Detect features
        kp1, desc1 = self.orb.detectAndCompute(base_processed, None)
        kp2, desc2 = self.orb.detectAndCompute(target_processed, None)
        
        if desc1 is None or desc2 is None:
            return None
        
        print(f"✨ Features found - Base: {len(kp1)}, Target: {len(kp2)}")
        
        # Feature matching
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(desc1, desc2, k=2)
        
        # Lowe's ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)
        
        print(f"💎 Good matches: {len(good_matches)}")
        
        if len(good_matches) < 10:
            return None
        
        return good_matches, kp1, kp2
    
    def find_robust_homography(self, good_matches, kp1, kp2):
        """
        Tìm homography matrix robust với multiple RANSAC attempts
        
        Args:
            good_matches: List các good matches
            kp1: Keypoints của ảnh base
            kp2: Keypoints của ảnh target
            
        Returns:
            tuple: (best_matrix, best_inliers, best_mask) hoặc None nếu thất bại
        """
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        best_matrix = None
        best_inliers = 0
        best_mask = None
        
        for config in self.ransac_configs:
            matrix, mask = cv2.findHomography(
                dst_pts, src_pts, cv2.RANSAC,
                config["threshold"], maxIters=config["maxIters"], 
                confidence=config["confidence"]
            )
            
            if matrix is not None:
                inliers = np.sum(mask)
                print(f"  📏 Threshold {config['threshold']}: {inliers} inliers")
                
                if inliers > best_inliers:
                    best_matrix = matrix
                    best_inliers = inliers
                    best_mask = mask
        
        if best_matrix is None:
            return None
        
        print(f"✅ Best result: {best_inliers} inliers")
        return best_matrix, best_inliers, best_mask
    
    def calculate_quality_score(self, base_img, aligned_img):
        """
        Tính quality score cho aligned image
        
        Args:
            base_img: Ảnh base
            aligned_img: Ảnh đã aligned
            
        Returns:
            float: Quality score (0-1)
        """
        try:
            # Convert to grayscale
            base_gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
            aligned_gray = cv2.cvtColor(aligned_img, cv2.COLOR_BGR2GRAY)
            
            # Ensure same size
            h = min(base_gray.shape[0], aligned_gray.shape[0])
            w = min(base_gray.shape[1], aligned_gray.shape[1])
            base_gray = cv2.resize(base_gray, (w, h))
            aligned_gray = cv2.resize(aligned_gray, (w, h))
            
            # Template matching
            corr = cv2.matchTemplate(base_gray, aligned_gray, cv2.TM_CCORR_NORMED)[0][0]
            
            # Mean squared error
            mse = np.mean((base_gray.astype(np.float32) - aligned_gray.astype(np.float32))**2) / (255.0**2)
            
            # Combined score
            quality = corr * (1 - mse)
            
            return max(0, min(1, quality))
            
        except Exception:
            return 0.5
    
    def create_comparison_image(self, base_img, target_img, aligned_img):
        """
        Tạo ảnh so sánh 3 ảnh
        
        Args:
            base_img: Ảnh base
            target_img: Ảnh target
            aligned_img: Ảnh aligned
            
        Returns:
            numpy.ndarray: Ảnh comparison
        """
        height, width = 400, 300
        
        # Resize all to same size
        base_resized = cv2.resize(base_img, (width, height))
        target_resized = cv2.resize(target_img, (width, height))
        aligned_resized = cv2.resize(aligned_img, (width, height))
        
        # Add labels
        cv2.putText(base_resized, "BASE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(target_resized, "TARGET", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(aligned_resized, "ALIGNED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # Combine horizontally
        comparison = np.hstack([base_resized, target_resized, aligned_resized])
        return comparison
    
    def create_visualization(self, base_norm, target_norm, kp1, kp2, good_matches, mask):
        """
        Tạo ảnh visualization showing matches
        
        Args:
            base_norm: Ảnh base normalized
            target_norm: Ảnh target normalized  
            kp1: Keypoints base
            kp2: Keypoints target
            good_matches: Good matches
            mask: Inlier mask
            
        Returns:
            numpy.ndarray: Visualization image
        """
        # Lấy inlier matches
        inlier_matches = [good_matches[i] for i in range(len(good_matches)) if mask[i]]
        
        # Draw matches
        vis_image = cv2.drawMatches(
            base_norm, kp1,
            target_norm, kp2,
            inlier_matches[:30], None,
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
        )
        
        return vis_image
    
    def align(self, base_img, target_img):
        """
        Thực hiện alignment chính - xử lý hoàn toàn trong bộ nhớ
        
        Args:
            base_img: Ảnh base (numpy array hoặc đường dẫn file)
            target_img: Ảnh target (numpy array hoặc đường dẫn file)
            
        Returns:
            dict: Kết quả alignment với các ảnh trong bộ nhớ
        """
        try:
            # Đọc ảnh nếu là đường dẫn
            if isinstance(base_img, str):
                base_image_original = cv2.imread(base_img)
                if base_image_original is None:
                    return {"success": False, "error": "Không thể đọc ảnh base"}
            else:
                base_image_original = base_img.copy()
            
            if isinstance(target_img, str):
                target_image_original = cv2.imread(target_img)
                if target_image_original is None:
                    return {"success": False, "error": "Không thể đọc ảnh target"}
            else:
                target_image_original = target_img.copy()
            
            print(f"📖 Original sizes - Base: {base_image_original.shape}, Target: {target_image_original.shape}")
            
            # Step 1: Size Normalization
            base_norm, target_norm, base_scale, target_scale = self.normalize_size(
                base_image_original, target_image_original
            )
            
            # Step 2: Enhanced preprocessing
            base_processed = self.enhanced_preprocessing(base_norm)
            target_processed = self.enhanced_preprocessing(target_norm)
            
            # Step 3: Feature detection and matching
            print("🔍 ORB feature detection với size đã normalized...")
            match_result = self.detect_and_match_features(base_processed, target_processed)
            
            if match_result is None:
                return {"success": False, "error": "Không tìm thấy đủ features hoặc matches"}
            
            good_matches, kp1, kp2 = match_result
            
            # Step 4: Robust homography estimation  
            print("🎯 Robust homography estimation...")
            homography_result = self.find_robust_homography(good_matches, kp1, kp2)
            
            if homography_result is None:
                return {"success": False, "error": "Không thể tính homography matrix"}
            
            best_matrix, best_inliers, best_mask = homography_result
            
            # Step 5: Scale compensation
            print("📏 Scale compensation...")
            
            # Scale matrix từ target original → target normalized
            target_to_norm = np.array([
                [target_scale, 0, 0],
                [0, target_scale, 0],
                [0, 0, 1]
            ], dtype=np.float32)
            
            # Scale matrix từ base normalized → base original  
            norm_to_base = np.array([
                [1/base_scale, 0, 0],
                [0, 1/base_scale, 0], 
                [0, 0, 1]
            ], dtype=np.float32)
            
            # Final transformation matrix
            final_matrix = norm_to_base @ best_matrix @ target_to_norm
            
            # Step 6: Apply transformation
            h, w = base_image_original.shape[:2]
            aligned_image = cv2.warpPerspective(target_image_original, final_matrix, (w, h))
            
            # Step 7: Quality assessment
            quality_score = self.calculate_quality_score(base_image_original, aligned_image)
            
            # Step 8: Create visualization images
            vis_image = self.create_visualization(base_norm, target_norm, kp1, kp2, good_matches, best_mask)
            comparison = self.create_comparison_image(base_image_original, target_image_original, aligned_image)
            
            return {
                "success": True,
                "aligned_image": aligned_image,
                "visualization_image": vis_image,
                "comparison_image": comparison,
                "base_image": base_image_original,
                "target_image": target_image_original,
                "original_sizes": {
                    "base": base_image_original.shape,
                    "target": target_image_original.shape
                },
                "normalized_sizes": {
                    "base": base_norm.shape,
                    "target": target_norm.shape
                },
                "features": {"base": len(kp1), "target": len(kp2)},
                "good_matches": len(good_matches),
                "inliers": best_inliers,
                "inlier_ratio": best_inliers / len(good_matches),
                "quality_score": quality_score,
                "homography_matrix": final_matrix,
                "scales": {"base_scale": base_scale, "target_scale": target_scale}
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def print_result_summary(self, result):
        """
        In tóm tắt kết quả alignment
        
        Args:
            result (dict): Kết quả từ hàm align()
        """
        if result["success"]:
            print("\n" + "="*50)
            print("✅ SIZE-NORMALIZED ALIGNMENT THÀNH CÔNG!")
            
            print(f"\n📏 Size Info:")
            print(f"  Original - Base: {result['original_sizes']['base']}, Target: {result['original_sizes']['target']}")
            print(f"  Normalized - Base: {result['normalized_sizes']['base']}, Target: {result['normalized_sizes']['target']}")
            print(f"  Scales - Base: {result['scales']['base_scale']:.3f}, Target: {result['scales']['target_scale']:.3f}")
            
            print(f"\n🔍 Matching Info:")
            print(f"  Features: Base={result['features']['base']}, Target={result['features']['target']}")
            print(f"  Good matches: {result['good_matches']}")
            print(f"  Inliers: {result['inliers']} (ratio: {result['inlier_ratio']:.3f})")
            print(f"  Quality Score: {result['quality_score']:.3f}")
            
            if result['quality_score'] > 0.7:
                print("🎉 CHẤT LƯỢNG XUẤT SẮC!")
            elif result['quality_score'] > 0.5:
                print("👍 CHẤT LƯỢNG TỐT!")
            elif result['quality_score'] > 0.3:
                print("👌 Chất lượng khá")
            else:
                print("⚠️ Cần kiểm tra")
                
        else:
            print(f"❌ Lỗi: {result['error']}")
    
    def display_results(self, result):
        """
        Hiển thị kết quả alignment bằng matplotlib
        
        Args:
            result (dict): Kết quả từ hàm align()
        """
        if not result["success"]:
            print(f"❌ Lỗi: {result['error']}")
            return
        
        # Convert BGR to RGB cho matplotlib
        aligned_rgb = cv2.cvtColor(result["aligned_image"], cv2.COLOR_BGR2RGB)
        vis_rgb = cv2.cvtColor(result["visualization_image"], cv2.COLOR_BGR2RGB)
        comp_rgb = cv2.cvtColor(result["comparison_image"], cv2.COLOR_BGR2RGB)
        
        # Display aligned image
        plt.figure(figsize=(8, 8))
        plt.title("Aligned Image")
        plt.imshow(aligned_rgb)
        plt.axis("off")
        plt.tight_layout()
        plt.show()
        
        # Display visualization
        plt.figure(figsize=(14, 7))
        plt.title("Feature Matches Visualization")
        plt.imshow(vis_rgb)
        plt.axis("off")
        plt.tight_layout()
        plt.show()
        
        # Display comparison
        plt.figure(figsize=(18, 6))
        plt.title("Comparison (Base | Target | Aligned)")
        plt.imshow(comp_rgb)
        plt.axis("off")
        plt.tight_layout()
        plt.show()


# Example usage
if __name__ == "__main__":
    # Khởi tạo aligner
    aligner = ORBImageAligner(target_dimension=800, orb_features=2000)
    
    # Thực hiện alignment (có thể truyền đường dẫn hoặc numpy array)
    base_path = r"C:\WorkSpace\DECDM\img\base_cccd_qr.jpg"
    target_path = r"C:\Users\0100644068\Downloads\New folder (3)\z7065551240806_9bc3b22dba7439d88d3d49b02e3f85eb.jpg"
    
    print("🚀 SIZE-NORMALIZED ORB ALIGNMENT (MEMORY ONLY)")
    print("="*50)
    
    result = aligner.align(base_path, target_path)
    
    # In tóm tắt
    aligner.print_result_summary(result)
    
    # Hiển thị kết quả
    if result["success"]:
        aligner.display_results(result)
        
        # Nếu muốn lưu file (optional)
        # cv2.imwrite("aligned.jpg", result["aligned_image"])
        # cv2.imwrite("visualization.jpg", result["visualization_image"])
        # cv2.imwrite("comparison.jpg", result["comparison_image"])