import os
import json
from pathlib import Path

# Define the log directory path
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'tasks')


class TaskStatistics:
    """Service for collecting and analyzing task statistics"""
    
    @staticmethod
    def get_statistics():
        """Get statistics from all task logs"""
        stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_cards_detected": 0,
            "card_types": {},
            "average_processing_time": 0,
            "total_processing_time": 0,
            "image_quality_stats": {
                "average_blur_score": 0,
                "average_brightness": 0,
                "average_contrast": 0,
                "average_quality_score": 0
            },
            "detection_confidence": {
                "average": 0,
                "min": float('inf'),
                "max": 0
            }
        }
        
        # Ensure log directory exists
        if not os.path.exists(LOG_DIR):
            return stats
        
        task_files = [f for f in os.listdir(LOG_DIR) if f.endswith('.json')]
        stats["total_tasks"] = len(task_files)
        
        if stats["total_tasks"] == 0:
            return stats
        
        processing_times = []
        blur_scores = []
        brightness_scores = []
        contrast_scores = []
        quality_scores = []
        confidences = []
        
        for filename in task_files:
            try:
                with open(os.path.join(LOG_DIR, filename), 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                
                # Count status
                if task_data.get("status") == "completed":
                    stats["completed_tasks"] += 1
                else:
                    stats["failed_tasks"] += 1
                
                result = task_data.get("result", {})
                
                # Processing time
                if "timing" in result:
                    processing_times.append(result["timing"].get("total_elapsed_time", 0))
                elif "elapsed_time" in result:
                    processing_times.append(result.get("elapsed_time", 0))
                
                # Image quality stats
                if "image_info" in result:
                    img_info = result["image_info"]
                    blur_scores.append(img_info.get("blur_score", 0))
                    brightness_scores.append(img_info.get("brightness", 0))
                    contrast_scores.append(img_info.get("contrast", 0))
                    quality_scores.append(img_info.get("quality_score", 0))
                
                # Card detection stats
                if "details" in result:
                    for detail in result["details"]:
                        if "card_info" in detail and "detections" in detail["card_info"]:
                            for detection in detail["card_info"]["detections"]:
                                label = detection.get("detected_label", "unknown")
                                stats["card_types"][label] = stats["card_types"].get(label, 0) + 1
                                stats["total_cards_detected"] += 1
                                
                                conf = detection.get("confidence", 0)
                                confidences.append(conf)
                                stats["detection_confidence"]["min"] = min(stats["detection_confidence"]["min"], conf)
                                stats["detection_confidence"]["max"] = max(stats["detection_confidence"]["max"], conf)
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
        
        # Calculate averages
        if processing_times:
            stats["average_processing_time"] = round(sum(processing_times) / len(processing_times), 3)
            stats["total_processing_time"] = round(sum(processing_times), 3)
        
        if blur_scores:
            stats["image_quality_stats"]["average_blur_score"] = round(sum(blur_scores) / len(blur_scores), 2)
        if brightness_scores:
            stats["image_quality_stats"]["average_brightness"] = round(sum(brightness_scores) / len(brightness_scores), 2)
        if contrast_scores:
            stats["image_quality_stats"]["average_contrast"] = round(sum(contrast_scores) / len(contrast_scores), 2)
        if quality_scores:
            stats["image_quality_stats"]["average_quality_score"] = round(sum(quality_scores) / len(quality_scores), 2)
        
        if confidences:
            stats["detection_confidence"]["average"] = round(sum(confidences) / len(confidences), 4)
        else:
            stats["detection_confidence"]["min"] = 0
        
        return stats
    
if __name__ == "__main__":
    stats = TaskStatistics.get_statistics()
    print(json.dumps(stats, indent=4))