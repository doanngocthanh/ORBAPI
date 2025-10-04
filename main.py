import os
os.environ['NNPACK_WARN'] = '0'  # Suppress NNPACK warnings
import warnings
warnings.filterwarnings('ignore')  # Suppress other warnings
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
import io
from PIL import Image
import base64
from typing import List, Optional, Dict, Any
import json
import os
import traceback
from service.orb.ORBImageAligner import ORBImageAligner
from config import RouterConfig, MiddlewareConfig

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Engine OCR API", 
    description="OCR API supporting multiple engines: PaddleOCR, VietOCR",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
RouterConfig().include_routers(app, RouterConfig().api_dir, "src.api")
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================
# ENGINE INITIALIZATION
# ===========================

# Initialize engine availability flags
PADDLEOCR_AVAILABLE = False
VIETOCR_AVAILABLE = False

# Initialize processors
paddle_ocr_processor = None
viet_ocr_processor = None

# Try to initialize PaddleOCR
try:
    from service.ocr.PaddletOCRApi import PaddleOCRProcessor
    paddle_ocr_processor = PaddleOCRProcessor(weights_dir='weights') 
    PADDLEOCR_AVAILABLE = True
    print("✓ PaddleOCR Engine initialized successfully!")
except Exception as e:
    print(f"✗ PaddleOCR Engine failed to initialize: {e}")
    PADDLEOCR_AVAILABLE = False

# Try to initialize VietOCR
try:
    from service.ocr.VietOCRApi import VietOCRProcessor
    viet_ocr_processor = VietOCRProcessor()
    VIETOCR_AVAILABLE = True
    print("✓ VietOCR Engine initialized successfully!")
except Exception as e:
    print(f"✗ VietOCR Engine failed to initialize: {e}")
    VIETOCR_AVAILABLE = False

# ===========================
# UTILITY FUNCTIONS
# ===========================

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

def decode_image_to_cv2(image_data: bytes) -> np.ndarray:
    """Decode image from bytes to OpenCV format (BGR)"""
    try:
        image = Image.open(io.BytesIO(image_data))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image_np = np.array(image)
        return cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error decoding image: {str(e)}")

def decode_image_to_pil(image_data: bytes) -> Image.Image:
    """Decode image from bytes to PIL format (RGB)"""
    try:
        image = Image.open(io.BytesIO(image_data))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return image
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error decoding image: {str(e)}")

def parse_bboxes(bboxes_str: str) -> List:
    """Parse bboxes from JSON string"""
    try:
        return json.loads(bboxes_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid bbox JSON format")

def standardize_response(success: bool, engine: str, data: Dict[str, Any] = None, error: str = None) -> Dict:
    """Standardize API response format"""
    response = {
        "success": success,
        "engine": engine,
        "timestamp": None,  # Could add timestamp if needed
    }
    
    if success and data:
        response.update(data)
    elif not success and error:
        response["error"] = error
    
    return convert_numpy_types(response)

# ===========================
# MAIN ROUTES
# ===========================
@app.get("/dashboard", response_class=FileResponse)
async def get_upload_page():
    """Serve the HTML upload interface"""
    html_path = os.path.join(os.path.dirname(__file__), "DashBoard.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        return HTMLResponse(
            content="<h1>Upload interface not found</h1><p>Please ensure index.html exists in the project directory.</p>", 
            status_code=404
        )
@app.get("/", response_class=FileResponse)
async def get_upload_page():
    """Serve the HTML upload interface"""
    html_path = os.path.join(os.path.dirname(__file__), "home.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        return HTMLResponse(
            content="<h1>Upload interface not found</h1><p>Please ensure index.html exists in the project directory.</p>", 
            status_code=404
        )

@app.get("/health")
async def health_check():
    """Health check and engine status endpoint"""
    return {
        "status": "healthy",
        "engines": {
            "paddleocr": {
                "available": PADDLEOCR_AVAILABLE,
                "status": "ready" if PADDLEOCR_AVAILABLE else "unavailable"
            },
            "vietocr": {
                "available": VIETOCR_AVAILABLE,
                "status": "ready" if VIETOCR_AVAILABLE else "unavailable"
            }
        },
        "endpoints": {
            "paddleocr": [
                "/api/paddleocr/full-image",
                "/api/paddleocr/bboxes",
                "/api/paddleocr/single-bbox"
            ],
            "vietocr": [
                "/api/vietocr/full-image", 
                "/api/vietocr/bboxes",
                "/api/vietocr/single-bbox"
            ]
        }
    }


aligner = ORBImageAligner(target_dimension=800, orb_features=2000)

@app.post('/api/orb')
async def orb(image_template: UploadFile = File(...), image_target: UploadFile = File(...)):
    try:
        template_img = read_image_from_upload(image_template)
        target_img = read_image_from_upload(image_target)
        result = aligner.align(template_img, target_img)
        json_result = prepare_response(result)
        return json_result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def read_image_from_upload(file: UploadFile):
    file_bytes = file.file.read()
    img_array = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img

def encode_image_to_base64(image):
    """Convert numpy image to base64 string"""
    _, buffer = cv2.imencode('.jpg', image)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return img_base64

def convert_numpy_types(obj):
    """Recursively convert numpy types to native Python types"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj

def prepare_response(result):
    """Convert ORB alignment result to JSON-serializable format"""
    if not result["success"]:
        return result
    
    # Convert numpy arrays to base64 encoded images
    response = {
        "success": True,
        "aligned_image_base64": encode_image_to_base64(result["aligned_image"]),
        "visualization_image_base64": encode_image_to_base64(result["visualization_image"]),
        "comparison_image_base64": encode_image_to_base64(result["comparison_image"]),
        "original_sizes": {
            "base": list(result["original_sizes"]["base"]),
            "target": list(result["original_sizes"]["target"])
        },
        "normalized_sizes": {
            "base": list(result["normalized_sizes"]["base"]),
            "target": list(result["normalized_sizes"]["target"])
        },
        "features": convert_numpy_types(result["features"]),
        "good_matches": convert_numpy_types(result["good_matches"]),
        "inliers": convert_numpy_types(result["inliers"]),
        "inlier_ratio": float(result["inlier_ratio"]),
        "quality_score": float(result["quality_score"]),
        "homography_matrix": result["homography_matrix"].tolist(),
        "scales": {
            "base_scale": float(result["scales"]["base_scale"]),
            "target_scale": float(result["scales"]["target_scale"])
        }
    }
    return response

# ===========================
# PADDLEOCR API ENDPOINTS
# ===========================

@app.post("/api/paddleocr/full-image")
async def paddleocr_process_full_image(file: UploadFile = File(...)):
    """
    Process entire image using PaddleOCR (detection + recognition)
    
    Returns:
    - texts: List of recognized texts
    - confidences: List of confidence scores
    - bboxes: List of bounding boxes (polygon format)
    - count: Number of text regions found
    """
    if not PADDLEOCR_AVAILABLE:
        raise HTTPException(status_code=503, detail="PaddleOCR engine not available")
    
    try:
        # Decode image
        image_data = await file.read()
        image = decode_image_to_cv2(image_data)
        
        # Process with PaddleOCR
        result = paddle_ocr_processor.process_full_image(image)
        
        return JSONResponse(content=standardize_response(
            success=True,
            engine="PaddleOCR",
            data={
                "texts": result["texts"],
                "confidences": result["confidences"], 
                "bboxes": result["bboxes"],
                "count": result["count"]
            }
        ))
        
    except Exception as e:
        return JSONResponse(
            content=standardize_response(
                success=False,
                engine="PaddleOCR",
                error=f"Processing failed: {str(e)}"
            ),
            status_code=500
        )

@app.post("/api/paddleocr/bboxes")
async def paddleocr_process_bboxes(
    file: UploadFile = File(...),
    bboxes: str = Form(...),
    bbox_format: str = Form(default="xyxy")
):
    """
    Process specific bounding boxes using PaddleOCR recognition
    
    Args:
    - bboxes: JSON string of bbox coordinates
    - bbox_format: "xyxy", "polygon", or "yolo"
    
    Returns:
    - results: List of results for each bbox
    """
    if not PADDLEOCR_AVAILABLE:
        raise HTTPException(status_code=503, detail="PaddleOCR engine not available")
    
    try:
        # Decode image and parse bboxes
        image_data = await file.read()
        image = decode_image_to_cv2(image_data)
        bboxes_list = parse_bboxes(bboxes)
        
        # Process with PaddleOCR
        results = paddle_ocr_processor.process_multiple_bboxes(image, bboxes_list, bbox_format)
        
        return JSONResponse(content=standardize_response(
            success=True,
            engine="PaddleOCR",
            data={"results": results}
        ))
        
    except Exception as e:
        return JSONResponse(
            content=standardize_response(
                success=False,
                engine="PaddleOCR", 
                error=f"Processing failed: {str(e)}"
            ),
            status_code=500
        )

@app.post("/api/paddleocr/single-bbox")
async def paddleocr_process_single_bbox(
    file: UploadFile = File(...),
    bbox: str = Form(...),
    bbox_format: str = Form(default="xyxy")
):
    """
    Process single bounding box using PaddleOCR recognition
    
    Args:
    - bbox: JSON string of bbox coordinates  
    - bbox_format: "xyxy", "polygon", or "yolo"
    
    Returns:
    - text: Recognized text
    - confidence: Confidence score
    - bbox: Processed bbox coordinates
    """
    if not PADDLEOCR_AVAILABLE:
        raise HTTPException(status_code=503, detail="PaddleOCR engine not available")
    
    try:
        # Decode image and parse bbox
        image_data = await file.read()
        image = decode_image_to_cv2(image_data)
        bbox_data = json.loads(bbox)
        
        # Process with PaddleOCR
        result = paddle_ocr_processor.process_bbox(image, bbox_data, bbox_format)
        
        return JSONResponse(content=standardize_response(
            success=True,
            engine="PaddleOCR",
            data={
                "text": result["text"],
                "confidence": result["confidence"],
                "bbox": result["bbox"]
            }
        ))
        
    except Exception as e:
        return JSONResponse(
            content=standardize_response(
                success=False,
                engine="PaddleOCR",
                error=f"Processing failed: {str(e)}"
            ),
            status_code=500
        )

# ===========================
# VIETOCR API ENDPOINTS  
# ===========================

@app.post("/api/vietocr/full-image")
async def vietocr_process_full_image(file: UploadFile = File(...)):
    """
    Process entire image using VietOCR (recognition only)
    
    Returns:
    - texts: List with single recognized text
    - confidences: List with confidence (always 1.0)
    - bboxes: Empty list (no detection)
    - count: 1 if text found, 0 otherwise
    """
    if not VIETOCR_AVAILABLE:
        raise HTTPException(status_code=503, detail="VietOCR engine not available")
    
    try:
        # Decode image
        image_data = await file.read()
        image = decode_image_to_pil(image_data)
        
        # Process with VietOCR
        result = viet_ocr_processor.process_full_image(image)
        
        return JSONResponse(content=standardize_response(
            success=True,
            engine="VietOCR",
            data={
                "texts": result["texts"],
                "confidences": result["confidences"],
                "bboxes": result["bboxes"],
                "count": result["count"]
            }
        ))
        
    except Exception as e:
        return JSONResponse(
            content=standardize_response(
                success=False,
                engine="VietOCR",
                error=f"Processing failed: {str(e)}"
            ),
            status_code=500
        )

@app.post("/api/vietocr/bboxes")
async def vietocr_process_bboxes(
    file: UploadFile = File(...),
    bboxes: str = Form(...),
    bbox_format: str = Form(default="xyxy")
):
    """
    Process specific bounding boxes using VietOCR recognition
    
    Args:
    - bboxes: JSON string of bbox coordinates
    - bbox_format: "xyxy", "polygon", or "yolo"
    
    Returns:
    - results: List of results for each bbox
    """
    if not VIETOCR_AVAILABLE:
        raise HTTPException(status_code=503, detail="VietOCR engine not available")
    
    try:
        # Decode image and parse bboxes
        image_data = await file.read()
        image = decode_image_to_pil(image_data)
        bboxes_list = parse_bboxes(bboxes)
        
        # Process with VietOCR
        results = viet_ocr_processor.process_multiple_bboxes(image, bboxes_list, bbox_format)
        
        return JSONResponse(content=standardize_response(
            success=True,
            engine="VietOCR",
            data={"results": results}
        ))
        
    except Exception as e:
        return JSONResponse(
            content=standardize_response(
                success=False,
                engine="VietOCR",
                error=f"Processing failed: {str(e)}"
            ),
            status_code=500
        )

@app.post("/api/vietocr/single-bbox")
async def vietocr_process_single_bbox(
    file: UploadFile = File(...),
    bbox: str = Form(...),
    bbox_format: str = Form(default="xyxy")
):
    """
    Process single bounding box using VietOCR recognition
    
    Args:
    - bbox: JSON string of bbox coordinates
    - bbox_format: "xyxy", "polygon", or "yolo"
    
    Returns:
    - text: Recognized text
    - confidence: Confidence score (always 1.0)
    - bbox: Processed bbox coordinates
    """
    if not VIETOCR_AVAILABLE:
        raise HTTPException(status_code=503, detail="VietOCR engine not available")
    
    try:
        # Decode image and parse bbox
        image_data = await file.read()
        image = decode_image_to_pil(image_data)
        bbox_data = json.loads(bbox)
        
        # Process with VietOCR
        result = viet_ocr_processor.process_bbox(image, bbox_data, bbox_format)
        
        return JSONResponse(content=standardize_response(
            success=True,
            engine="VietOCR",
            data={
                "text": result["text"],
                "confidence": result["confidence"],
                "bbox": result["bbox"]
            }
        ))
        
    except Exception as e:
        return JSONResponse(
            content=standardize_response(
                success=False,
                engine="VietOCR",
                error=f"Processing failed: {str(e)}"
            ),
            status_code=500
        )

# ===========================
# LEGACY ENDPOINTS (Backward Compatibility)
# ===========================

@app.post("/process-full-image")
async def legacy_process_full_image(file: UploadFile = File(...)):
    """Legacy endpoint - redirects to PaddleOCR full image processing"""
    if PADDLEOCR_AVAILABLE:
        return await paddleocr_process_full_image(file)
    else:
        raise HTTPException(status_code=503, detail="PaddleOCR engine not available")

@app.post("/process-bboxes")
async def legacy_process_bboxes(
    file: UploadFile = File(...),
    bboxes: str = Form(...),
    bbox_format: str = Form(default="xyxy")
):
    """Legacy endpoint - redirects to PaddleOCR bbox processing"""
    if PADDLEOCR_AVAILABLE:
        return await paddleocr_process_bboxes(file, bboxes, bbox_format)
    else:
        raise HTTPException(status_code=503, detail="PaddleOCR engine not available")

# ===========================
# STATISTICS SCHEDULER
# ===========================

# Initialize Statistics Scheduler
statistics_scheduler = None
try:
    from service.statistics.scheduler import get_scheduler
    statistics_scheduler = get_scheduler()
    print("✓ Statistics Scheduler loaded")
except Exception as e:
    print(f"✗ Statistics Scheduler failed to load: {e}")

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    if statistics_scheduler:
        try:
            statistics_scheduler.start()
            print("✓ Statistics Scheduler started")
        except Exception as e:
            print(f"✗ Failed to start Statistics Scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on application shutdown"""
    if statistics_scheduler:
        try:
            statistics_scheduler.stop()
            print("✓ Statistics Scheduler stopped")
        except Exception as e:
            print(f"✗ Failed to stop Statistics Scheduler: {e}")

@app.get("/api/statistics/status")
async def get_statistics_status():
    """Get scheduler status and scheduled jobs"""
    if not statistics_scheduler:
        return {"status": "unavailable", "message": "Statistics scheduler not initialized"}
    
    return {
        "status": "running" if statistics_scheduler.is_running else "stopped",
        "jobs": statistics_scheduler.get_jobs()
    }

@app.post("/api/statistics/update")
async def trigger_statistics_update():
    """Manually trigger statistics update"""
    if not statistics_scheduler:
        raise HTTPException(status_code=503, detail="Statistics scheduler not available")
    
    try:
        statistics_scheduler.run_now()
        return {"status": "success", "message": "Statistics update triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger update: {str(e)}")

# ===========================
# MAIN APPLICATION
# ===========================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Multi-Engine OCR API Server v2.0")
    print("=" * 60)
    
    # Engine status
    print("📊 Engine Status:")
    print(f"  ✓ PaddleOCR: {'Available' if PADDLEOCR_AVAILABLE else 'Not Available'}")
    print(f"  ✓ VietOCR:   {'Available' if VIETOCR_AVAILABLE else 'Not Available'}")
    print()
    
    # API endpoints
    print("🔗 API Endpoints:")
    print("  📊 System:")
    print("    GET  /                    - Upload interface")
    print("    GET  /health              - Health check & status")
    print("    GET  /docs                - API documentation")
    print()
    
    if PADDLEOCR_AVAILABLE:
        print("  🔥 PaddleOCR APIs:")
        print("    POST /api/paddleocr/full-image   - Full image processing")
        print("    POST /api/paddleocr/bboxes       - Multiple bbox processing")
        print("    POST /api/paddleocr/single-bbox  - Single bbox processing")
        print()
    
    if VIETOCR_AVAILABLE:
        print("  🇻🇳 VietOCR APIs:")
        print("    POST /api/vietocr/full-image     - Full image processing")
        print("    POST /api/vietocr/bboxes         - Multiple bbox processing")
        print("    POST /api/vietocr/single-bbox    - Single bbox processing")
        print()
    
    print("  ⚡ Legacy APIs (PaddleOCR):")
    print("    POST /process-full-image         - Legacy full image")
    print("    POST /process-bboxes             - Legacy bbox processing")
    print()
    
    print("  ⏰ Statistics APIs:")
    print("    GET  /api/statistics/status     - Scheduler status")
    print("    POST /api/statistics/update     - Trigger manual update")
    print()
    
    print("🌐 Access URLs:")
    print("  - Web Interface: http://localhost:5555")
    print("  - API Docs:      http://localhost:5555/docs")
    print("  - Health Check:  http://localhost:5555/health")
    print("  - Stats Status:  http://localhost:5555/api/statistics/status")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=5555, log_level="info")
