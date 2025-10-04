import os
from fastapi import APIRouter, HTTPException
from service.detect.CCCDDetector import CCCDDetector
from config import PtConfig
from service.yolo.YOLODetector import DetectionConfig
from fastapi import File, UploadFile
from service.utils.ImageUploadHandler import ImageUploadHandler
router = APIRouter(
    prefix="/api/v1",
    tags=["VietNam Citizens Card Detection"],
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
    
@router.post("/card/detect")
async def detect_card(file: UploadFile = File(...)):
    """
    Detect Vietnamese Citizen Card (CCCD) from uploaded image
    Automatically handles RGBA/PNG images and converts to RGB/JPEG
    """
    try:
        # Read the uploaded file
        contents = await file.read()
        
        # Initialize image handler with auto RGB conversion
        image_handler = ImageUploadHandler(auto_convert_to_rgb=True)
        
        # Process uploaded image (handles RGBA -> RGB conversion automatically)
        upload_result = image_handler.process_upload(
            contents,
            save_temp=True,
            format='JPEG',
            calculate_metrics=True
        )
        
        temp_path = upload_result['temp_path']
        image_info = upload_result['info']
        quality_metrics = upload_result['metrics']
        
        # Log conversion info
        if image_info['converted']:
            print(f"✓ Converted image from {image_info['original_mode']} to {image_info['final_mode']}")
        
        # Initialize detector with config
        pt_config = PtConfig()
        cccd_detector = CCCDDetector(
            pt_config.get_model("CCCD_FACE_DETECT_2025_NEW_TITLE"), 
            config
        )
        
        # Process the uploaded image
        result = cccd_detector.process_image(temp_path, return_json=True, verbose=True)
        
        # Add image info and quality metrics to result
        if isinstance(result, dict):
            result['image_info'] = {
                **image_info,
                **quality_metrics
            }
        
        # Clean up temporary file
        image_handler.cleanup_temp(temp_path)
        
        return result
        
    except ValueError as e:
        # Handle validation errors (file size, format, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")