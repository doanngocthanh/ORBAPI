"""
Test script để so sánh ORB alignment trước và sau optimization

Run this to verify improvements in feature detection and matching
"""
import cv2
import numpy as np
from service.orb.ORBImageAligner import ORBImageAligner
from config import ImageBaseConfig
import time

def compare_orb_versions():
    """
    So sánh kết quả với different feature counts
    """
    print("="*80)
    print("🧪 ORB ALIGNMENT COMPARISON TEST")
    print("="*80)
    
    # Load test images
    image_config = ImageBaseConfig()
    base_img_path = image_config.get_image("base_qr_cccd")
    
    # Test với ảnh target (thay đổi path này)
    target_img_path = r"C:\Workspace\ORBAPI\images\01HM00019983_img_1_a67965b0.png"
    
    print(f"\n📁 Test images:")
    print(f"  Base: {base_img_path}")
    print(f"  Target: {target_img_path}")
    
    # Test 1: Old configuration (2000 features)
    print("\n" + "="*80)
    print("TEST 1: OLD CONFIG (2000 features)")
    print("="*80)
    
    start_time = time.time()
    aligner_old = ORBImageAligner(target_dimension=800, orb_features=2000)
    
    # Temporarily adjust ORB params back to old values for comparison
    aligner_old.orb = cv2.ORB_create(
        nfeatures=2000,
        scaleFactor=1.2,
        nlevels=8,
        edgeThreshold=31,
        firstLevel=0,
        WTA_K=2,
        scoreType=cv2.ORB_HARRIS_SCORE,
        patchSize=31,
        fastThreshold=20
    )
    
    result_old = aligner_old.align(base_img_path, target_img_path)
    time_old = time.time() - start_time
    
    if result_old["success"]:
        print(f"\n✅ OLD CONFIG Results:")
        print(f"  Features: Base={result_old['features']['base']}, Target={result_old['features']['target']}")
        print(f"  Good matches: {result_old['good_matches']}")
        print(f"  Inliers: {result_old['inliers']}")
        print(f"  Inlier ratio: {result_old['inlier_ratio']:.3f}")
        print(f"  Quality score: {result_old['quality_score']:.3f}")
        print(f"  Time: {time_old:.3f}s")
    else:
        print(f"\n❌ OLD CONFIG Failed: {result_old['error']}")
    
    # Test 2: New configuration (5000 features)
    print("\n" + "="*80)
    print("TEST 2: NEW CONFIG (5000 features)")
    print("="*80)
    
    start_time = time.time()
    aligner_new = ORBImageAligner(target_dimension=800, orb_features=5000)
    result_new = aligner_new.align(base_img_path, target_img_path)
    time_new = time.time() - start_time
    
    if result_new["success"]:
        print(f"\n✅ NEW CONFIG Results:")
        print(f"  Features: Base={result_new['features']['base']}, Target={result_new['features']['target']}")
        print(f"  Good matches: {result_new['good_matches']}")
        print(f"  Inliers: {result_new['inliers']}")
        print(f"  Inlier ratio: {result_new['inlier_ratio']:.3f}")
        print(f"  Quality score: {result_new['quality_score']:.3f}")
        print(f"  Time: {time_new:.3f}s")
    else:
        print(f"\n❌ NEW CONFIG Failed: {result_new['error']}")
    
    # Comparison
    print("\n" + "="*80)
    print("📊 COMPARISON SUMMARY")
    print("="*80)
    
    if result_old["success"] and result_new["success"]:
        print(f"\n{'Metric':<20} {'Old':<15} {'New':<15} {'Improvement':<15}")
        print("-"*80)
        
        # Features
        old_features = result_old['features']['target']
        new_features = result_new['features']['target']
        features_improvement = ((new_features - old_features) / old_features) * 100
        print(f"{'Features detected':<20} {old_features:<15} {new_features:<15} {features_improvement:>+.1f}%")
        
        # Good matches
        old_matches = result_old['good_matches']
        new_matches = result_new['good_matches']
        matches_improvement = ((new_matches - old_matches) / old_matches) * 100 if old_matches > 0 else 0
        print(f"{'Good matches':<20} {old_matches:<15} {new_matches:<15} {matches_improvement:>+.1f}%")
        
        # Inliers
        old_inliers = result_old['inliers']
        new_inliers = result_new['inliers']
        inliers_improvement = ((new_inliers - old_inliers) / old_inliers) * 100 if old_inliers > 0 else 0
        print(f"{'Inliers':<20} {old_inliers:<15} {new_inliers:<15} {inliers_improvement:>+.1f}%")
        
        # Quality score
        old_quality = result_old['quality_score']
        new_quality = result_new['quality_score']
        quality_improvement = ((new_quality - old_quality) / old_quality) * 100 if old_quality > 0 else 0
        print(f"{'Quality score':<20} {old_quality:<15.3f} {new_quality:<15.3f} {quality_improvement:>+.1f}%")
        
        # Time
        time_increase = ((time_new - time_old) / time_old) * 100
        print(f"{'Processing time (s)':<20} {time_old:<15.3f} {time_new:<15.3f} {time_increase:>+.1f}%")
        
        print("\n" + "="*80)
        
        # Calculate OCR quality thresholds
        print("\n🎯 OCR QUALITY CHECK:")
        print("-"*80)
        
        def check_quality(matches, inliers, blur_score=500):
            """Simulate quality check from OCR_CCCD_QR"""
            if inliers < 25 or matches < 50:
                return False, 0, "Below absolute minimums"
            
            score = 0
            # Inliers scoring
            if inliers >= 100: score += 40
            elif inliers >= 60: score += 35
            elif inliers >= 40: score += 25
            elif inliers >= 25: score += 15
            else: score += 5
            
            # Matches scoring
            if matches >= 300: score += 30
            elif matches >= 150: score += 25
            elif matches >= 80: score += 20
            elif matches >= 50: score += 12
            else: score += 5
            
            # Blur scoring (assume good)
            if blur_score >= 300: score += 30
            elif blur_score >= 200: score += 25
            elif blur_score >= 100: score += 15
            else: score += 10
            
            passed = score >= 50
            return passed, score, "PASS" if passed else "FAIL"
        
        old_passed, old_score, old_status = check_quality(old_matches, old_inliers)
        new_passed, new_score, new_status = check_quality(new_matches, new_inliers)
        
        print(f"{'Config':<20} {'Quality Score':<20} {'Status':<15}")
        print(f"{'Old (2000 feat)':<20} {old_score}/100 {'':<5} {old_status:<15}")
        print(f"{'New (5000 feat)':<20} {new_score}/100 {'':<5} {new_status:<15}")
        
        print("\n" + "="*80)
        
        if new_passed and not old_passed:
            print("🎉 SUCCESS! New config passes quality check while old config fails!")
        elif new_score > old_score:
            print(f"📈 IMPROVEMENT! Quality score increased by {new_score - old_score} points")
        else:
            print("⚠️ No significant improvement in quality score")
        
        # Save comparison images
        try:
            if result_old["success"]:
                cv2.imwrite("comparison_old_aligned.jpg", result_old["aligned_image"])
                cv2.imwrite("comparison_old_vis.jpg", result_old["visualization_image"])
                print("\n💾 Old results saved: comparison_old_aligned.jpg, comparison_old_vis.jpg")
            
            if result_new["success"]:
                cv2.imwrite("comparison_new_aligned.jpg", result_new["aligned_image"])
                cv2.imwrite("comparison_new_vis.jpg", result_new["visualization_image"])
                print("💾 New results saved: comparison_new_aligned.jpg, comparison_new_vis.jpg")
        except Exception as e:
            print(f"⚠️ Could not save images: {e}")
    
    else:
        if not result_old["success"]:
            print("\n❌ Old config failed, cannot compare")
        if not result_new["success"]:
            print("❌ New config failed, cannot compare")
    
    print("\n" + "="*80)
    print("✅ Test completed!")
    print("="*80)

if __name__ == "__main__":
    try:
        compare_orb_versions()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
