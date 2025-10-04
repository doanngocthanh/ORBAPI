from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional, List
import uuid
from service.MRZExtractor import MRZExtractor
from service.utils.ImageUploadHandler import ImageUploadHandler

# Router setup
router = APIRouter(
    prefix="/api/v1",
    tags=["MRZ Detection"],
    responses={
        404: {"description": "Not found"}
    }
)
@router.post("/mrz/ext")
async def mrz(file: UploadFile = File(...)):
    """
    Extract MRZ (Machine Readable Zone) from ID card image
    Automatically handles RGBA/PNG images and converts to RGB
    """
    # Validate file type
    if not file.filename.lower().endswith(('.jpg', '.png', '.jpeg', '.bmp', '.webp')):
        raise HTTPException(
            status_code=400, 
            detail="File must be an image (jpg, png, jpeg, bmp, webp)."
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Initialize image handler with auto RGB conversion
        image_handler = ImageUploadHandler(auto_convert_to_rgb=True)
        
        # Process uploaded image (handles RGBA -> RGB conversion automatically)
        try:
            upload_result = image_handler.process_upload(
                content,
                save_temp=False,  # MRZ works with bytes directly
                format='JPEG',
                calculate_metrics=True
            )
            
            image_info = upload_result['info']
            quality_metrics = upload_result['metrics']
            
            # Log conversion info
            if image_info['converted']:
                print(f"✓ MRZ: Converted image from {image_info['original_mode']} to {image_info['final_mode']}")
            
            # Convert PIL image back to bytes for MRZ processing
            import io
            output = io.BytesIO()
            upload_result['image'].save(output, format='JPEG', quality=95)
            processed_content = output.getvalue()
            
        except ValueError as e:
            # Handle image processing errors
            raise HTTPException(status_code=400, detail=f"Image processing error: {str(e)}")
        
        # Initialize MRZ extractor service
        mrz_extractor = MRZExtractor()
        
        # Extract MRZ using service (with processed content)
        result = mrz_extractor.extract_mrz_from_bytes(processed_content)
        
        # Add image info and quality metrics to result
        if isinstance(result, dict):
            result['image_info'] = {
                **image_info,
                **quality_metrics
            }
        
        # Handle different result statuses
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        elif result["status"] == "no_mrz_detected":
            return {
                **result,
                "message": "No MRZ regions detected in the image."
            }
        elif result["status"] == "ocr_failed":
            return {
                **result,
                "message": "OCR processing failed."
            }
        
        # Return successful result (dates are already included by MRZExtractor service)
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")