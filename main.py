from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import base64
from service.orb.ORBImageAligner import ORBImageAligner
import uvicorn
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ORB Image Alignment API", version="1.0.0")
aligner = ORBImageAligner(target_dimension=800, orb_features=2000)

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

@app.get("/")
def read_root():
    # Serve the HTML file
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=5000)