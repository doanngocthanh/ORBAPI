# 🐋 Quick Start - Docker Deployment

## 🚀 One-Line Deploy

### Linux/Mac:
```bash
chmod +x deploy.sh
./deploy.sh build && ./deploy.sh start
```

### Windows:
```cmd
deploy.bat build && deploy.bat start
```

---

## 📋 What You Get

✅ **PaddleOCR Engine** - Detection + Recognition  
✅ **VietOCR Engine** - Vietnamese text recognition  
✅ **ORB Alignment** - Template-based image alignment  
✅ **YOLO Detection** - Card type classification  
✅ **MRZ Processing** - Machine Readable Zone extraction  
✅ **Health Monitoring** - Built-in health checks  
✅ **Auto-restart** - Automatic recovery on failure  

---

## 🌐 Access Points

| Service | URL |
|---------|-----|
| 🏠 Home | http://localhost:8000 |
| 📖 API Docs | http://localhost:8000/docs |
| ❤️ Health Check | http://localhost:8000/health |
| 📸 Scan API | http://localhost:8000/api/scan/ |
| 📊 Dashboard | http://localhost:8000/dashboard |

---

## 🛠️ Quick Commands

```bash
# Build image
./deploy.sh build

# Start services
./deploy.sh start

# Check status
./deploy.sh status

# View logs
./deploy.sh logs

# Restart
./deploy.sh restart

# Stop
./deploy.sh stop

# Test API
./deploy.sh test

# Backup
./deploy.sh backup

# Clean up
./deploy.sh clean
```

---

## 📦 What's Included

### Docker Files
- ✅ `Dockerfile` - Multi-stage build for optimized image
- ✅ `docker-compose.yml` - Service orchestration
- ✅ `.dockerignore` - Build optimization
- ✅ `deploy.sh` - Linux/Mac deployment script
- ✅ `deploy.bat` - Windows deployment script

### Features
- 🔹 Multi-stage build (reduced image size)
- 🔹 Health checks (automatic monitoring)
- 🔹 Volume mounts (persistent data)
- 🔹 Resource limits (controlled usage)
- 🔹 Auto-restart (high availability)
- 🔹 Logging (persistent logs)

---

## ⚙️ System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disk | 10 GB | 20 GB |
| Docker | 20.10+ | Latest |

---

## 🧪 Test After Deploy

```bash
# Health check
curl http://localhost:8000/health

# Test scan API
curl -X POST "http://localhost:8000/api/scan/" \
  -F "file=@test_image.jpg"
```

Expected health response:
```json
{
  "status": "healthy",
  "engines": {
    "paddleocr": {"available": true, "status": "ready"},
    "vietocr": {"available": true, "status": "ready"}
  }
}
```

---

## 📁 Directory Structure

```
ORBAPI/
├── 🐋 Docker Files
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .dockerignore
│   ├── deploy.sh
│   └── deploy.bat
│
├── 📦 Application
│   ├── fastapi_server_new.py
│   ├── src/
│   │   └── api/
│   │       └── scan.py
│   └── service/
│
├── 🎯 Models (mounted)
│   ├── models/pt/
│   ├── lockup/
│   └── weights/
│
└── 📊 Data (persistent)
    ├── logs/
    └── images/
```

---

## 🔧 Configuration

### Change Port

Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Change 8080 to your desired port
```

### Increase Workers

Edit `Dockerfile`:
```dockerfile
CMD ["uvicorn", "fastapi_server_new:app", "--workers", "8"]
```

### Adjust Memory

Edit `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 12G  # Increase as needed
```

---

## 🐛 Troubleshooting

### Port already in use
```bash
# Stop conflicting service
docker-compose down
# Or change port in docker-compose.yml
```

### Out of memory
```bash
# Increase Docker Desktop memory to 8GB+
# Or reduce workers in Dockerfile
```

### Models not loading
```bash
# Check models directory
ls -la models/pt/

# Rebuild with no cache
./deploy.sh clean
./deploy.sh build
```

### Can't access API
```bash
# Check logs
./deploy.sh logs

# Check status
./deploy.sh status

# Test health
curl http://localhost:8000/health
```

---

## 📚 Full Documentation

For detailed information, see [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

---

## 🆘 Getting Help

1. ✅ Check logs: `./deploy.sh logs`
2. ✅ Check status: `./deploy.sh status`
3. ✅ Test API: `./deploy.sh test`
4. ✅ Read [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

---

## 🎉 That's It!

Your OCR API is now running in Docker! 🚀

**Next Steps:**
1. Open http://localhost:8000 in your browser
2. Try the API at http://localhost:8000/docs
3. Upload an image and test the OCR

---

**Version:** 1.0.0  
**Last Updated:** October 4, 2025
