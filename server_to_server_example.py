#!/usr/bin/env python3
"""
Example: Using gRPC for Server-to-Server Communication
Demonstrates how to use gRPC OCR Server in a distributed system
"""

import asyncio
import aiohttp
from aiohttp import web
import json
import logging
import time
import io
import base64
from PIL import Image

# Import gRPC client
from grpc_client import OCRGRPCClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRAPIGateway:
    """
    API Gateway that uses gRPC OCR Server for processing
    This demonstrates server-to-server communication via gRPC
    """
    
    def __init__(self, grpc_server_address="localhost:50051"):
        self.grpc_client = OCRGRPCClient(grpc_server_address)
        self.connected = False
    
    async def startup(self):
        """Connect to gRPC server on startup"""
        self.connected = self.grpc_client.connect()
        if self.connected:
            logger.info("✓ API Gateway connected to gRPC OCR Server")
        else:
            logger.error("✗ Failed to connect to gRPC OCR Server")
    
    async def cleanup(self):
        """Cleanup on shutdown"""
        self.grpc_client.close()
        logger.info("📡 API Gateway disconnected from gRPC server")
    
    def _decode_base64_image(self, base64_string):
        """Decode base64 image to bytes"""
        try:
            if base64_string.startswith('data:image'):
                base64_string = base64_string.split(',')[1]
            return base64.b64decode(base64_string)
        except Exception as e:
            raise ValueError(f"Invalid base64 image: {e}")
    
    async def process_ocr_request(self, request):
        """Process OCR request via gRPC"""
        if not self.connected:
            return web.json_response({
                "success": False,
                "error": "gRPC server not available"
            }, status=503)
        
        try:
            data = await request.json()
            
            # Extract parameters
            image_data_b64 = data.get('image')
            engine = data.get('engine', 'paddleocr')
            operation = data.get('operation', 'full_image')
            
            if not image_data_b64:
                return web.json_response({
                    "success": False,
                    "error": "No image provided"
                }, status=400)
            
            # Decode image
            image_data = self._decode_base64_image(image_data_b64)
            
            # Process based on operation type
            if operation == 'full_image':
                result = self.grpc_client.process_full_image(image_data, engine)
                
            elif operation == 'single_bbox':
                bbox = data.get('bbox')
                bbox_format = data.get('bbox_format', 'xyxy')
                
                if not bbox:
                    return web.json_response({
                        "success": False,
                        "error": "No bbox provided for single_bbox operation"
                    }, status=400)
                
                result = self.grpc_client.process_single_bbox(
                    image_data, bbox, bbox_format, engine
                )
                
            elif operation == 'multiple_bboxes':
                bboxes = data.get('bboxes')
                bbox_format = data.get('bbox_format', 'xyxy')
                
                if not bboxes:
                    return web.json_response({
                        "success": False,
                        "error": "No bboxes provided for multiple_bboxes operation"
                    }, status=400)
                
                result = self.grpc_client.process_multiple_bboxes(
                    image_data, bboxes, bbox_format, engine
                )
                
            else:
                return web.json_response({
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }, status=400)
            
            return web.json_response(result)
            
        except ValueError as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error processing OCR request: {e}")
            return web.json_response({
                "success": False,
                "error": "Internal server error"
            }, status=500)
    
    async def get_engine_status(self, request):
        """Get engine status via gRPC"""
        if not self.connected:
            return web.json_response({
                "connected": False,
                "error": "gRPC server not available"
            })
        
        try:
            engines = self.grpc_client.get_engine_status()
            return web.json_response({
                "connected": True,
                "engines": engines
            })
        except Exception as e:
            return web.json_response({
                "connected": False,
                "error": str(e)
            })
    
    async def health_check(self, request):
        """Health check endpoint"""
        if not self.connected:
            return web.json_response({
                "status": "unhealthy",
                "grpc_connected": False
            }, status=503)
        
        try:
            health = self.grpc_client.health_check()
            return web.json_response({
                "status": "healthy",
                "grpc_connected": True,
                "grpc_health": health
            })
        except Exception as e:
            return web.json_response({
                "status": "unhealthy",
                "grpc_connected": False,
                "error": str(e)
            }, status=503)

def create_app():
    """Create aiohttp application"""
    app = web.Application()
    
    # Create API Gateway
    gateway = OCRAPIGateway()
    app['gateway'] = gateway
    
    # Routes
    app.router.add_post('/api/ocr', gateway.process_ocr_request)
    app.router.add_get('/api/engines', gateway.get_engine_status)
    app.router.add_get('/health', gateway.health_check)
    
    # Static files for demo frontend
    app.router.add_get('/', index_handler)
    
    # Startup/cleanup
    app.on_startup.append(startup_handler)
    app.on_cleanup.append(cleanup_handler)
    
    return app

async def startup_handler(app):
    """Startup handler"""
    await app['gateway'].startup()

async def cleanup_handler(app):
    """Cleanup handler"""
    await app['gateway'].cleanup()

async def index_handler(request):
    """Serve demo page"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>gRPC OCR API Gateway Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        button { padding: 10px 20px; margin: 5px; cursor: pointer; }
        .success { color: green; }
        .error { color: red; }
        .result { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 3px; }
        input[type="file"] { margin: 10px 0; }
        select { padding: 5px; margin: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 gRPC OCR API Gateway Demo</h1>
        <p>This demo shows how to use gRPC for server-to-server communication.</p>
        
        <div class="section">
            <h3>📊 Server Status</h3>
            <button onclick="checkHealth()">Check Health</button>
            <button onclick="getEngineStatus()">Get Engine Status</button>
            <div id="status-result"></div>
        </div>
        
        <div class="section">
            <h3>🖼️ OCR Processing</h3>
            <input type="file" id="imageInput" accept="image/*">
            <br>
            <select id="engineSelect">
                <option value="paddleocr">PaddleOCR</option>
                <option value="vietocr">VietOCR</option>
            </select>
            <select id="operationSelect">
                <option value="full_image">Full Image</option>
                <option value="single_bbox">Single BBox</option>
                <option value="multiple_bboxes">Multiple BBoxes</option>
            </select>
            <br>
            <button onclick="processImage()">Process Image</button>
            <div id="ocr-result"></div>
        </div>
        
        <div class="section">
            <h3>📝 Example API Usage</h3>
            <pre id="api-example">
# Example: Process full image
curl -X POST http://localhost:8080/api/ocr \\
  -H "Content-Type: application/json" \\
  -d '{
    "image": "data:image/jpeg;base64,...",
    "engine": "paddleocr",
    "operation": "full_image"
  }'

# Example: Process single bbox
curl -X POST http://localhost:8080/api/ocr \\
  -H "Content-Type: application/json" \\
  -d '{
    "image": "data:image/jpeg;base64,...",
    "engine": "vietocr",
    "operation": "single_bbox",
    "bbox": [100, 100, 300, 200],
    "bbox_format": "xyxy"
  }'
            </pre>
        </div>
    </div>

    <script>
        async function checkHealth() {
            try {
                const response = await fetch('/health');
                const data = await response.json();
                document.getElementById('status-result').innerHTML = 
                    `<div class="result ${data.status === 'healthy' ? 'success' : 'error'}">
                        Status: ${data.status}<br>
                        gRPC Connected: ${data.grpc_connected}
                    </div>`;
            } catch (error) {
                document.getElementById('status-result').innerHTML = 
                    `<div class="result error">Error: ${error.message}</div>`;
            }
        }

        async function getEngineStatus() {
            try {
                const response = await fetch('/api/engines');
                const data = await response.json();
                let html = '<div class="result">';
                if (data.connected) {
                    html += '<strong>Engine Status:</strong><br>';
                    for (const [name, info] of Object.entries(data.engines)) {
                        html += `${name}: ${info.available ? '✓' : '✗'} ${info.status} (v${info.version})<br>`;
                    }
                } else {
                    html += '<span class="error">gRPC server not connected</span>';
                }
                html += '</div>';
                document.getElementById('status-result').innerHTML = html;
            } catch (error) {
                document.getElementById('status-result').innerHTML = 
                    `<div class="result error">Error: ${error.message}</div>`;
            }
        }

        async function processImage() {
            const fileInput = document.getElementById('imageInput');
            const engine = document.getElementById('engineSelect').value;
            const operation = document.getElementById('operationSelect').value;
            
            if (!fileInput.files[0]) {
                alert('Please select an image file');
                return;
            }

            const file = fileInput.files[0];
            const reader = new FileReader();
            
            reader.onload = async function(e) {
                try {
                    const base64Image = e.target.result;
                    
                    const requestData = {
                        image: base64Image,
                        engine: engine,
                        operation: operation
                    };
                    
                    // Add example bbox for single_bbox operation
                    if (operation === 'single_bbox') {
                        requestData.bbox = [100, 100, 300, 200];
                        requestData.bbox_format = 'xyxy';
                    }
                    
                    // Add example bboxes for multiple_bboxes operation
                    if (operation === 'multiple_bboxes') {
                        requestData.bboxes = [
                            [100, 100, 300, 200],
                            [100, 250, 400, 350]
                        ];
                        requestData.bbox_format = 'xyxy';
                    }
                    
                    const response = await fetch('/api/ocr', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestData)
                    });
                    
                    const result = await response.json();
                    
                    let html = '<div class="result">';
                    if (result.success) {
                        html += '<span class="success">✓ OCR Success</span><br>';
                        html += `Engine: ${result.engine}<br>`;
                        
                        if (result.texts) {
                            html += `Found ${result.count} text regions:<br>`;
                            result.texts.forEach((text, i) => {
                                html += `${i+1}. ${text} (${result.confidences[i].toFixed(2)})<br>`;
                            });
                        }
                        
                        if (result.text) {
                            html += `Text: ${result.text}<br>`;
                            html += `Confidence: ${result.confidence.toFixed(2)}<br>`;
                        }
                        
                        if (result.results) {
                            html += `Processed ${result.results.length} regions:<br>`;
                            result.results.forEach((res, i) => {
                                html += `${i+1}. ${res.text} (${res.confidence.toFixed(2)})<br>`;
                            });
                        }
                    } else {
                        html += `<span class="error">✗ Error: ${result.error}</span>`;
                    }
                    html += '</div>';
                    
                    document.getElementById('ocr-result').innerHTML = html;
                    
                } catch (error) {
                    document.getElementById('ocr-result').innerHTML = 
                        `<div class="result error">Error: ${error.message}</div>`;
                }
            };
            
            reader.readAsDataURL(file);
        }
    </script>
</body>
</html>
    """
    return web.Response(text=html_content, content_type='text/html')

if __name__ == "__main__":
    # Create app
    app = create_app()
    
    logger.info("=" * 60)
    logger.info("🚀 OCR API Gateway (gRPC Client)")
    logger.info("=" * 60)
    logger.info("📡 Starting API Gateway on http://localhost:8080")
    logger.info("🔗 Connects to gRPC OCR Server on localhost:50051")
    logger.info("=" * 60)
    
    # Run server
    web.run_app(app, host='localhost', port=8080)
