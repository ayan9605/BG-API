import io
import logging
import os  # ADD THIS IMPORT
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from PIL import Image
from rembg import remove, new_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global model session (loaded once at startup)
model_session: Optional[object] = None

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Expanded list of supported image formats (PIL/Pillow supported)
ALLOWED_EXTENSIONS = {
    "image/jpeg", "image/jpg", "image/png", "image/gif", 
    "image/bmp", "image/tiff", "image/webp", "image/x-icon",
    "image/vnd.microsoft.icon", "image/avif", "image/heic",
    "image/heif", "image/x-tga", "image/x-pcx", "image/x-portable-pixmap",
    "image/x-portable-graymap", "image/x-portable-bitmap",
    "image/x-portable-anymap", "image/x-ms-bmp"
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    global model_session
    
    # Startup: Load rembg model once
    logger.info("🚀 Starting up: Loading rembg model...")
    try:
        model_session = new_session("u2netp")
        logger.info("✅ Model loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        raise
    
    yield
    
    # Shutdown: Cleanup
    logger.info("🛑 Shutting down gracefully...")
    model_session = None


# Initialize FastAPI app
app = FastAPI(
    title="AI Background Removal API",
    description="High-performance API for removing backgrounds from images using rembg/U²-Net",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_image(file: UploadFile) -> None:
    """
    Validate uploaded file type and size
    """
    # Check content type (relaxed for common formats)
    if file.content_type and file.content_type not in ALLOWED_EXTENSIONS:
        # Try to validate by file extension if content type check fails
        if not any(file.filename.lower().endswith(ext) for ext in [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', 
            '.tif', '.webp', '.ico', '.avif', '.heic', '.heif',
            '.tga', '.pcx', '.ppm', '.pgm', '.pbm', '.pnm'
        ]):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Supported formats: JPEG, PNG, GIF, BMP, TIFF, WebP, ICO, AVIF, and more"
            )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )


async def process_image(file_content: bytes) -> bytes:
    """
    Process image and remove background - supports all PIL formats
    """
    try:
        # Open image (PIL auto-detects format)
        input_image = Image.open(io.BytesIO(file_content))
        
        # Log image info
        logger.info(f"Processing image: {input_image.format} {input_image.size} {input_image.mode}")
        
        # Convert image mode if necessary for rembg compatibility
        # rembg works best with RGB or RGBA images
        if input_image.mode not in ('RGB', 'RGBA'):
            if input_image.mode == 'P':  # Palette mode
                # Check if image has transparency
                if 'transparency' in input_image.info:
                    input_image = input_image.convert('RGBA')
                else:
                    input_image = input_image.convert('RGB')
            elif input_image.mode in ('L', 'LA'):  # Grayscale
                if input_image.mode == 'LA':
                    input_image = input_image.convert('RGBA')
                else:
                    input_image = input_image.convert('RGB')
            elif input_image.mode == '1':  # Binary
                input_image = input_image.convert('RGB')
            elif input_image.mode == 'CMYK':
                input_image = input_image.convert('RGB')
            else:
                # For any other mode, try converting to RGB
                input_image = input_image.convert('RGB')
            
            logger.info(f"Converted image mode to: {input_image.mode}")
        
        # Remove background using preloaded model
        output_image = remove(input_image, session=model_session)
        
        # Convert to PNG with transparency
        output_buffer = io.BytesIO()
        output_image.save(output_buffer, format="PNG", optimize=True)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}"
        )


@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "name": "AI Background Removal API",
        "version": "1.0.0",
        "status": "running",
        "supported_formats": [
            "JPEG", "PNG", "GIF", "BMP", "TIFF", "WebP", 
            "ICO", "AVIF", "HEIC", "TGA", "PCX", "PPM", "PGM", "PBM"
        ],
        "endpoints": {
            "remove_background": "/api/remove-bg",
            "documentation": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "model_loaded": model_session is not None
    }


@app.post("/api/remove-bg")
async def remove_background(file: UploadFile = File(...)):
    """
    Remove background from uploaded image
    
    Supports all major image formats: JPEG, PNG, GIF, BMP, TIFF, WebP, 
    ICO, AVIF, HEIC, TGA, PCX, PPM, and more.
    
    Args:
        file: Uploaded image file (max 10MB)
    
    Returns:
        Transparent PNG image stream
    """
    logger.info(f"📥 Received request: {file.filename} ({file.content_type})")
    
    try:
        # Validate file
        validate_image(file)
        
        # Read file content
        file_content = await file.read()
        
        # Process image (remove background)
        output_bytes = await process_image(file_content)
        
        logger.info(f"✅ Successfully processed: {file.filename}")
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(output_bytes),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=nobg_{file.filename.rsplit('.', 1)[0]}.png"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for uncaught errors
    """
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Graceful shutdown handler
def handle_shutdown(signum, frame):
    """
    Handle shutdown signals
    """
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


if __name__ == "__main__":
    import uvicorn
    # FIXED: Read PORT from environment variable (Render requirement)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
