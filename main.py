import io
import logging
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
ALLOWED_EXTENSIONS = {"image/jpeg", "image/jpg", "image/png"}


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
    # Check content type
    if file.content_type not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (read in chunks to avoid loading entire file into memory)
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
    Process image and remove background
    """
    try:
        # Open image
        input_image = Image.open(io.BytesIO(file_content))
        
        # Log image info
        logger.info(f"Processing image: {input_image.format} {input_image.size} {input_image.mode}")
        
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
    
    Args:
        file: Uploaded image file (JPG/PNG, max 10MB)
    
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )