#!/usr/bin/env python3
"""
Wrapper script for Steam Games Downloader

This script ensures the correct Python path is set before running the application.
"""

import os
import sys
import subprocess

# Get the absolute path of the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Ensure current directory is in Python path
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Ensure subdirectories are in Python path
for subdir in ["ui", "modules", "utils"]:
    subdir_path = os.path.join(current_dir, subdir)
    if os.path.isdir(subdir_path) and subdir_path not in sys.path:
        sys.path.insert(0, subdir_path)

# Print Python path for debugging
print("Python path:")
for path in sys.path:
    print(f"  - {path}")

# Run the main application
try:
    print("Starting Steam Games Downloader...")
    import main
    main.main()
except ImportError as e:
    print(f"Import error: {str(e)}")
    print("Make sure the project structure is correct with 'ui', 'modules', and 'utils' directories")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {str(e)}")
    sys.exit(1) 