#!/usr/bin/env python3
"""
gRPC OCR Server
Provides OCR services via gRPC protocol
"""

import grpc
from concurrent import futures
import threading
import time
import io
import numpy as np
from PIL import Image
import cv2
import logging

# Import generated gRPC modules
import ocr_pb2
import ocr_pb2_grpc

# Import OCR processors
try:
    from PaddletOCRApi import PaddleOCRProcessor
    PADDLEOCR_AVAILABLE = True
except ImportError as e:
    print(f"PaddleOCR not available: {e}")
    PADDLEOCR_AVAILABLE = False

try:
    from VietOCRApi import VietOCRProcessor
    VIETOCR_AVAILABLE = True
except ImportError as e:
    print(f"VietOCR not available: {e}")
    VIETOCR_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRServiceImpl(ocr_pb2_grpc.OCRServiceServicer):
    """gRPC OCR Service Implementation"""
    
    def __init__(self):
        self.paddle_ocr = None
        self.viet_ocr = None
        
        # Initialize OCR engines
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize OCR engines"""
        if PADDLEOCR_AVAILABLE:
            try:
                self.paddle_ocr = PaddleOCRProcessor(weights_dir='weights')
                logger.info("✓ PaddleOCR engine initialized")
            except Exception as e:
                logger.error(f"✗ Failed to initialize PaddleOCR: {e}")
        
        if VIETOCR_AVAILABLE:
            try:
                self.viet_ocr = VietOCRProcessor()
                logger.info("✓ VietOCR engine initialized")
            except Exception as e:
                logger.error(f"✗ Failed to initialize VietOCR: {e}")
    
    def _decode_image(self, image_data: bytes):
        """Decode image data to appropriate format"""
        try:
            # For PaddleOCR (requires OpenCV format)
            image_pil = Image.open(io.BytesIO(image_data))
            if image_pil.mode != 'RGB':
                image_pil = image_pil.convert('RGB')
            
            # Convert to numpy array for OpenCV
            image_np = np.array(image_pil)
            image_cv2 = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            
            return image_cv2, image_pil
        except Exception as e:
            raise ValueError(f"Failed to decode image: {e}")
    
    def _convert_bbox_to_proto(self, bbox, bbox_format="polygon"):
        """Convert bbox to protobuf format"""
        proto_bbox = ocr_pb2.BoundingBox()
        
        if bbox_format == "polygon" and isinstance(bbox[0], (list, tuple)):
            # Polygon format [[x1,y1], [x2,y2], ...]
            polygon = ocr_pb2.PolygonBox()
            for point in bbox:
                proto_point = ocr_pb2.Point(x=float(point[0]), y=float(point[1]))
                polygon.points.append(proto_point)
            proto_bbox.polygon.CopyFrom(polygon)
        
        elif bbox_format == "xyxy" or len(bbox) == 4:
            # XYXY format [x1, y1, x2, y2]
            if isinstance(bbox[0], (list, tuple)):
                # Convert polygon to XYXY
                xs = [point[0] for point in bbox]
                ys = [point[1] for point in bbox]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
            else:
                x1, y1, x2, y2 = bbox
            
            xyxy = ocr_pb2.XYXYBox(x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2))
            proto_bbox.xyxy.CopyFrom(xyxy)
        
        return proto_bbox
    
    def _convert_proto_to_bbox(self, proto_bbox):
        """Convert protobuf bbox to Python format"""
        if proto_bbox.HasField('xyxy'):
            return [proto_bbox.xyxy.x1, proto_bbox.xyxy.y1, 
                   proto_bbox.xyxy.x2, proto_bbox.xyxy.y2]
        elif proto_bbox.HasField('polygon'):
            return [[point.x, point.y] for point in proto_bbox.polygon.points]
        elif proto_bbox.HasField('yolo'):
            return [proto_bbox.yolo.x_center, proto_bbox.yolo.y_center,
                   proto_bbox.yolo.width, proto_bbox.yolo.height]
        else:
            raise ValueError("Unknown bbox format in protobuf")
    
    def ProcessFullImage(self, request, context):
        """Process full image with specified engine"""
        try:
            # Decode image
            image_cv2, image_pil = self._decode_image(request.image_data)
            
            # Select engine
            if request.engine.lower() == "paddleocr":
                if not self.paddle_ocr:
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    context.set_details("PaddleOCR engine not available")
                    return ocr_pb2.ProcessFullImageResponse()
                
                # Process with PaddleOCR
                result = self.paddle_ocr.process_full_image(image_cv2)
                
            elif request.engine.lower() == "vietocr":
                if not self.viet_ocr:
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    context.set_details("VietOCR engine not available")
                    return ocr_pb2.ProcessFullImageResponse()
                
                # Process with VietOCR
                result = self.viet_ocr.process_full_image(image_pil)
                
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Unknown engine: {request.engine}")
                return ocr_pb2.ProcessFullImageResponse()
            
            # Convert results to protobuf
            response = ocr_pb2.ProcessFullImageResponse(
                success=True,
                engine=request.engine,
                texts=result["texts"],
                confidences=[float(c) for c in result["confidences"]],
                count=result["count"]
            )
            
            # Convert bboxes
            for bbox in result["bboxes"]:
                proto_bbox = self._convert_bbox_to_proto(bbox)
                response.bboxes.append(proto_bbox)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing full image: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ocr_pb2.ProcessFullImageResponse(
                success=False,
                error=str(e)
            )
    
    def ProcessSingleBbox(self, request, context):
        """Process single bounding box"""
        try:
            # Decode image
            image_cv2, image_pil = self._decode_image(request.image_data)
            
            # Convert bbox from protobuf
            bbox = self._convert_proto_to_bbox(request.bbox)
            
            # Select engine and image format
            if request.engine.lower() == "paddleocr":
                if not self.paddle_ocr:
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    context.set_details("PaddleOCR engine not available")
                    return ocr_pb2.ProcessSingleBboxResponse()
                
                result = self.paddle_ocr.process_bbox(image_cv2, bbox, request.bbox_format)
                
            elif request.engine.lower() == "vietocr":
                if not self.viet_ocr:
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    context.set_details("VietOCR engine not available")
                    return ocr_pb2.ProcessSingleBboxResponse()
                
                result = self.viet_ocr.process_bbox(image_pil, bbox, request.bbox_format)
                
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Unknown engine: {request.engine}")
                return ocr_pb2.ProcessSingleBboxResponse()
            
            # Convert result to protobuf
            response = ocr_pb2.ProcessSingleBboxResponse(
                success=True,
                engine=request.engine,
                text=result["text"],
                confidence=float(result["confidence"]),
                bbox=self._convert_bbox_to_proto(result["bbox"])
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing single bbox: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ocr_pb2.ProcessSingleBboxResponse(
                success=False,
                error=str(e)
            )
    
    def ProcessBboxes(self, request, context):
        """Process multiple bounding boxes"""
        try:
            # Decode image
            image_cv2, image_pil = self._decode_image(request.image_data)
            
            # Convert bboxes from protobuf
            bboxes = [self._convert_proto_to_bbox(bbox) for bbox in request.bboxes]
            
            # Select engine
            if request.engine.lower() == "paddleocr":
                if not self.paddle_ocr:
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    context.set_details("PaddleOCR engine not available")
                    return ocr_pb2.ProcessBboxesResponse()
                
                results = self.paddle_ocr.process_multiple_bboxes(image_cv2, bboxes, request.bbox_format)
                
            elif request.engine.lower() == "vietocr":
                if not self.viet_ocr:
                    context.set_code(grpc.StatusCode.UNAVAILABLE)
                    context.set_details("VietOCR engine not available")
                    return ocr_pb2.ProcessBboxesResponse()
                
                results = self.viet_ocr.process_multiple_bboxes(image_pil, bboxes, request.bbox_format)
                
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Unknown engine: {request.engine}")
                return ocr_pb2.ProcessBboxesResponse()
            
            # Convert results to protobuf
            response = ocr_pb2.ProcessBboxesResponse(
                success=True,
                engine=request.engine
            )
            
            for result in results:
                bbox_result = ocr_pb2.BboxResult(
                    text=result["text"],
                    confidence=float(result["confidence"]),
                    bbox=self._convert_bbox_to_proto(result["bbox"]),
                    bbox_index=result.get("bbox_index", -1)
                )
                response.results.append(bbox_result)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing bboxes: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ocr_pb2.ProcessBboxesResponse(
                success=False,
                error=str(e)
            )
    
    def GetEngineStatus(self, request, context):
        """Get engine status"""
        response = ocr_pb2.EngineStatusResponse()
        
        # PaddleOCR status
        paddle_info = ocr_pb2.EngineInfo(
            available=self.paddle_ocr is not None,
            status="ready" if self.paddle_ocr else "unavailable",
            version="2.7.0"  # Could be dynamic
        )
        response.engines["paddleocr"].CopyFrom(paddle_info)
        
        # VietOCR status
        viet_info = ocr_pb2.EngineInfo(
            available=self.viet_ocr is not None,
            status="ready" if self.viet_ocr else "unavailable",
            version="0.3.8"  # Could be dynamic
        )
        response.engines["vietocr"].CopyFrom(viet_info)
        
        return response
    
    def HealthCheck(self, request, context):
        """Health check"""
        response = ocr_pb2.HealthCheckResponse(status="healthy")
        
        # Add engine info
        engine_status = self.GetEngineStatus(request, context)
        for engine_name, engine_info in engine_status.engines.items():
            response.engines[engine_name].CopyFrom(engine_info)
        
        return response

def serve(port=50051):
    """Start gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add OCR service
    ocr_service = OCRServiceImpl()
    ocr_pb2_grpc.add_OCRServiceServicer_to_server(ocr_service, server)
    
    # Configure server
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    # Start server
    server.start()
    
    logger.info("=" * 60)
    logger.info("🚀 gRPC OCR Server Started")
    logger.info("=" * 60)
    logger.info(f"📡 Server listening on port: {port}")
    logger.info(f"📊 Engine Status:")
    logger.info(f"  ✓ PaddleOCR: {'Available' if PADDLEOCR_AVAILABLE else 'Not Available'}")
    logger.info(f"  ✓ VietOCR:   {'Available' if VIETOCR_AVAILABLE else 'Not Available'}")
    logger.info("=" * 60)
    
    try:
        while True:
            time.sleep(86400)  # Keep server alive
    except KeyboardInterrupt:
        logger.info("🛑 Stopping gRPC server...")
        server.stop(0)

if __name__ == "__main__":
    serve()
