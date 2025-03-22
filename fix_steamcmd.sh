#!/bin/bash
# fix_steamcmd.sh - Repairs SteamCMD installation

echo "Fixing SteamCMD installation..."

# Create directory if it doesn't exist
mkdir -p /root/steamcmd
cd /root/steamcmd

# Download SteamCMD tarball
echo "Downloading SteamCMD..."
if command -v curl &> /dev/null; then
    curl -sqL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" | tar zxvf -
else
    wget -q "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" -O steamcmd_linux.tar.gz
    tar -xzvf steamcmd_linux.tar.gz
    rm steamcmd_linux.tar.gz
fi

# Make the script executable
chmod +x steamcmd.sh

# Create linux32 directory
mkdir -p linux32

# Copy steamcmd binary to linux32 directory
if [ -f "steamcmd" ]; then
    cp steamcmd linux32/
    chmod +x linux32/steamcmd
    echo "✅ Copied steamcmd to linux32/"
else
    echo "❌ steamcmd binary not found"
fi

# Create a simplified steamcmd.sh script
cat > steamcmd.sh << 'EOF'
#!/bin/bash
# Simple SteamCMD wrapper script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINARY="$SCRIPT_DIR/linux32/steamcmd"

if [ ! -f "$BINARY" ]; then
    echo "ERROR: SteamCMD binary not found at $BINARY"
    exit 1
fi

# Make sure it's executable
chmod +x "$BINARY"

# Run SteamCMD with all arguments
"$BINARY" "$@"
EOF

chmod +x steamcmd.sh

echo "✅ SteamCMD fixed successfully" 