#!/bin/bash
set -e

# Show environment info
echo "Running as user: $(id)"
echo "Working directory: $(pwd)"
echo "Steam download path: $STEAM_DOWNLOAD_PATH"

# Set Python path to include our directories
export PYTHONPATH="/app:/app/ui:/app/modules:/app/utils"
echo "Python path: $PYTHONPATH"

# Run initialization checks
echo "Running initialization checks..."

# Check if data directories are writable
for dir in "/data" "/data/downloads" "/root/steamcmd"; do
    if [ -d "$dir" ]; then
        if [ -w "$dir" ]; then
            echo "✅ Directory $dir exists and is writable"
        else
            echo "❌ Directory $dir exists but is not writable"
            exit 1
        fi
    else
        echo "Creating directory $dir"
        mkdir -p "$dir"
        if [ $? -ne 0 ]; then
            echo "❌ Failed to create directory $dir"
            exit 1
        fi
        echo "✅ Created directory $dir"
    fi
done

# Check for required system dependencies
echo "Checking system dependencies..."
for cmd in python3 pip3; do
    if command -v $cmd >/dev/null 2>&1; then
        echo "✅ $cmd is installed"
    else
        echo "❌ $cmd is not installed"
        exit 1
    fi
done

# Check for required Python modules
echo "Checking Python modules..."
python3 -c "
import sys
required = ['gradio', 'pandas', 'requests']
missing = []
for module in required:
    try:
        __import__(module)
        print(f'✅ {module} is installed')
    except ImportError:
        missing.append(module)
        print(f'❌ {module} is not installed')
if missing:
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "Installing missing Python modules..."
    pip3 install gradio pandas requests
fi

# Check for SteamCMD
if [ -f "/root/steamcmd/steamcmd.sh" ]; then
    echo "✅ SteamCMD is installed"
else
    echo "⚠️ SteamCMD not found, will attempt to install it"
    mkdir -p /root/steamcmd
    cd /root/steamcmd
    curl -sqL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" | tar zxvf -
    if [ -f "/root/steamcmd/steamcmd.sh" ]; then
        echo "✅ SteamCMD installed successfully"
        # Test SteamCMD
        echo "Testing SteamCMD..."
        ./steamcmd.sh +quit
        if [ $? -eq 0 ]; then
            echo "✅ SteamCMD working correctly"
        else
            echo "⚠️ SteamCMD test failed, but continuing anyway"
        fi
    else
        echo "⚠️ SteamCMD installation failed, but continuing anyway"
    fi
    cd /app
fi

echo "All checks passed, starting application..."

# Prioritize using simple.py if it exists
if [ -f "simple.py" ]; then
    echo "Using simple launcher script..."
    exec python3 simple.py
# Otherwise try run.py
elif [ -f "run.py" ]; then
    echo "Using run.py script..."
    exec python3 run.py
# Fall back to main.py if available
elif [ -f "main.py" ]; then
    echo "Using main.py script..."
    exec python3 main.py
# Final fallback
else
    echo "No launcher script found, using python -m gradio..."
    exec python3 -m gradio ui/main_ui.py
fi