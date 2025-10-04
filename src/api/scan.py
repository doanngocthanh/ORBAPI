import os
from urllib import response
from fastapi import APIRouter
from service.detect.CCCDDetector import CCCDDetector
from config import PtConfig
from service.yolo.YOLODetector import DetectionConfig
from fastapi import File, UploadFile
import io
from PIL import Image
import numpy as np
import json
import uuid
from datetime import datetime
from typing import Dict
from service.utils.ImageUploadHandler import ImageUploadHandler

router = APIRouter(
    prefix="/api/scan",
    tags=["VietNam Citizens Card Scanner"],
    responses={
        404: {"description": "Not found"}
    }
)

config = DetectionConfig(
        conf_threshold=0.25,
        iou_threshold=0.3,
        max_positions_per_label=1,
        target_size=640,
        enhance_image=False)

# Lưu trữ tasks trong memory (có thể thay bằng database)
tasks: Dict[str, dict] = {}

# Tạo thư mục log nếu chưa có
LOG_DIR = "logs/tasks"
os.makedirs(LOG_DIR, exist_ok=True)

def save_task_to_file(task_id: str, task_data: dict):
    """Lưu task data ra file JSON"""
    file_path = os.path.join(LOG_DIR, f"{task_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(task_data, f, ensure_ascii=False, indent=2)

def load_task_from_file(task_id: str) -> dict:
    """Đọc task data từ file JSON"""
    file_path = os.path.join(LOG_DIR, f"{task_id}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None
@router.post("/", status_code=200)
@router.post("", status_code=200, include_in_schema=False)
async def scan_card(image_file: UploadFile = File(...)):
    import time
    import cv2
    file = image_file
    # Tạo UUID cho request
    task_id = str(uuid.uuid4())
    start_time = time.time()
    start_timestamp = datetime.now()
    
    # Khởi tạo task log
    task_data = {
        "id": task_id,
        "status": "processing",
        "created_at": start_timestamp.isoformat(),
        "filename": file.filename
    }
    tasks[task_id] = task_data
    
    try:
        # Read the uploaded file
        contents = await file.read()
        
        # Process image with handler
        image_handler = ImageUploadHandler(auto_convert_to_rgb=True)
        upload_result = image_handler.process_upload(
            contents,
            save_temp=True,
            format='JPEG',
            calculate_metrics=True
        )
        
        image = upload_result['image']
        temp_path = upload_result['temp_path']
        
        # Build image quality info
        image_quality = {
            "original_size": len(contents),
            "load_method": "ImageUploadHandler",
            "format": upload_result['info']['original_format'],
            "original_mode": upload_result['info']['original_mode'],
            "final_mode": upload_result['info']['final_mode'],
            "converted": upload_result['info']['converted'],
            "width": upload_result['info']['width'],
            "height": upload_result['info']['height'],
            "quality_score": upload_result['metrics']['quality_score'],
            "blur_score": upload_result['metrics']['blur_score'],
            "brightness": upload_result['metrics']['brightness'],
            "contrast": upload_result['metrics']['contrast']
        }
        
        # Initialize detector with config
        pt_config = PtConfig()
        cccd_detector = CCCDDetector(pt_config.get_model("CCCD_FACE_DETECT_2025_NEW_TITLE"), config)
        
        # Detect card from the image
        detection_result = cccd_detector.process_image(temp_path)
        print(f"Detection result: {detection_result}")
        print(f"Task ID: {task_id}")
        
        # Initialize result structure
        ocr_data = {
            "id": "",
            "name": "",
            "birth": "",
            "sex": "",
            "nationality": "",
            "place_of_origin": "",
            "place_of_residence": "",
            "expiry": ""
        }
        
        card_ocr_results = {
            "full_name": "",
            "id_number": "",
            "date_of_birth": "",
            "sex": "",
            "nationality": "",
            "place_of_origin": "",
            "place_of_residence": "",
            "expiry": "",
            "portrait": "",
            "qr_code": "",
            "day": "",
            "month": "",
            "year": ""
        }
        
        detections = detection_result.get('detections', [])
        
        # Initialize response structure early to avoid UnboundLocalError
        response = {
            "status": "processing",
            "message": "Image processing in progress",
            "task_id": task_id,
            "timing": {},
            "image_info": image_quality,
            "results": {},
            "details": [],
            "mrz_result": {}
        }
        mrz_result = None
        if detections:
            item = detections[0]
            detected_label = item.get('detected_label')
            print(f"Detected label: {detected_label}")
            
            # Add image quality to detection result
            item['image_quality'] = image_quality
            
            if detected_label in ['cccd_qr_front', 'cccd_qr_back']:
                from service.card.OCR_CCCD_QR import OCR_CCCD_QR
                ocr_processor = OCR_CCCD_QR(face=detected_label)
                ocr_result = ocr_processor.process_image(temp_path)
                
                # Map OCR results
                ocr_data = {
                    "id": ocr_result.get("id", ""),
                    "name": ocr_result.get("name", ""),
                    "birth": ocr_result.get("birth", ""),
                    "sex": ocr_result.get("sex", ""),
                    "nationality": ocr_result.get("nationality", ""),
                    "place_of_origin": ocr_result.get("place_of_origin", ""),
                    "place_of_residence": ocr_result.get("place_of_residence", ""),
                    "expiry": ocr_result.get("expiry", "")
                }
                
                card_ocr_results = {
                    "full_name": ocr_result.get("name", ""),
                    "id_number": ocr_result.get("id", ""),
                    "date_of_birth": ocr_result.get("birth", ""),
                    "sex": ocr_result.get("sex", ""),
                    "nationality": ocr_result.get("nationality", ""),
                    "place_of_origin": ocr_result.get("place_of_origin", ""),
                    "place_of_residence": ocr_result.get("place_of_residence", ""),
                }
                
                # Process MRZ for back side only
                if 'back' in detected_label:
                    from service.MRZExtractor import MRZExtractor
                
                    # Initialize MRZ extractor service
                    mrz_extractor = MRZExtractor()
                    
                    # Extract MRZ using service
                    mrz_result = mrz_extractor.extract_mrz_from_bytes(contents)
                  
                print(f"OCR result for {detected_label}: {ocr_result}")
                
            elif detected_label in ['cccd_new_front', 'cccd_new_back']:
                from service.card.OCR_CCCD_2025_NEW import OCR_CCCD_2025_NEW
                ocr_processor = OCR_CCCD_2025_NEW()
               
                ocr_result = ocr_processor.process_image(temp_path)
                
                # Process MRZ for back side only
               
                if 'back' in detected_label:
                        from service.MRZExtractor import MRZExtractor
                        mrz_extractor = MRZExtractor()
                        # Extract MRZ using service
                        mrz_result = mrz_extractor.extract_mrz_from_bytes(contents)

                print(f"OCR result for {detected_label}: {ocr_result}")
                # Map OCR results (adjust based on OCR_CCCD_2025 output structure)
                if isinstance(ocr_result, dict):
                    ocr_data = {
                        "id": ocr_result.get("c_id", ""),
                        "name": ocr_result.get("c_full_name", ""),
                        "birth": ocr_result.get("cdate_of_birth", ""),
                        "sex": ocr_result.get("c_sex", ""),
                        "nationality": ocr_result.get("c_national", ""),
                        "place_of_origin": ocr_result.get("cplace_of_birth", ""),
                        "place_of_residence": ocr_result.get("address_1", "")+" "+ocr_result.get("address_2", ""),
                        "expiry": ocr_result.get("cdate_of_expiry", "")
                    }
                    
                    card_ocr_results.update({
                        "full_name": ocr_result.get("c_full_name", ""),
                        "id_number": ocr_result.get("c_id", ""),
                        "date_of_birth": ocr_result.get("cdate_of_birth", ""),
                        "sex": ocr_result.get("c_sex", ""),
                        "nationality": ocr_result.get("c_national", ""),
                        "place_of_origin": ocr_result.get("cplace_of_birth", ""),
                        "place_of_residence": ocr_result.get("address_1", "")+" "+ocr_result.get("address_2", ""),
                        "expiry": ocr_result.get("cdate_of_expiry", ""),
                        "date_of_issue": ocr_result.get("cdate_of_issue", "")
                    })
        
        # Clean up temp file
        image_handler.cleanup_temp(temp_path)
        
        # Calculate timing
        end_time = time.time()
        elapsed_time = round(end_time - start_time, 3)
        end_timestamp = datetime.now()
        
        # Update final response structure
        response.update({
            "status": "completed",
            "message": "Image processed successfully",
            "timing": {
                "start_time": start_time,
                "end_time": end_time,
                "start_timestamp": start_timestamp.isoformat(),
                "end_timestamp": end_timestamp.isoformat(),
                "total_elapsed_time": elapsed_time
            },
            "results": {
                "processing_time_sec": elapsed_time,
                "results": [ocr_data]
            },
            "details": [
                {
                    "card_info": {
                        "detections": detections,
                        "image_quality": image_quality,
                        "debug_info": {
                            "total_detections": len(detections),
                            "ocr_detections": len([d for d in detections if d.get('detected_label') not in ['portrait', 'qr_code']]),
                            "detected_types": [d.get('detected_label') for d in detections],
                            "sex_detected": any(d.get('detected_label') == 'sex' for d in detections),
                            "sex_confidence": next((d.get('confidence', 0) for d in detections if d.get('detected_label') == 'sex'), 0)
                        }
                    },
                    "card_ocr_results": card_ocr_results,
                    "timing": {},
                    "ocr_fields_count": sum(1 for v in card_ocr_results.values() if v),
                    "ocr_fields_total": len(card_ocr_results)
                }
            ],
            "mrz_result": mrz_result if mrz_result else {
                "status": "no_mrz_detected",
                "message": "No MRZ regions detected in the image.",
                "texts": [],
                "mrz_string": "",
                "mrz_length": 0,
                "total_mrz_regions": 0,
                "dates_found": [],
                "total_dates": 0
            },
            "start_time": start_time,
            "elapsed_time": elapsed_time
        })
        
        task_data["status"] = "completed"
        task_data["result"] = response
        tasks[task_id] = task_data
        save_task_to_file(task_id, task_data)
        
        return response
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        
        end_time = time.time()
        elapsed_time = round(end_time - start_time, 3)
        
        error_response = {
            "status": "error",
            "message": str(e),
            "task_id": task_id,
            "error_detail": error_detail,
            "elapsed_time": elapsed_time
        }
        
        task_data["status"] = "error"
        task_data["error"] = str(e)
        task_data["error_detail"] = error_detail
        tasks[task_id] = task_data
        save_task_to_file(task_id, task_data)
        
        return error_response
    

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    # Kiểm tra trong memory trước
    if task_id in tasks:
        return tasks[task_id]
    
    # Nếu không có trong memory, đọc từ file
    task_data = load_task_from_file(task_id)
    if task_data:
        return task_data
    
    return {"error": "Task not found"}, 404