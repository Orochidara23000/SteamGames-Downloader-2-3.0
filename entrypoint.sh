#!/bin/bash
# entrypoint.sh - Entry point for Steam Games Downloader container

set -e

# Set up environment
APP_DIR="/app"
DOWNLOAD_DIR="/data/downloads"
USER_ID=${PUID:-0}
GROUP_ID=${PGID:-0}

# Change to app directory
cd "$APP_DIR" || { echo "Error: Unable to change to app directory $APP_DIR"; exit 1; }

# Create download dir if it doesn't exist
if [ ! -d "$DOWNLOAD_DIR" ]; then
    echo "Creating directory $DOWNLOAD_DIR"
    mkdir -p "$DOWNLOAD_DIR"
    chown -R "$USER_ID":"$GROUP_ID" "$DOWNLOAD_DIR"
fi

# Show user information
echo "Running as user: $(id)"
echo
echo "Working directory: $(pwd)"
echo
echo "Steam download path: $DOWNLOAD_DIR"
echo

# Add directories to PYTHONPATH
export PYTHONPATH="$APP_DIR:$APP_DIR/ui:$APP_DIR/modules:$APP_DIR/utils"
echo "Python path: $PYTHONPATH"
echo

# Initialize directories function
initialize_directories() {
    echo "Creating necessary directories..."
    mkdir -p /root/steamcmd
    echo "✅ Created directory /root/steamcmd"
}

check_dependencies() {
    echo "Running initialization checks..."
    echo
    
    # Check data directory
    if [ -d "/data" ] && [ -w "/data" ]; then
        echo "✅ Directory /data exists and is writable"
    else
        echo "❌ Directory /data does not exist or is not writable"
        exit 1
    fi
    
    # Check download directory
    if [ -d "$DOWNLOAD_DIR" ] && [ -w "$DOWNLOAD_DIR" ]; then
        echo "✅ Directory $DOWNLOAD_DIR exists and is writable"
    else
        mkdir -p "$DOWNLOAD_DIR"
        echo "✅ Created directory $DOWNLOAD_DIR"
    fi
    
    # Check if root/steamcmd directory exists
    if [ ! -d "/root/steamcmd" ]; then
        initialize_directories
    fi
    
    echo "Checking system dependencies..."
    
    # Check python and pip
    if command -v python3 &> /dev/null; then
        echo "✅ python3 is installed"
    else
        echo "❌ python3 is not installed"
        exit 1
    fi
    
    if command -v pip3 &> /dev/null; then
        echo "✅ pip3 is installed"
    else
        echo "❌ pip3 is not installed"
        exit 1
    fi
    
    echo "Checking Python modules..."
    
    # Check required Python modules
    if python3 -c "import gradio" &> /dev/null; then
        echo "✅ gradio is installed"
    else
        echo "❌ gradio is not installed"
        pip3 install gradio
        echo "✅ gradio has been installed"
    fi
    
    if python3 -c "import pandas" &> /dev/null; then
        echo "✅ pandas is installed"
    else
        echo "❌ pandas is not installed"
        pip3 install pandas
        echo "✅ pandas has been installed"
    fi
    
    if python3 -c "import requests" &> /dev/null; then
        echo "✅ requests is installed"
    else
        echo "❌ requests is not installed"
        pip3 install requests
        echo "✅ requests has been installed"
    fi
}

# Run dependency checks
check_dependencies

# Check SteamCMD
if [ -e "/root/steamcmd/steamcmd.sh" ] && [ -e "/root/steamcmd/linux32/steamcmd" ]; then
    echo "✅ SteamCMD is installed"
else
    echo "⚠️ SteamCMD not found, will attempt to install it"
    # Create script to install SteamCMD
    python3 -c "from modules.steamcmd_manager import SteamCMD; SteamCMD().install_steamcmd()" || echo "Failed to install SteamCMD via Python module"
    if [ -e "/root/steamcmd/steamcmd.sh" ]; then
        echo "✅ SteamCMD installed successfully"
    else
        echo "❌ Failed to install SteamCMD"
        exit 1
    fi
fi

# Test SteamCMD
echo "Testing SteamCMD..."
/root/steamcmd/steamcmd.sh +quit

# Decide which script to run
if [ -f "app.py" ]; then
    echo "Using app.py launcher script..."
    python3 app.py
elif [ -f "simple.py" ]; then
    echo "Using simple launcher script..."
    python3 simple.py
elif [ -f "run.py" ]; then
    echo "Using run.py launcher script..."
    python3 run.py
else
    echo "No launcher script found. Attempting to run main.py..."
    if [ -f "main.py" ]; then
        python3 main.py
    else
        echo "Error: No suitable entry point found."
        exit 1
    fi
fi