from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
import io
from PIL import Image
import base64
from typing import List, Optional
import json
import os
from service.orb.ORBImageAligner import ORBImageAligner
# Import our OCR processors
from PaddletOCRApi import PaddleOCRProcessor

# Try to import VietOCR (optional)
try:
    from VietOCRApi import VietOCRProcessor
    VIETOCR_AVAILABLE = True
except ImportError:
    print("⚠️  VietOCR not available. Install with: pip install vietocr")
    VietOCRProcessor = None
    VIETOCR_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Engine OCR API", 
    description="OCR API supporting multiple engines: PaddleOCR, VietOCR",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OCR processors
paddle_ocr_processor = None
viet_ocr_processor = None

try:
    paddle_ocr_processor = PaddleOCRProcessor(weights_dir='weights')
    print("✓ PaddleOCR Processor initialized successfully!")
except Exception as e:
    print(f"✗ Error initializing PaddleOCR Processor: {e}")

if VIETOCR_AVAILABLE:
    try:
        viet_ocr_processor = VietOCRProcessor()
        print("✓ VietOCR Processor initialized successfully!")
    except Exception as e:
        print(f"✗ Error initializing VietOCR Processor: {e}")
else:
    print("⚠️  VietOCR Processor not available")

# Utility functions
def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    return obj

def decode_image(image_data: bytes) -> np.ndarray:
    """Decode image from bytes to numpy array"""
    try:
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        image_np = np.array(image)
        
        # Convert RGB to BGR for OpenCV
        image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        return image_bgr
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error decoding image: {str(e)}")

# API Routes
@app.get("/", response_class=FileResponse)
async def get_upload_page():
    """Serve the HTML upload page"""
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        return HTMLResponse(content="<h1>HTML file not found. Please ensure index.html exists.</h1>", status_code=404)

@app.post("/process-full-image")
async def process_full_image(file: UploadFile = File(...)):
    """Process full image and return all detected text"""
    if paddle_ocr_processor is None:
        raise HTTPException(status_code=500, detail="PaddleOCR processor not initialized")
    
    try:
        # Read and decode image
        image_data = await file.read()
        image = decode_image(image_data)
        
        # Process image
        result = paddle_ocr_processor.process_full_image(image)
        
        # Convert numpy types to JSON serializable types
        serializable_result = convert_numpy_types({
            "success": True,
            "count": result["count"],
            "texts": result["texts"],
            "confidences": result["confidences"],
            "bboxes": result["bboxes"]
        })
        
        return JSONResponse(content=serializable_result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# ===========================
# VIETOCR ENDPOINTS
# ===========================

@app.post("/vietocr/process-full-image")
async def vietocr_process_full_image(file: UploadFile = File(...)):
    """Process full image using VietOCR and return recognized text"""
    if not VIETOCR_AVAILABLE or viet_ocr_processor is None:
        raise HTTPException(status_code=500, detail="VietOCR processor not available")
    
    try:
        # Read and decode image
        image_data = await file.read()
        image_pil = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if image_pil.mode != 'RGB':
            image_pil = image_pil.convert('RGB')
        
        # Process image
        result = viet_ocr_processor.process_full_image(image_pil)
        
        # Convert numpy types to JSON serializable types
        serializable_result = convert_numpy_types({
            "success": True,
            "engine": "VietOCR",
            "count": result["count"],
            "texts": result["texts"],
            "confidences": result["confidences"],
            "bboxes": result["bboxes"]
        })
        
        return JSONResponse(content=serializable_result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image with VietOCR: {str(e)}")

@app.post("/vietocr/process-bboxes")
async def vietocr_process_bboxes(
    file: UploadFile = File(...),
    bboxes: str = Form(...),
    bbox_format: str = Form(default="xyxy")
):
    """Process specific bboxes using VietOCR and return text for each bbox"""
    if not VIETOCR_AVAILABLE or viet_ocr_processor is None:
        raise HTTPException(status_code=500, detail="VietOCR processor not available")
    
    try:
        # Read and decode image
        image_data = await file.read()
        image_pil = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if image_pil.mode != 'RGB':
            image_pil = image_pil.convert('RGB')
        
        # Parse bboxes
        try:
            bboxes_list = json.loads(bboxes)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid bbox format")
        
        # Convert bboxes to the format expected by our processor
        processed_bboxes = []
        for bbox in bboxes_list:
            if bbox_format.lower() == "xyxy":
                processed_bboxes.append([bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]])
            else:
                processed_bboxes.append(bbox)
        
        # Process bboxes
        results = viet_ocr_processor.process_multiple_bboxes(image_pil, processed_bboxes, bbox_format)
        
        # Convert numpy types to JSON serializable types
        serializable_results = convert_numpy_types({
            "success": True,
            "engine": "VietOCR",
            "results": results
        })
        
        return JSONResponse(content=serializable_results)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bboxes with VietOCR: {str(e)}")

@app.post("/vietocr/process-single-bbox")
async def vietocr_process_single_bbox(
    file: UploadFile = File(...),
    bbox: str = Form(...),
    bbox_format: str = Form(default="xyxy")
):
    """Process a single bbox using VietOCR and return text"""
    if not VIETOCR_AVAILABLE or viet_ocr_processor is None:
        raise HTTPException(status_code=500, detail="VietOCR processor not available")
    
    try:
        # Read and decode image
        image_data = await file.read()
        image_pil = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if image_pil.mode != 'RGB':
            image_pil = image_pil.convert('RGB')
        
        # Parse bbox
        try:
            bbox_data = json.loads(bbox)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid bbox format")
        
        # Convert bbox format if needed
        if bbox_format.lower() == "xyxy" and isinstance(bbox_data, dict):
            bbox_list = [bbox_data["x1"], bbox_data["y1"], bbox_data["x2"], bbox_data["y2"]]
        else:
            bbox_list = bbox_data
        
        # Process bbox
        result = viet_ocr_processor.process_bbox(image_pil, bbox_list, bbox_format)
        
        # Convert numpy types to JSON serializable types
        serializable_result = convert_numpy_types({
            "success": True,
            "engine": "VietOCR",
            "text": result["text"],
            "confidence": result["confidence"],
            "bbox": result["bbox"]
        })
        
        return JSONResponse(content=serializable_result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bbox with VietOCR: {str(e)}")

@app.post("/process-bboxes")
async def process_bboxes(
    file: UploadFile = File(...),
    bboxes: str = Form(...),
    bbox_format: str = Form(default="xyxy")
):
    """Process specific bboxes in image and return text for each bbox"""
    if paddle_ocr_processor is None:
        raise HTTPException(status_code=500, detail="PaddleOCR processor not initialized")
    
    try:
        # Read and decode image
        image_data = await file.read()
        image = decode_image(image_data)
        
        # Parse bboxes
        try:
            bboxes_list = json.loads(bboxes)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid bbox format")
        
        # Convert bboxes to the format expected by our processor
        processed_bboxes = []
        for bbox in bboxes_list:
            if bbox_format.lower() == "xyxy":
                processed_bboxes.append([bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]])
            else:
                processed_bboxes.append(bbox)
        
        # Process bboxes
        results = paddle_ocr_processor.process_multiple_bboxes(image, processed_bboxes, bbox_format)
        
        # Convert numpy types to JSON serializable types
        serializable_results = convert_numpy_types(results)
        
        return JSONResponse(content=serializable_results)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bboxes: {str(e)}")

@app.post("/process-single-bbox")
async def process_single_bbox(
    file: UploadFile = File(...),
    bbox: str = Form(...),
    bbox_format: str = Form(default="xyxy")
):
    """Process a single bbox in image and return text"""
    if paddle_ocr_processor is None:
        raise HTTPException(status_code=500, detail="PaddleOCR processor not initialized")
    
    try:
        # Read and decode image
        image_data = await file.read()
        image = decode_image(image_data)
        
        # Parse bbox
        try:
            bbox_data = json.loads(bbox)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid bbox format")
        
        # Convert bbox format if needed
        if bbox_format.lower() == "xyxy" and isinstance(bbox_data, dict):
            bbox_list = [bbox_data["x1"], bbox_data["y1"], bbox_data["x2"], bbox_data["y2"]]
        else:
            bbox_list = bbox_data
        
        # Process bbox
        result = paddle_ocr_processor.process_bbox(image, bbox_list, bbox_format)
        
        # Convert numpy types to JSON serializable types
        serializable_result = convert_numpy_types({
            "success": True,
            "text": result["text"],
            "confidence": result["confidence"],
            "bbox": result["bbox"]
        })
        
        return JSONResponse(content=serializable_result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing bbox: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "paddle_ocr_available": paddle_ocr_processor is not None,
        "viet_ocr_available": VIETOCR_AVAILABLE and viet_ocr_processor is not None,
        "engines": {
            "paddleocr": paddle_ocr_processor is not None,
            "vietocr": VIETOCR_AVAILABLE and viet_ocr_processor is not None
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Multi-Engine OCR FastAPI Server...")
    print("📋 Available endpoints:")
    print("  - GET  /                               : HTML upload interface")
    print("  - GET  /health                         : Health check")
    print("")
    print("🔥 PADDLEOCR ENDPOINTS:")
    print("  - POST /process-full-image              : Process entire image (Legacy)")
    print("  - POST /process-bboxes                  : Process multiple bboxes (Legacy)")
    print("  - POST /process-single-bbox             : Process single bbox (Legacy)")
    print("")
    print("🔥 VIETOCR ENDPOINTS:")
    print("  - POST /vietocr/process-full-image      : Process entire image with VietOCR")
    print("  - POST /vietocr/process-bboxes          : Process multiple bboxes with VietOCR")
    print("  - POST /vietocr/process-single-bbox     : Process single bbox with VietOCR")
    print("")
    print("📊 Engine Status:")
    print(f"  - PaddleOCR: {'✓ Available' if paddle_ocr_processor else '✗ Not Available'}")
    print(f"  - VietOCR: {'✓ Available' if VIETOCR_AVAILABLE and viet_ocr_processor else '✗ Not Available'}")
    print("")
    print("🌐 Open http://localhost:8000 in your browser to use the interface")
    print("📚 API docs available at http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
