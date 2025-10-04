# Multi-stage build for optimized image size
FROM python:3.10-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ===========================
# Final stage
# ===========================
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs/tasks \
    && mkdir -p models/pt \
    && mkdir -p lockup \
    && mkdir -p weights \
    && mkdir -p images
RUN mkdir -p /root/.cache/torch/hub/checkpoints && \
    if [ ! -f /root/.cache/torch/hub/checkpoints/vgg19_bn-c79401a0.pth ]; then \
      for i in 1 2 3 4 5; do \
        curl -L -o /root/.cache/torch/hub/checkpoints/vgg19_bn-c79401a0.pth \
        "https://download.pytorch.org/models/vgg19_bn-c79401a0.pth" && break || sleep 5; \
      done; \
    fi
# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NNPACK_WARN=0 \
    PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5555/health')" || exit 1

# Run the application
CMD ["uvicorn", "fastapi_server_new:app", "--host", "0.0.0.0", "--port", "5555"]
# Download and cache PyTorch model weights
