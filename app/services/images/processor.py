import io
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
from fastapi import UploadFile, HTTPException
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """service for processing and converting images to webp format."""
    
    # supported input formats
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    # maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # image quality for webp conversion
    WEBP_QUALITY = 85
    
    # maximum image dimensions
    MAX_WIDTH = 2048
    MAX_HEIGHT = 2048
    
    def __init__(self, upload_dir: str = "static/images"):
        """Initialize the image processor.
        
        Args:
            upload_dir: Directory to store processed images
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_image_file(self, file: UploadFile) -> None:
        """Validate uploaded image file.
        
        Args:
            file: The uploaded file to validate
            
        Raises:
            HTTPException: If file is invalid
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        # check file size
        if hasattr(file, 'size') and file.size and file.size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Maximum size: {self.MAX_FILE_SIZE // (1024*1024)}MB"
            )
    
    def resize_image_if_needed(self, image: Image.Image) -> Image.Image:
        """Resize image if it exceeds maximum dimensions.
        
        Args:
            image: PIL Image object
            
        Returns:
            Resized image if needed, original otherwise
        """
        width, height = image.size
        
        if width <= self.MAX_WIDTH and height <= self.MAX_HEIGHT:
            return image
        
        # calculate new dimensions maintaining aspect ratio
        ratio = min(self.MAX_WIDTH / width, self.MAX_HEIGHT / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        
        logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def convert_to_webp(self, image: Image.Image) -> Image.Image:
        """Convert image to webp format.
        
        Args:
            image: PIL Image object
            
        Returns:
            Image converted to webp format
        """
        # convert RGBA to RGB if necessary (webp doesn't support transparency well)
        if image.mode in ('RGBA', 'LA', 'P'):
            # create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        
        return image
    
    def generate_filename(self, original_filename: str) -> str:
        """Generate unique filename for processed image.
        
        Args:
            original_filename: Original filename
            
        Returns:
            New unique filename with .webp extension
        """
        # generate UUID for uniqueness
        unique_id = str(uuid.uuid4())
        original_name = Path(original_filename).stem
        # clean the original name (keep only alphanumeric and common chars)
        clean_name = ''.join(c for c in original_name if c.isalnum() or c in '-_')[:50]
        return f"{clean_name}_{unique_id}.webp"
    
    async def process_image(self, file: UploadFile) -> Tuple[str, str]:
        """Process uploaded image file.
        
        Args:
            file: Uploaded image file
            
        Returns:
            Tuple of (filename, file_path) of processed image
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            # check the file
            self.validate_image_file(file)
            
            # read file content
            content = await file.read()
            
            # additional size check after reading
            if len(content) > self.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File too large. Maximum size: {self.MAX_FILE_SIZE // (1024*1024)}MB"
                )
            
            # open and process image
            image = Image.open(io.BytesIO(content))
            
            try:
                # resize if needed
                image = self.resize_image_if_needed(image)
                
                # convert to webp
                image = self.convert_to_webp(image)
                
                # generate unique filename
                filename = self.generate_filename(file.filename)
                file_path = self.upload_dir / filename
                
                # save processed image
                image.save(file_path, format='WEBP', quality=self.WEBP_QUALITY, optimize=True)
                
                logger.info(f"Successfully processed image: {filename}")
                return filename, str(file_path)
            finally:
                # Ensure image is closed to release file handles
                if hasattr(image, 'close'):
                    image.close()
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process image")
    
    def delete_image(self, filename: str) -> bool:
        """Delete processed image file.
        
        Args:
            filename: Name of file to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        import time
        try:
            file_path = self.upload_dir / filename
            if not file_path.exists():
                return False
            
            # Try to delete with retries to handle Windows file locking
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    file_path.unlink()
                    logger.info(f"Deleted image: {filename}")
                    return True
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        # Wait a bit and retry for Windows file locking issues
                        time.sleep(0.1)
                        continue
                    else:
                        logger.error(f"Permission error deleting image {filename}: {str(e)}")
                        return False
                except Exception as e:
                    logger.error(f"Error deleting image {filename}: {str(e)}")
                    return False
            
            return False
        except Exception as e:
            logger.error(f"Error deleting image {filename}: {str(e)}")
            return False


# global instance
image_processor = ImageProcessor()