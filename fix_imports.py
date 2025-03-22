#!/usr/bin/env python3
"""
Fix Imports Script

This script updates all imports in the project to use absolute imports instead of
relative imports, which can help resolve import errors in some Python environments.
"""

import os
import re
import glob

def fix_file_imports(file_path):
    """Fix imports in a single file"""
    print(f"Processing file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix relative imports from ui.* to direct imports
    content = re.sub(r'from ui\.', r'from ', content)
    content = re.sub(r'import ui\.', r'import ', content)
    
    # Fix relative imports from modules.* to direct imports
    content = re.sub(r'from modules\.', r'from ', content)
    content = re.sub(r'import modules\.', r'import ', content)
    
    # Fix relative imports from utils.* to direct imports
    content = re.sub(r'from utils\.', r'from ', content)
    content = re.sub(r'import utils\.', r'import ', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def process_directory(directory):
    """Process all Python files in a directory"""
    print(f"Processing directory: {directory}")
    
    files = glob.glob(os.path.join(directory, "*.py"))
    for file in files:
        fix_file_imports(file)

def main():
    """Main function"""
    print("Fixing imports in Python files...")
    
    # Fix imports in the main directory
    main_dir = os.path.dirname(os.path.abspath(__file__))
    main_files = [f for f in os.listdir(main_dir) if f.endswith('.py')]
    for file in main_files:
        fix_file_imports(os.path.join(main_dir, file))
    
    # Fix imports in subdirectories
    for subdir in ['ui', 'modules', 'utils']:
        subdir_path = os.path.join(main_dir, subdir)
        if os.path.exists(subdir_path) and os.path.isdir(subdir_path):
            process_directory(subdir_path)
    
    print("All imports fixed!")
    print("Note: You may need to adjust some imports manually if they're more complex.")

if __name__ == "__main__":
    main() 