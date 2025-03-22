#!/usr/bin/env python3
"""
Application Structure Checker

This script checks if the application structure is correct and if
modules can be imported correctly.
"""

import os
import sys
import importlib
import traceback

def print_separator():
    """Print a separator line"""
    print("-" * 80)

def check_directory(directory):
    """Check if a directory exists and has the expected files"""
    print(f"Checking directory: {directory}")
    
    if not os.path.exists(directory):
        print(f"  ERROR: Directory '{directory}' does not exist")
        return False
    
    if not os.path.isdir(directory):
        print(f"  ERROR: '{directory}' is not a directory")
        return False
    
    print(f"  OK: Directory '{directory}' exists")
    
    # Check if it has __init__.py
    init_file = os.path.join(directory, "__init__.py")
    if os.path.exists(init_file):
        print(f"  OK: '{directory}/__init__.py' exists")
    else:
        print(f"  WARNING: '{directory}/__init__.py' does not exist")
        print(f"  Creating empty __init__.py file...")
        try:
            with open(init_file, "w") as f:
                f.write('"""' + directory + ' package"""')
            print(f"  OK: Created '{init_file}'")
        except Exception as e:
            print(f"  ERROR: Failed to create '{init_file}': {str(e)}")
    
    # List files in directory
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    print(f"  Files in '{directory}':")
    for file in files:
        if file.endswith(".py"):
            print(f"    - {file}")
    
    return True

def check_python_path():
    """Check Python path"""
    print("Checking Python path:")
    
    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Current directory: {current_dir}")
    
    # Check if current directory is in Python path
    if current_dir in sys.path:
        print(f"  OK: Current directory is in Python path")
    else:
        print(f"  WARNING: Current directory is not in Python path")
        print(f"  Adding current directory to Python path...")
        sys.path.insert(0, current_dir)
        print(f"  OK: Added current directory to Python path")
    
    # Print Python path
    print("Python path:")
    for path in sys.path:
        print(f"  - {path}")
    
    return True

def try_import(module_name):
    """Try to import a module"""
    print(f"Trying to import module: {module_name}")
    
    try:
        module = importlib.import_module(module_name)
        print(f"  OK: Module '{module_name}' imported successfully")
        return True
    except ImportError as e:
        print(f"  ERROR: Failed to import module '{module_name}': {str(e)}")
        traceback.print_exc()
        return False

def fix_imports():
    """Try to fix import issues"""
    print("Attempting to fix import issues...")
    
    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add important directories to path
    for directory in ["", "ui", "modules", "utils"]:
        dir_path = os.path.join(current_dir, directory)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            if dir_path not in sys.path:
                sys.path.insert(0, dir_path)
                print(f"  Added '{dir_path}' to Python path")
    
    # Create empty __init__.py files if they don't exist
    for directory in ["ui", "modules", "utils"]:
        dir_path = os.path.join(current_dir, directory)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            init_file = os.path.join(dir_path, "__init__.py")
            if not os.path.exists(init_file):
                try:
                    with open(init_file, "w") as f:
                        f.write('"""' + directory + ' package"""')
                    print(f"  Created '{init_file}'")
                except Exception as e:
                    print(f"  ERROR: Failed to create '{init_file}': {str(e)}")
    
    # Create empty __init__.py in current directory if it doesn't exist
    init_file = os.path.join(current_dir, "__init__.py")
    if not os.path.exists(init_file):
        try:
            with open(init_file, "w") as f:
                f.write('"""SteamGames Downloader package"""')
            print(f"  Created '{init_file}'")
        except Exception as e:
            print(f"  ERROR: Failed to create '{init_file}': {str(e)}")
    
    return True

def main():
    """Main function"""
    print_separator()
    print("STEAM GAMES DOWNLOADER - STRUCTURE CHECKER")
    print_separator()
    
    # Check Python path
    check_python_path()
    print_separator()
    
    # Check directories
    directories = ["ui", "modules", "utils"]
    for directory in directories:
        check_directory(directory)
        print_separator()
    
    # Try imports before fixes
    print("Testing imports before fixes:")
    try_import("ui")
    try_import("modules")
    try_import("utils")
    try_import("ui.main_ui")
    print_separator()
    
    # Fix imports
    fix_imports()
    print_separator()
    
    # Try imports after fixes
    print("Testing imports after fixes:")
    try_import("ui")
    try_import("modules")
    try_import("utils")
    try_import("ui.main_ui")
    print_separator()
    
    print("Check complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 