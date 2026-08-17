FROM python:3.12-slim

# Install system dependencies (ffmpeg for audio handling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set default port
ENV PORT=8080
EXPOSE 8080

# Run 24/7 Jarvis Cloud Server
CMD ["python", "server.py"]
