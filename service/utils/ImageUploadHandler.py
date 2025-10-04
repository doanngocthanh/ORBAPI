"""
Image Upload Handler
Handles various image formats and conversions for file uploads
"""
import io
import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional, Union
import tempfile
import os


class ImageUploadHandler:
    """
    Handles image upload processing with format conversion and validation
    """
    
    SUPPORTED_FORMATS = ['JPEG', 'JPG', 'PNG', 'BMP', 'WEBP', 'TIFF']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, auto_convert_to_rgb: bool = True):
        """
        Initialize image handler
        
        Args:
            auto_convert_to_rgb: Automatically convert RGBA/other modes to RGB
        """
        self.auto_convert_to_rgb = auto_convert_to_rgb
    
    @staticmethod
    def convert_to_rgb(image: Image.Image) -> Image.Image:
        """
        Convert image to RGB mode (remove alpha channel if exists)
        
        Args:
            image: PIL Image in any mode
            
        Returns:
            PIL Image in RGB mode
        """
        if image.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            # Paste image using alpha channel as mask
            background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
            return background
        elif image.mode == 'LA':
            # Grayscale with alpha
            background = Image.new('L', image.size, 255)
            background.paste(image, mask=image.split()[1])
            return background.convert('RGB')
        elif image.mode == 'P':
            # Palette mode
            return image.convert('RGB')
        elif image.mode == 'L':
            # Grayscale
            return image.convert('RGB')
        elif image.mode == 'CMYK':
            # CMYK to RGB
            return image.convert('RGB')
        elif image.mode != 'RGB':
            # Any other mode
            return image.convert('RGB')
        
        return image
    
    def load_from_bytes(
        self, 
        image_bytes: bytes,
        convert_to_rgb: Optional[bool] = None
    ) -> Tuple[Image.Image, dict]:
        """
        Load image from bytes with automatic format handling
        
        Args:
            image_bytes: Raw image bytes
            convert_to_rgb: Override auto_convert_to_rgb setting
            
        Returns:
            Tuple of (PIL Image, info dict)
        """
        if convert_to_rgb is None:
            convert_to_rgb = self.auto_convert_to_rgb
        
        # Validate file size
        file_size = len(image_bytes)
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"File size ({file_size} bytes) exceeds maximum ({self.MAX_FILE_SIZE} bytes)")
        
        # Load image
        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            raise ValueError(f"Failed to load image: {str(e)}")
        
        # Get original info
        original_mode = image.mode
        original_format = image.format or "UNKNOWN"
        width, height = image.size
        
        info = {
            "original_mode": original_mode,
            "original_format": original_format,
            "width": width,
            "height": height,
            "file_size": file_size,
            "converted": False
        }
        
        # Convert if needed
        if convert_to_rgb and original_mode != 'RGB':
            image = self.convert_to_rgb(image)
            info["converted"] = True
            info["final_mode"] = image.mode
        else:
            info["final_mode"] = original_mode
        
        return image, info
    
    def save_to_temp(
        self,
        image: Image.Image,
        format: str = 'JPEG',
        quality: int = 95,
        suffix: Optional[str] = None
    ) -> str:
        """
        Save PIL Image to temporary file
        
        Args:
            image: PIL Image to save
            format: Output format (JPEG, PNG, etc.)
            quality: JPEG quality (1-100)
            suffix: File suffix (auto-detected if None)
            
        Returns:
            Path to temporary file
        """
        # Auto-detect suffix
        if suffix is None:
            suffix = f'.{format.lower()}'
            if format.upper() == 'JPEG':
                suffix = '.jpg'
        
        # Ensure RGB for JPEG
        if format.upper() in ['JPEG', 'JPG'] and image.mode != 'RGB':
            image = self.convert_to_rgb(image)
        
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            temp_path = tmp_file.name
            
            # Save with appropriate settings
            save_kwargs = {}
            if format.upper() in ['JPEG', 'JPG']:
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif format.upper() == 'PNG':
                save_kwargs['optimize'] = True
            
            image.save(temp_path, format=format, **save_kwargs)
        
        return temp_path
    
    def to_cv2_array(self, image: Image.Image) -> np.ndarray:
        """
        Convert PIL Image to OpenCV array (BGR format)
        
        Args:
            image: PIL Image
            
        Returns:
            OpenCV array in BGR format
        """
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = self.convert_to_rgb(image)
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Convert RGB to BGR for OpenCV
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_bgr
    
    def calculate_quality_metrics(self, image: Union[Image.Image, np.ndarray]) -> dict:
        """
        Calculate image quality metrics
        
        Args:
            image: PIL Image or numpy array
            
        Returns:
            Dictionary with quality metrics
        """
        # Convert to cv2 array if PIL Image
        if isinstance(image, Image.Image):
            img_array = self.to_cv2_array(image)
        else:
            img_array = image
        
        # Convert to grayscale for analysis
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_array
        
        # Calculate metrics
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        brightness = gray.mean()
        contrast = gray.std()
        
        # Calculate overall quality score (0-100)
        quality_score = min(100, (blur_score / 5) + (contrast / 2))
        
        return {
            "blur_score": round(float(blur_score), 2),
            "brightness": round(float(brightness), 2),
            "contrast": round(float(contrast), 2),
            "quality_score": round(float(quality_score), 2)
        }
    
    def process_upload(
        self,
        image_bytes: bytes,
        save_temp: bool = True,
        format: str = 'JPEG',
        calculate_metrics: bool = True
    ) -> dict:
        """
        Complete processing pipeline for uploaded image
        
        Args:
            image_bytes: Raw image bytes from upload
            save_temp: Whether to save to temporary file
            format: Output format for temp file
            calculate_metrics: Whether to calculate quality metrics
            
        Returns:
            Dictionary with all processing results
        """
        # Load image
        image, info = self.load_from_bytes(image_bytes)
        
        result = {
            "image": image,
            "info": info
        }
        
        # Save to temp file
        if save_temp:
            temp_path = self.save_to_temp(image, format=format)
            result["temp_path"] = temp_path
        
        # Calculate metrics
        if calculate_metrics:
            metrics = self.calculate_quality_metrics(image)
            result["metrics"] = metrics
        
        return result
    
    @staticmethod
    def cleanup_temp(temp_path: str) -> bool:
        """
        Clean up temporary file
        
        Args:
            temp_path: Path to temporary file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                return True
        except Exception as e:
            print(f"Failed to cleanup temp file {temp_path}: {e}")
        return False


# Example usage
if __name__ == "__main__":
    # Test with sample image
    handler = ImageUploadHandler(auto_convert_to_rgb=True)
    
    # Simulate uploaded file
    test_image_path = "test_rgba.png"
    
    # Create test RGBA image
    test_img = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
    test_img.save(test_image_path)
    
    # Read as bytes
    with open(test_image_path, 'rb') as f:
        image_bytes = f.read()
    
    # Process
    result = handler.process_upload(image_bytes, save_temp=True, calculate_metrics=True)
    
    print("Image Info:")
    print(f"  Original mode: {result['info']['original_mode']}")
    print(f"  Final mode: {result['info']['final_mode']}")
    print(f"  Converted: {result['info']['converted']}")
    print(f"  Size: {result['info']['width']}x{result['info']['height']}")
    
    print("\nQuality Metrics:")
    for key, value in result['metrics'].items():
        print(f"  {key}: {value}")
    
    print(f"\nTemp file: {result['temp_path']}")
    
    # Cleanup
    handler.cleanup_temp(result['temp_path'])
    os.unlink(test_image_path)
    print("\nCleanup complete!")
