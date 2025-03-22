#!/bin/bash
set -euo pipefail

# Print diagnostic information
echo "Starting Steam Downloader container..."
echo "Running as user: $(id)"
echo "Working directory: $(pwd)"
echo "Steam download path: ${STEAM_DOWNLOAD_PATH:-Not set}"
echo "Python path: ${PYTHONPATH:-Not set}"

# Ensure necessary directories exist and have proper permissions
mkdir -p /app/steamcmd /app/logs "${STEAM_DOWNLOAD_PATH}"
mkdir -p /app/ui /app/modules /app/utils /app/data
chmod 755 /app/steamcmd /app/logs "${STEAM_DOWNLOAD_PATH}"

# Ensure permissions are correct for the download directory
chown -R $(id -u):$(id -g) "${STEAM_DOWNLOAD_PATH}"
chmod -R 755 "${STEAM_DOWNLOAD_PATH}"

# Create empty __init__.py files if they don't exist
touch /app/__init__.py
touch /app/ui/__init__.py
touch /app/modules/__init__.py
touch /app/utils/__init__.py

# If SteamCMD exists, make sure it's executable
if [ -f "/app/steamcmd/steamcmd.sh" ]; then
    chmod +x /app/steamcmd/steamcmd.sh
fi

# Check if we need to use the new init_check.py file
if [ -f "init_check.py.new" ]; then
    echo "Using new initialization check script..."
    mv init_check.py.new init_check.py
fi

# Set PYTHONPATH if not already set
if [ -z "${PYTHONPATH:-}" ]; then
    export PYTHONPATH="/app:/app/ui:/app/modules:/app/utils"
    echo "Set PYTHONPATH to: $PYTHONPATH"
fi

# Run the diagnostic check first
echo "Running diagnostic checks..."
if ! python3 init_check.py; then
    echo "Diagnostic checks failed. Exiting."
    exit 1
fi

# Start the application and keep it running in the foreground
echo "Starting main application..."
if [ -f "run.py" ]; then
    echo "Using wrapper script run.py..."
    exec python3 run.py
else
    echo "Using main.py directly..."
    exec python3 main.py
fi