# Fly.io Dockerfile for Crypto Signal Bot
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .
COPY admin/ ./admin/

# Create data directory for persistent storage
RUN mkdir -p /data

# Create health check endpoint script
RUN echo 'from http.server import HTTPServer, BaseHTTPRequestHandler\n\
import threading\n\
import os\n\
\n\
class HealthHandler(BaseHTTPRequestHandler):\n\
    def do_GET(self):\n\
        if self.path == "/health":\n\
            self.send_response(200)\n\
            self.send_header("Content-type", "text/plain")\n\
            self.end_headers()\n\
            self.wfile.write(b"OK")\n\
        else:\n\
            self.send_response(404)\n\
            self.end_headers()\n\
    def log_message(self, format, *args):\n\
        pass\n\
\n\
def start_health_server():\n\
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)\n\
    server.serve_forever()\n\
\n\
if __name__ == "__main__":\n\
    threading.Thread(target=start_health_server, daemon=True).start()\n\
    os.system("python3 bot.py")' > start.py

# Expose health check port
EXPOSE 8080

# Run the bot with health check server
CMD ["python3", "start.py"]
