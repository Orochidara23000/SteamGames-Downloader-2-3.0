FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
# Install a specific version of Gradio that's known to work
RUN pip install --no-cache-dir gradio==3.50.2
RUN pip install --no-cache-dir -r requirements.txt

# Install SteamCMD dependencies
RUN apt-get update && apt-get install -y \
    lib32gcc-s1 \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /app/logs
RUN mkdir -p /data/downloads

# Copy application files
COPY . .

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.py

# Environment variables
ENV PORT=7862
ENV LOG_LEVEL=INFO
ENV STEAM_DOWNLOAD_PATH=/data/downloads
ENV ENABLE_SHARE=True
ENV DEBUG=False

# Expose the port
EXPOSE 7862

# Run the application using the entrypoint script
CMD ["python", "docker-entrypoint.py"]