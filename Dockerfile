FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STEAM_DOWNLOAD_PATH=/data/downloads \
    PYTHONPATH="/app:/app/ui:/app/modules:/app/utils"

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    lib32gcc-s1 \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directories
WORKDIR /app
RUN mkdir -p /app/logs /app/steamcmd /data/downloads /data/config \
    /app/ui /app/modules /app/utils /app/data

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make scripts executable
RUN chmod +x /app/entrypoint.sh
RUN if [ -f /app/run.py ]; then chmod +x /app/run.py; fi

# Create empty __init__.py files if they don't exist
RUN touch /app/__init__.py /app/ui/__init__.py /app/modules/__init__.py /app/utils/__init__.py

# Expose port
EXPOSE 7860

# Run entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 