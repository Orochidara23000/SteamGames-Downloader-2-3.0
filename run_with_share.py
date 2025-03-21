import os
import subprocess

# Set environment variables
os.environ["ENABLE_SHARE"] = "True"
os.environ["PORT"] = "7862"

print("Starting Steam Games Downloader with sharing enabled...")
# Run the main application
subprocess.run(["python", "main.py"]) 