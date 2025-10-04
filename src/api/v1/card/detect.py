import os
from fastapi import APIRouter
from service.detect.CCCDDetector import CCCDDetector
from config import PtConfig
from service.yolo.YOLODetector import DetectionConfig
from fastapi import File, UploadFile
import io
from PIL import Image
import numpy as np
import json
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
async def detect_card(image_file: UploadFile = File(...)):
        try:
            # Read the uploaded file
            contents = await image_file.read()
            # Convert to PIL Image if needed
            image = Image.open(io.BytesIO(contents))
            
            # Save the uploaded image temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                image.save(tmp_file.name)
                temp_path = tmp_file.name
            
            # Initialize detector with config
            pt_config = PtConfig()
            cccd_detector = CCCDDetector(pt_config.get_model("CCCD_FACE_DETECT_2025_NEW_TITLE"), config)
          
            # Process the uploaded image
            result =  cccd_detector.process_image(temp_path, return_json=True, verbose=True)
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}