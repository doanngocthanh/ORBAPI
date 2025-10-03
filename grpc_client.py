#!/usr/bin/env python3
"""
gRPC OCR Client
Demonstrates how to communicate with gRPC OCR Server
"""

import grpc
import io
from PIL import Image
import base64
import json
import time
import logging

# Import generated gRPC modules
import ocr_pb2
import ocr_pb2_grpc

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRGRPCClient:
    """gRPC Client for OCR Server"""
    
    def __init__(self, server_address="localhost:50051"):
        self.server_address = server_address
        self.channel = None
        self.stub = None
        
    def connect(self):
        """Connect to gRPC server"""
        try:
            self.channel = grpc.insecure_channel(self.server_address)
            self.stub = ocr_pb2_grpc.OCRServiceStub(self.channel)
            
            # Test connection with health check
            response = self.stub.HealthCheck(ocr_pb2.HealthCheckRequest())
            logger.info(f"✓ Connected to gRPC server at {self.server_address}")
            logger.info(f"📊 Server status: {response.status}")
            
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to server: {e}")
            return False
    
    def close(self):
        """Close connection"""
        if self.channel:
            self.channel.close()
            logger.info("📡 Connection closed")
    
    def load_image_from_file(self, image_path):
        """Load image from file and convert to bytes"""
        try:
            with open(image_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load image from {image_path}: {e}")
            return None
    
    def load_image_from_base64(self, base64_string):
        """Load image from base64 string"""
        try:
            # Remove data URL prefix if present
            if base64_string.startswith('data:image'):
                base64_string = base64_string.split(',')[1]
            
            return base64.b64decode(base64_string)
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            return None
    
    def process_full_image(self, image_data, engine="paddleocr"):
        """Process full image"""
        try:
            logger.info(f"🔍 Processing full image with {engine} engine...")
            
            request = ocr_pb2.ProcessFullImageRequest(
                image_data=image_data,
                engine=engine
            )
            
            response = self.stub.ProcessFullImage(request)
            
            if response.success:
                logger.info(f"✓ OCR completed successfully!")
                logger.info(f"📝 Found {response.count} text regions")
                
                result = {
                    "success": True,
                    "engine": response.engine,
                    "count": response.count,
                    "texts": list(response.texts),
                    "confidences": list(response.confidences),
                    "bboxes": []
                }
                
                # Convert bboxes
                for bbox in response.bboxes:
                    if bbox.HasField('xyxy'):
                        result["bboxes"].append([
                            bbox.xyxy.x1, bbox.xyxy.y1,
                            bbox.xyxy.x2, bbox.xyxy.y2
                        ])
                    elif bbox.HasField('polygon'):
                        result["bboxes"].append([
                            [point.x, point.y] for point in bbox.polygon.points
                        ])
                
                return result
            else:
                logger.error(f"✗ OCR failed: {response.error}")
                return {"success": False, "error": response.error}
                
        except grpc.RpcError as e:
            logger.error(f"✗ gRPC error: {e.code()} - {e.details()}")
            return {"success": False, "error": f"gRPC error: {e.details()}"}
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    def process_single_bbox(self, image_data, bbox, bbox_format="xyxy", engine="paddleocr"):
        """Process single bounding box"""
        try:
            logger.info(f"🔍 Processing single bbox with {engine} engine...")
            
            # Create bbox protobuf
            proto_bbox = ocr_pb2.BoundingBox()
            if bbox_format == "xyxy":
                xyxy = ocr_pb2.XYXYBox(x1=bbox[0], y1=bbox[1], x2=bbox[2], y2=bbox[3])
                proto_bbox.xyxy.CopyFrom(xyxy)
            elif bbox_format == "polygon":
                polygon = ocr_pb2.PolygonBox()
                for point in bbox:
                    proto_point = ocr_pb2.Point(x=point[0], y=point[1])
                    polygon.points.append(proto_point)
                proto_bbox.polygon.CopyFrom(polygon)
            
            request = ocr_pb2.ProcessSingleBboxRequest(
                image_data=image_data,
                bbox=proto_bbox,
                bbox_format=bbox_format,
                engine=engine
            )
            
            response = self.stub.ProcessSingleBbox(request)
            
            if response.success:
                logger.info(f"✓ OCR completed successfully!")
                logger.info(f"📝 Text: {response.text}")
                logger.info(f"📊 Confidence: {response.confidence:.2f}")
                
                return {
                    "success": True,
                    "engine": response.engine,
                    "text": response.text,
                    "confidence": response.confidence
                }
            else:
                logger.error(f"✗ OCR failed: {response.error}")
                return {"success": False, "error": response.error}
                
        except grpc.RpcError as e:
            logger.error(f"✗ gRPC error: {e.code()} - {e.details()}")
            return {"success": False, "error": f"gRPC error: {e.details()}"}
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    def process_multiple_bboxes(self, image_data, bboxes, bbox_format="xyxy", engine="paddleocr"):
        """Process multiple bounding boxes"""
        try:
            logger.info(f"🔍 Processing {len(bboxes)} bboxes with {engine} engine...")
            
            # Create bboxes protobuf
            proto_bboxes = []
            for bbox in bboxes:
                proto_bbox = ocr_pb2.BoundingBox()
                if bbox_format == "xyxy":
                    xyxy = ocr_pb2.XYXYBox(x1=bbox[0], y1=bbox[1], x2=bbox[2], y2=bbox[3])
                    proto_bbox.xyxy.CopyFrom(xyxy)
                elif bbox_format == "polygon":
                    polygon = ocr_pb2.PolygonBox()
                    for point in bbox:
                        proto_point = ocr_pb2.Point(x=point[0], y=point[1])
                        polygon.points.append(proto_point)
                    proto_bbox.polygon.CopyFrom(polygon)
                proto_bboxes.append(proto_bbox)
            
            request = ocr_pb2.ProcessBboxesRequest(
                image_data=image_data,
                bboxes=proto_bboxes,
                bbox_format=bbox_format,
                engine=engine
            )
            
            response = self.stub.ProcessBboxes(request)
            
            if response.success:
                logger.info(f"✓ OCR completed successfully!")
                logger.info(f"📝 Processed {len(response.results)} regions")
                
                results = []
                for result in response.results:
                    results.append({
                        "text": result.text,
                        "confidence": result.confidence,
                        "bbox_index": result.bbox_index
                    })
                
                return {
                    "success": True,
                    "engine": response.engine,
                    "results": results
                }
            else:
                logger.error(f"✗ OCR failed: {response.error}")
                return {"success": False, "error": response.error}
                
        except grpc.RpcError as e:
            logger.error(f"✗ gRPC error: {e.code()} - {e.details()}")
            return {"success": False, "error": f"gRPC error: {e.details()}"}
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_engine_status(self):
        """Get engine status"""
        try:
            response = self.stub.GetEngineStatus(ocr_pb2.EngineStatusRequest())
            
            status = {}
            for engine_name, engine_info in response.engines.items():
                status[engine_name] = {
                    "available": engine_info.available,
                    "status": engine_info.status,
                    "version": engine_info.version
                }
            
            return status
        except Exception as e:
            logger.error(f"Failed to get engine status: {e}")
            return {}
    
    def health_check(self):
        """Perform health check"""
        try:
            response = self.stub.HealthCheck(ocr_pb2.HealthCheckRequest())
            return {
                "status": response.status,
                "engines": dict(response.engines)
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

def demo_client():
    """Demo function showing how to use the client"""
    
    logger.info("=" * 60)
    logger.info("🚀 gRPC OCR Client Demo")
    logger.info("=" * 60)
    
    # Create client
    client = OCRGRPCClient("localhost:50051")
    
    # Connect to server
    if not client.connect():
        logger.error("Failed to connect to server")
        return
    
    try:
        # Health check
        logger.info("\n📊 Health Check:")
        health = client.health_check()
        logger.info(f"Status: {health['status']}")
        
        # Engine status
        logger.info("\n🔧 Engine Status:")
        engines = client.get_engine_status()
        for name, info in engines.items():
            status = "✓" if info["available"] else "✗"
            logger.info(f"  {status} {name}: {info['status']} (v{info['version']})")
        
        # Demo image processing (you need to provide an actual image)
        # Example with a test image file:
        """
        image_path = "test_image.jpg"
        if os.path.exists(image_path):
            logger.info(f"\n🖼️  Processing test image: {image_path}")
            
            # Load image
            image_data = client.load_image_from_file(image_path)
            if image_data:
                # Process full image
                result = client.process_full_image(image_data, engine="paddleocr")
                if result["success"]:
                    logger.info(f"Found {result['count']} text regions")
                    for i, text in enumerate(result['texts']):
                        logger.info(f"  {i+1}. {text} (confidence: {result['confidences'][i]:.2f})")
                
                # Process single bbox
                if result["success"] and result["bboxes"]:
                    logger.info("\n🎯 Processing first detected region:")
                    bbox_result = client.process_single_bbox(
                        image_data, 
                        result["bboxes"][0], 
                        bbox_format="xyxy",
                        engine="vietocr"
                    )
                    if bbox_result["success"]:
                        logger.info(f"Text: {bbox_result['text']}")
                        logger.info(f"Confidence: {bbox_result['confidence']:.2f}")
        """
        
        logger.info("\n✓ Demo completed successfully!")
        
    finally:
        # Close connection
        client.close()

if __name__ == "__main__":
    demo_client()
