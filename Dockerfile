# Vigint API Services Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs recordings

# Download MediaMTX binary
RUN wget -O mediamtx.tar.gz https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_linux_amd64.tar.gz \
    && tar -xzf mediamtx.tar.gz \
    && chmod +x mediamtx \
    && rm mediamtx.tar.gz

# Create non-root user
RUN useradd -m -u 1000 vigint && chown -R vigint:vigint /app
USER vigint

# Expose ports
EXPOSE 5000 8554 9997 9998

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Default command
CMD ["python3", "start_vigint.py", "--mode", "full"]