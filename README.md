# 🎨 AI Background Removal API

Production-grade FastAPI application for removing backgrounds from images using rembg/U²-Net.

## ✨ Features

- ⚡ **High Performance**: Async I/O with FastAPI + Gunicorn
- 🚀 **Optimized**: Model preloaded once at startup
- 🔒 **Secure**: File validation, size limits, error handling
- 📊 **Observable**: Detailed logging and health checks
- 🐳 **Container Ready**: Fully Dockerized
- 📚 **Auto-documented**: Swagger UI + ReDoc
- 🌐 **CORS Enabled**: Cross-domain support

## 🛠️ Quick Start

### Option 1: Docker (Recommended)

```bash
# Build the image
docker build -t bg-removal-api .

# Run the container
docker run -d -p 8000:8000 --name bg-api bg-removal-api

# Check logs
docker logs -f bg-api
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run with Uvicorn (development)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run with Gunicorn (production)
gunicorn -k uvicorn.workers.UvicornWorker main:app \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

## 📡 API Endpoints

### Remove Background
```bash
POST /api/remove-bg
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/remove-bg \
  -F "file=@input.jpg" \
  -o output.png
```

**Python Example:**
```python
import requests

url = "http://localhost:8000/api/remove-bg"
files = {"file": open("input.jpg", "rb")}
response = requests.post(url, files=files)

with open("output.png", "wb") as f:
    f.write(response.content)
```

**JavaScript Example:**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/api/remove-bg', {
  method: 'POST',
  body: formData
});

const blob = await response.blob();
const url = URL.createObjectURL(blob);
```

### Health Check
```bash
GET /health
```

### Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🚀 Deployment

### VPS Deployment

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Clone or upload your code
git clone <your-repo>
cd bg-removal-api

# Build and run with Docker
docker build -t bg-removal-api .
docker run -d -p 8000:8000 --restart unless-stopped bg-removal-api

# Or use Docker Compose
docker-compose up -d
```

### Cloud Platforms

#### Render
1. Connect your GitHub repository
2. Select "Docker" as environment
3. Set port to `8000`
4. Deploy

#### Railway
```bash
railway login
railway init
railway up
```

#### AWS EC2
```bash
# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo service docker start

# Deploy
docker build -t bg-removal-api .
docker run -d -p 8000:8000 bg-removal-api
```

### Environment Variables (Optional)

```bash
# .env file
PORT=8000
MAX_FILE_SIZE=10485760
LOG_LEVEL=info
WORKERS=4
```

## ⚙️ Configuration

### Worker Configuration
Adjust workers based on your server specs:
- **2GB RAM**: 2-4 workers
- **4GB RAM**: 4-8 workers
- **8GB+ RAM**: 8-16 workers

```bash
gunicorn -k uvicorn.workers.UvicornWorker main:app --workers 4
```

### File Size Limits
Edit `MAX_FILE_SIZE` in `main.py`:
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

### CORS Configuration
Update allowed origins in `main.py`:
```python
allow_origins=["https://yourdomain.com"]
```

## 📊 Performance

- **Startup Time**: ~5-10 seconds (model loading)
- **Processing Time**: ~100-200ms for small images (< 1MB)
- **Memory Usage**: ~500MB base + 100-200MB per worker
- **Concurrent Requests**: Scales with worker count

## 🔍 Monitoring

### Check Status
```bash
curl http://localhost:8000/health
```

### View Logs
```bash
# Docker
docker logs -f bg-api

# Direct
tail -f /var/log/bg-removal-api.log
```

## 🐛 Troubleshooting

### Model Loading Fails
- Ensure internet connection for first-time model download
- Check disk space (model is ~180MB)

### Out of Memory
- Reduce worker count
- Increase VPS RAM
- Enable swap space

### Slow Processing
- Use SSD storage
- Increase CPU cores
- Consider GPU support (requires CUDA setup)

## 📝 API Specifications

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Max File Size: 10MB
- Allowed Formats: JPG, JPEG, PNG

**Response:**
- Content-Type: `image/png`
- Format: Transparent PNG
- Status Codes:
  - `200`: Success
  - `400`: Invalid input
  - `500`: Server error

## 🔐 Security Notes

- Non-root user in Docker
- File type validation
- Size limit enforcement
- Input sanitization
- Rate limiting (recommended: add nginx reverse proxy)

## 📄 License

MIT License - Feel free to use in personal and commercial projects.

## 🤝 Support

For issues and questions:
- Check `/docs` for API documentation
- Review logs for error details
- Ensure dependencies are up to date

---

**Built with ❤️ using FastAPI, rembg, and U²-Net**