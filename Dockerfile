# Sử dụng Python 3.10 slim image làm base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Cài đặt system dependencies cần thiết cho OpenCV
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libhdf5-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requitement.txt .

# Upgrade pip và cài đặt Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requitement.txt

# Copy source code
COPY . .

# Create directories for any potential file uploads or temp files
RUN mkdir -p /tmp/uploads

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1



# Run the application
CMD ["python", "main.py"]
