import os
import cv2
import numpy as np
import re
from typing import Optional, List, Dict, Any, Union
from dataclasses import is_dataclass
from service.yolo.YOLODetector import YOLODetector, Detection
from service.ocr.PaddletOCRApi import PaddleOCRProcessor
from config import PtConfig


class MRZExtractor:
    """
    Service class for extracting MRZ (Machine Readable Zone) text from images.
    Uses YOLO for MRZ region detection and PaddleOCR for text recognition.
    """
    
    def __init__(self, model_name: str = "MRZ.pt"):
        """
        Initialize MRZ extractor with model path.
        
        Args:
            model_name: Name of the YOLO model file (default: "MRZ.pt")
        """
        self.pt_config = PtConfig()

        self.model_path = self.pt_config.get_model("MRZ")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"MRZ model not found at {self.model_path}")

        self.detector = YOLODetector(self.model_path)
        self.ocr = PaddleOCRProcessor()
    
    def extract_mrz_from_image(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract MRZ text from image.
        
        Args:
            image: Input image as numpy array (BGR format)
            
        Returns:
            Dictionary containing:
            - status: success/no_mrz_detected/ocr_failed
            - message: Status message
            - texts: List of individual text elements found
            - mrz_string: Combined MRZ string
            - mrz_length: Length of MRZ string
            - total_mrz_regions: Number of MRZ regions detected
        """
        try:

            # Detect MRZ regions using YOLO
            yolo_result = self.detector.detect(image)
            if isinstance(yolo_result, dict) and 'detections' in yolo_result:
                detections = yolo_result['detections']
            elif isinstance(yolo_result, list):
                detections = yolo_result
            else:
                detections = []

            if not detections:
                return {
                    "status": "no_mrz_detected",
                    "message": "No MRZ regions detected in the image.",
                    "texts": [],
                    "mrz_string": "",
                    "mrz_length": 0,
                    "total_mrz_regions": 0,
                    "dates_found": [],
                    "total_dates": 0
                }
            
            # Process full image with OCR
            print("Processing full image with OCR...")
            ocr_result = self.ocr.process_full_image(image)
            
            if not ocr_result or not isinstance(ocr_result, dict):
                return {
                    "status": "ocr_failed",
                    "message": "OCR processing failed.",
                    "texts": [],
                    "mrz_string": "",
                    "mrz_length": 0,
                    "total_mrz_regions": len(detections),
                    "dates_found": [],
                    "total_dates": 0
                }
            
            # Extract OCR results - PaddleOCR returns 'bboxes' not 'text_regions'
            text_regions = ocr_result.get('bboxes', ocr_result.get('text_regions', []))
            recognized_texts = ocr_result.get('texts', [])
            print(f"OCR found {len(text_regions)} text regions with {len(recognized_texts)} recognized texts")
            
            # Handle PaddleOCR result structure
            actual_texts = self._extract_texts_from_ocr_result(recognized_texts)
            
            # Create OCR detections for processing
            ocr_detections = self._create_ocr_detections(text_regions, actual_texts)
            print(f"Created {len(ocr_detections)} valid OCR detections")
            
            # Find texts within MRZ regions
            all_mrz_texts = self._find_texts_in_mrz_regions(detections, ocr_detections)
            
            # Generate final MRZ string
            mrz_string = self._generate_mrz_string(all_mrz_texts)
            
            # Extract dates from ALL OCR texts (not just MRZ region texts)
            all_ocr_texts = [det.get('text', '') for det in ocr_detections if det.get('text')]
            dates_found = self.extract_dates_from_all_texts(all_ocr_texts)
            
            return {
                "status": "success",
                "message": f"Found {len(all_mrz_texts)} MRZ text lines",
                "texts": all_mrz_texts,
                "mrz_string": mrz_string,
                "mrz_length": len(mrz_string),
                "total_mrz_regions": len(detections),
                "dates_found": dates_found,
                "total_dates": len(dates_found),
                "all_ocr_texts": all_ocr_texts  # For debugging
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing image: {str(e)}",
                "texts": [],
                "mrz_string": "",
                "mrz_length": 0,
                "total_mrz_regions": 0,
                "dates_found": [],
                "total_dates": 0
            }
    
    def extract_mrz_from_file_path(self, image_path: str) -> Dict[str, Any]:
        """
        Extract MRZ text from image file path.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with extraction results
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {
                    "status": "error",
                    "message": "Could not load image from path",
                    "texts": [],
                    "mrz_string": "",
                    "mrz_length": 0,
                    "total_mrz_regions": 0,
                    "dates_found": [],
                    "total_dates": 0
                }
            
            return self.extract_mrz_from_image(image)
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error loading image: {str(e)}",
                "texts": [],
                "mrz_string": "",
                "mrz_length": 0,
                "total_mrz_regions": 0,
                "dates_found": [],
                "total_dates": 0
            }
    
    def extract_mrz_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract MRZ text from image bytes.
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Dictionary with extraction results
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return {
                    "status": "error",
                    "message": "Invalid image data or corrupted bytes",
                    "texts": [],
                    "mrz_string": "",
                    "mrz_length": 0,
                    "total_mrz_regions": 0,
                    "dates_found": [],
                    "total_dates": 0
                }
            
            return self.extract_mrz_from_image(image)
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing image bytes: {str(e)}",
                "texts": [],
                "mrz_string": "",
                "mrz_length": 0,
                "total_mrz_regions": 0,
                "dates_found": [],
                "total_dates": 0
            }
    
    def _extract_texts_from_ocr_result(self, recognized_texts) -> List[str]:
        """Extract actual text list from OCR result structure."""
        actual_texts = []
        
        if isinstance(recognized_texts, tuple) and len(recognized_texts) == 2:
            # Case: (text_list, confidence_list)
            text_list, confidence_list = recognized_texts
            if isinstance(text_list, list):
                actual_texts = text_list
            print(f"Extracted {len(actual_texts)} texts from tuple structure")
        elif isinstance(recognized_texts, list):
            # Case: direct list of texts
            actual_texts = recognized_texts
            print(f"Using direct list of {len(actual_texts)} texts")
        else:
            print(f"Unexpected text structure: {type(recognized_texts)}")
            actual_texts = []
        
        return actual_texts
    
    def _create_ocr_detections(self, text_regions: List, actual_texts: List[str]) -> List[Dict]:
        """Create structured OCR detections from regions and texts."""
        ocr_detections = []
        min_length = min(len(text_regions), len(actual_texts))
        print(f"Processing {min_length} matched text regions/texts pairs")
        
        for i in range(min_length):
            try:
                bbox = text_regions[i]
                text_item = actual_texts[i]
                
                # Check if bbox is valid (handle numpy arrays and lists)
                bbox_valid = False
                if isinstance(bbox, np.ndarray):
                    bbox_valid = bbox.size > 0
                elif isinstance(bbox, list):
                    bbox_valid = len(bbox) > 0
                else:
                    bbox_valid = bbox is not None
                
                if bbox_valid and text_item:
                    # Handle case where text_item might be a list or string
                    if isinstance(text_item, list):
                        text_content = ' '.join(str(t) for t in text_item if t) if text_item else ''
                    else:
                        text_content = str(text_item)
                    
                    if text_content.strip():
                        # Process text for MRZ patterns
                        text_lines = self._process_text_for_mrz_patterns(text_content)
                        
                        # Add detections
                        if len(text_lines) > 1:
                            for j, line in enumerate(text_lines):
                                if line.strip():
                                    ocr_detections.append({
                                        'bbox': bbox,
                                        'text': line.strip(),
                                        'confidence': 1.0
                                    })
                                    print(f"OCR Detection {i}.{j}: '{line.strip()[:100]}...' at {bbox}")
                        else:
                            ocr_detections.append({
                                'bbox': bbox,
                                'text': text_content.strip(),
                                'confidence': 1.0
                            })
                            print(f"OCR Detection {i}: '{text_content.strip()[:100]}...' at {bbox}")
            except Exception as e:
                print(f"Error processing OCR detection {i}: {str(e)} - text_item type: {type(actual_texts[i])}, bbox type: {type(text_regions[i])}")
                continue
        
        return ocr_detections
    
    def _process_text_for_mrz_patterns(self, text_content: str) -> List[str]:
        """Process text content to extract MRZ patterns."""
        try:
            text_lines = []
            
            # Ensure text_content is a string
            text_content = str(text_content)
            
            # Split by common separators
            raw_lines = re.split(r'[\n\r]|(?=[A-Z]{2}[A-Z0-9<]{20,})', text_content)
            
            for line in raw_lines:
                line = line.strip()
                if line:
                    # Check if line looks like MRZ
                    if re.match(r'[A-Z0-9<]{20,}', line) or '<<' in line:
                        text_lines.append(line)
                    elif len(line) > 100:  # Long text might contain multiple MRZ lines
                        # Extract MRZ patterns from long text
                        mrz_patterns = re.findall(r'[A-Z0-9<]{20,}|[A-Z]+<<[A-Z<]*', line)
                        text_lines.extend(mrz_patterns)
                    else:
                        text_lines.append(line)
            
            return text_lines if text_lines else [text_content]
        except Exception as e:
            print(f"Error in _process_text_for_mrz_patterns: {str(e)}")
            return [str(text_content)]
    
    def _bbox_overlap(self, text_bbox, mrz_bbox) -> bool:
        """Check if text bbox overlaps with MRZ region bbox."""
        try:
            # Convert to numpy array if needed
            if isinstance(text_bbox, np.ndarray):
                text_bbox_arr = text_bbox
            else:
                text_bbox_arr = np.array(text_bbox)
            
            # Check if it's a 4-point polygon format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            if text_bbox_arr.shape == (4, 2):
                text_x1, text_y1 = text_bbox_arr.min(axis=0)
                text_x2, text_y2 = text_bbox_arr.max(axis=0)
            # Check if it's already in [x1, y1, x2, y2] format
            elif text_bbox_arr.shape == (4,) or (text_bbox_arr.ndim == 1 and len(text_bbox_arr) == 4):
                text_x1, text_y1, text_x2, text_y2 = text_bbox_arr[:4]
            else:
                # Try to flatten and use first 4 values
                flat = text_bbox_arr.flatten()
                if len(flat) >= 8:
                    # Assume 4 points: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    points = flat[:8].reshape(4, 2)
                    text_x1, text_y1 = points.min(axis=0)
                    text_x2, text_y2 = points.max(axis=0)
                elif len(flat) >= 4:
                    text_x1, text_y1, text_x2, text_y2 = flat[:4]
                else:
                    return False
        except Exception as e:
            print(f"    Error parsing text_bbox: {e}, shape: {text_bbox_arr.shape if isinstance(text_bbox, np.ndarray) else 'N/A'}")
            return False
        
        # mrz_bbox from YOLO: [x1, y1, x2, y2]
        mrz_x1, mrz_y1, mrz_x2, mrz_y2 = mrz_bbox
        
        # Calculate overlap
        overlap_x = max(0, min(text_x2, mrz_x2) - max(text_x1, mrz_x1))
        overlap_y = max(0, min(text_y2, mrz_y2) - max(text_y1, mrz_y1))
        overlap_area = overlap_x * overlap_y
        
        # Calculate text area
        text_area = (text_x2 - text_x1) * (text_y2 - text_y1)
        
        # Consider overlap if >= 50% of text area
        if text_area > 0:
            overlap_ratio = overlap_area / text_area
            is_overlap = overlap_ratio >= 0.5
            # Debug output for MRZ-like texts
            if not is_overlap:
                print(f"    No overlap: text[{int(text_x1)},{int(text_y1)},{int(text_x2)},{int(text_y2)}] vs mrz[{int(mrz_x1)},{int(mrz_y1)},{int(mrz_x2)},{int(mrz_y2)}] ratio={overlap_ratio:.2f}")
            return is_overlap
        return False
    
    def _find_texts_in_mrz_regions(self, detections: List[Union[Detection, Dict]], ocr_detections: List[Dict]) -> List[str]:
        """Find all texts that fall within MRZ regions."""
        all_mrz_texts = []
        
        for i, detection in enumerate(detections):
            try:
                # Extract bounding box coordinates from Detection object or dict
                # Detection object (dataclass) has attributes: bbox, confidence, class_name, etc.
                if isinstance(detection, dict):
                    mrz_bbox = detection.get('bbox', detection.get('box', []))
                    confidence = detection.get('confidence', 0)
                    class_name = detection.get('class_name', detection.get('label', 'unknown'))
                elif isinstance(detection, Detection):
                    mrz_bbox = detection.bbox
                    confidence = detection.confidence
                    class_name = getattr(detection, 'class_name', 'unknown')
                elif is_dataclass(detection):
                    mrz_bbox = detection.bbox
                    confidence = detection.confidence
                    class_name = getattr(detection, 'class_name', 'unknown')
                else:
                    print(f"⚠️ Unknown detection type: {type(detection)}")
                    continue
                
                # Validate mrz_bbox (handle numpy arrays)
                bbox_valid = False
                bbox_len = 0
                if isinstance(mrz_bbox, np.ndarray):
                    bbox_valid = mrz_bbox.size >= 4
                    bbox_len = mrz_bbox.size
                elif isinstance(mrz_bbox, (list, tuple)):
                    bbox_valid = len(mrz_bbox) >= 4
                    bbox_len = len(mrz_bbox)
                
                if not bbox_valid:
                    print(f"⚠️ Invalid bbox for detection {i}: length={bbox_len}")
                    continue
                
                x1, y1, x2, y2 = map(int, mrz_bbox[:4])
                
                print(f"MRZ Region {i+1} ({class_name}): bbox=[{x1},{y1},{x2},{y2}], confidence={confidence:.3f}")
                
                # Find all OCR texts within this MRZ region
                region_texts = []
                
                for ocr_detection in ocr_detections:
                    try:
                        text_bbox = ocr_detection.get('bbox', [])
                        text_content = ocr_detection.get('text', '')
                        text_confidence = ocr_detection.get('confidence', 1.0)
                        
                        # Ensure text_content is string and not empty
                        if isinstance(text_content, list):
                            text_content = ' '.join(str(t) for t in text_content if t)
                        text_content = str(text_content).strip()
                        
                        # Check if text_bbox is valid (handle numpy arrays and lists)
                        bbox_valid = False
                        if isinstance(text_bbox, np.ndarray):
                            bbox_valid = text_bbox.size > 0
                        elif isinstance(text_bbox, list):
                            bbox_valid = len(text_bbox) > 0
                        else:
                            bbox_valid = text_bbox is not None
                        
                        if not text_content or not bbox_valid:
                            continue
                        
                        # Check if text falls within MRZ region
                        if self._bbox_overlap(text_bbox, mrz_bbox):
                            region_texts.append({
                                'text': text_content,
                                'confidence': text_confidence,
                                'bbox': text_bbox
                            })
                            print(f"  Found MRZ text: '{text_content}' (conf: {text_confidence:.3f})")
                    
                    except Exception as text_error:
                        print(f"  Error processing OCR text: {str(text_error)}")
                        continue
                
                # Sort by Y coordinate (top to bottom)
                def get_y_coord(item):
                    bbox = item['bbox']
                    if isinstance(bbox, np.ndarray):
                        bbox_arr = bbox
                    else:
                        bbox_arr = np.array(bbox)
                    
                    # Check shape to determine format
                    if bbox_arr.shape == (4, 2):
                        # Format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        return bbox_arr.min(axis=0)[1]
                    else:
                        # Format: [x1, y1, x2, y2] or flattened
                        flat = bbox_arr.flatten()
                        return flat[1] if len(flat) >= 2 else 0
                
                region_texts.sort(key=get_y_coord)
                
                # Add to results
                for text_item in region_texts:
                    all_mrz_texts.append(text_item['text'])
                    
            except Exception as e:
                print(f"Error processing MRZ detection {i}: {str(e)}")
                continue
        
        return all_mrz_texts
    
    def _generate_mrz_string(self, all_mrz_texts: List[str]) -> str:
        """Generate final MRZ string by combining all texts."""
        mrz_string = ""
        
        if all_mrz_texts:
            # Join all texts together, remove invalid characters and uppercase
            combined_text = ''.join(all_mrz_texts)
            # Keep only valid MRZ characters and uppercase
            mrz_string = re.sub(r'[^A-Z0-9<]', '', combined_text.upper())
            print(f"Generated MRZ string: {mrz_string}")
        
        return mrz_string
    
    def extract_dates_from_all_texts(self, texts: List[str]) -> List[str]:
        """
        Extract and format dates from all OCR texts using regex patterns.
        Supports multiple date formats including dd/mm/yyyy, dd/mm/yy, etc.
        
        Args:
            texts: List of all OCR text strings to search for dates
            
        Returns:
            List of formatted date strings (dd/MM/yyyy)
        """
        dates_found = []
        
        for text in texts:
            if not text:
                continue
                
            text_str = str(text).strip()
            print(f"Searching for dates in: '{text_str}'")
            
            # Pattern 1: dd/mm/yyyy (like 18/03/2024) - relaxed word boundaries
            pattern1 = r'(\d{1,2})/(\d{1,2})/(\d{4})'
            matches1 = re.findall(pattern1, text_str)
            for match in matches1:
                day, month, year = match
                try:
                    day_int, month_int, year_int = int(day), int(month), int(year)
                    if 1 <= day_int <= 31 and 1 <= month_int <= 12 and 1900 <= year_int <= 2100:
                        formatted_date = f"{day_int:02d}/{month_int:02d}/{year_int}"
                        if formatted_date not in dates_found:
                            dates_found.append(formatted_date)
                            print(f"Found date (dd/mm/yyyy): {formatted_date}")
                except:
                    pass
            
            # Pattern 2: dd/mm/yy (like 18/03/24) - relaxed word boundaries
            pattern2 = r'(\d{1,2})/(\d{1,2})/(\d{2})(?!\d)'  # negative lookahead to avoid matching part of 4-digit year
            matches2 = re.findall(pattern2, text_str)
            for match in matches2:
                day, month, year = match
                try:
                    day_int, month_int, year_int = int(day), int(month), int(year)
                    # Handle 2-digit year
                    if year_int >= 50:
                        full_year = 1900 + year_int
                    else:
                        full_year = 2000 + year_int
                    
                    if 1 <= day_int <= 31 and 1 <= month_int <= 12:
                        formatted_date = f"{day_int:02d}/{month_int:02d}/{full_year}"
                        if formatted_date not in dates_found:
                            dates_found.append(formatted_date)
                            print(f"Found date (dd/mm/yy): {formatted_date}")
                except:
                    pass
            
            # Pattern 3: ddmmyyyy (like 18032024) - more restrictive
            pattern3 = r'(?<!\d)(\d{2})(\d{2})(\d{4})(?!\d)'
            matches3 = re.findall(pattern3, text_str)
            for match in matches3:
                day, month, year = match
                try:
                    day_int, month_int, year_int = int(day), int(month), int(year)
                    if 1 <= day_int <= 31 and 1 <= month_int <= 12 and 1900 <= year_int <= 2100:
                        formatted_date = f"{day_int:02d}/{month_int:02d}/{year_int}"
                        if formatted_date not in dates_found:
                            dates_found.append(formatted_date)
                            print(f"Found date (ddmmyyyy): {formatted_date}")
                except:
                    pass
            
            # Pattern 4: dd-mm-yyyy (like 18-03-2024)
            pattern4 = r'(\d{1,2})-(\d{1,2})-(\d{4})'
            matches4 = re.findall(pattern4, text_str)
            for match in matches4:
                day, month, year = match
                try:
                    day_int, month_int, year_int = int(day), int(month), int(year)
                    if 1 <= day_int <= 31 and 1 <= month_int <= 12 and 1900 <= year_int <= 2100:
                        formatted_date = f"{day_int:02d}/{month_int:02d}/{year_int}"
                        if formatted_date not in dates_found:
                            dates_found.append(formatted_date)
                            print(f"Found date (dd-mm-yyyy): {formatted_date}")
                except:
                    pass
            
            # Pattern 5: ddmmyy (6 digits like 180324) - be careful not to match random 6-digit numbers
            pattern5 = r'(?<!\d)(\d{6})(?!\d)'
            matches5 = re.findall(pattern5, text_str)
            for match in matches5:
                date_str = match
                # Try ddmmyy format
                try:
                    day = int(date_str[:2])
                    month = int(date_str[2:4])
                    year = int(date_str[4:6])
                    
                    # Handle 2-digit year
                    if year >= 50:
                        full_year = 1900 + year
                    else:
                        full_year = 2000 + year
                    
                    if 1 <= day <= 31 and 1 <= month <= 12:
                        formatted_date = f"{day:02d}/{month:02d}/{full_year}"
                        if formatted_date not in dates_found:
                            dates_found.append(formatted_date)
                            print(f"Found date (ddmmyy): {formatted_date}")
                except:
                    pass
        
        print(f"Total dates found: {dates_found}")
        return sorted(list(set(dates_found)))  # Remove duplicates and sort
    
    def extract_dates_from_texts(self, texts: List[str]) -> List[str]:
        """
        Extract and format dates from MRZ texts.
        
        Args:
            texts: List of text strings to search for dates
            
        Returns:
            List of formatted date strings (dd/MM/yyyy)
        """
        dates_found = []
        
        for text in texts:
            if not text:
                continue
                
            text_str = str(text).strip()
            
            # Look for 6-digit date patterns
            date_patterns = re.findall(r'\d{6}', text_str)
            
            for date_str in date_patterns:
                # Try different date formats
                formatted_dates = self._parse_date_patterns(date_str)
                for date in formatted_dates:
                    if date and date not in dates_found:
                        dates_found.append(date)
        
        return sorted(list(set(dates_found)))  # Remove duplicates and sort
    
    def _parse_date_patterns(self, date_str: str) -> List[str]:
        """Parse date string in different formats."""
        dates = []
        
        if len(date_str) == 6:
            # Try YYMMDD format
            try:
                year = int(date_str[:2])
                month = int(date_str[2:4])
                day = int(date_str[4:6])
                
                # Handle 2-digit year
                if year >= 50:
                    full_year = 1900 + year
                else:
                    full_year = 2000 + year
                
                if 1 <= month <= 12 and 1 <= day <= 31:
                    dates.append(f"{day:02d}/{month:02d}/{full_year}")
            except:
                pass
            
            # Try DDMMYY format
            try:
                day = int(date_str[:2])
                month = int(date_str[2:4])
                year = int(date_str[4:6])
                
                # Handle 2-digit year
                if year >= 50:
                    full_year = 1900 + year
                else:
                    full_year = 2000 + year
                
                if 1 <= month <= 12 and 1 <= day <= 31:
                    formatted_date = f"{day:02d}/{month:02d}/{full_year}"
                    if formatted_date not in dates:
                        dates.append(formatted_date)
            except:
                pass
        
        return dates
