#!/usr/bin/env python3
"""
Update Script for Steam Games Downloader

This script helps update the application by:
1. Checking for updates from the repository
2. Creating backups of important files
3. Applying updates safely
4. Migrating user data if needed
"""

import os
import sys
import time
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("Update")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Update Steam Games Downloader")
    parser.add_argument(
        "--backup", 
        action="store_true", 
        help="Create a backup before updating"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force update even if no updates are available"
    )
    parser.add_argument(
        "--skip-deps", 
        action="store_true", 
        help="Skip updating dependencies"
    )
    return parser.parse_args()

def create_backup():
    """Create a backup of important files and user data"""
    logger.info("Creating backup...")
    
    try:
        # Create backups directory if it doesn't exist
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        # Create a timestamped backup folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"backup_{timestamp}"
        backup_path.mkdir()
        
        # Files and directories to backup
        backup_items = [
            "data",
            "settings.json",
            "app.log"
        ]
        
        # Copy files and directories
        for item in backup_items:
            item_path = Path(item)
            if item_path.exists():
                if item_path.is_dir():
                    shutil.copytree(item_path, backup_path / item_path.name)
                else:
                    shutil.copy2(item_path, backup_path / item_path.name)
        
        logger.info(f"Backup created at {backup_path}")
        return str(backup_path)
    
    except Exception as e:
        logger.error(f"Failed to create backup: {str(e)}")
        return None

def check_for_updates():
    """Check if updates are available"""
    logger.info("Checking for updates...")
    
    try:
        # If this is a git repository, use git to check for updates
        if Path(".git").exists():
            try:
                # Fetch the latest changes
                subprocess.run(["git", "fetch"], check=True, capture_output=True)
                
                # Check if we're behind the remote
                result = subprocess.run(
                    ["git", "rev-list", "HEAD..origin/main", "--count"],
                    check=True, 
                    capture_output=True, 
                    text=True
                )
                
                commit_count = int(result.stdout.strip())
                if commit_count > 0:
                    logger.info(f"Updates available: {commit_count} new commits")
                    return True
                else:
                    logger.info("No updates available")
                    return False
                
            except subprocess.CalledProcessError as e:
                logger.warning(f"Git command failed: {e.stderr}")
                return False
            except ValueError:
                logger.warning("Failed to parse git output")
                return False
        else:
            # If not a git repository, check the version file
            if Path("__init__.py").exists():
                with open("__init__.py", "r") as f:
                    content = f.read()
                    if "__version__" in content:
                        logger.info("Version check would need to be done manually or online")
                        # In a real scenario, we would check against a remote version
                        return False
            
            logger.warning("Not a git repository and no version information found")
            return False
    
    except Exception as e:
        logger.error(f"Error checking for updates: {str(e)}")
        return False

def update_application(force=False):
    """Update the application code"""
    if not force and not check_for_updates():
        logger.info("No updates available. Use --force to update anyway.")
        return False
    
    logger.info("Updating application...")
    
    try:
        # If this is a git repository, use git to update
        if Path(".git").exists():
            try:
                # Pull the latest changes
                result = subprocess.run(
                    ["git", "pull", "origin", "main"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                logger.info(f"Git pull result: {result.stdout.strip()}")
                return "Already up to date." not in result.stdout
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Git pull failed: {e.stderr}")
                return False
        else:
            logger.warning("Not a git repository, can't automatically update")
            logger.info("Please download the latest version manually")
            return False
    
    except Exception as e:
        logger.error(f"Error updating application: {str(e)}")
        return False

def update_dependencies():
    """Update Python dependencies"""
    logger.info("Updating dependencies...")
    
    try:
        if Path("requirements.txt").exists():
            # Install or update requirements
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--upgrade"],
                check=True,
                capture_output=True,
                text=True
            )
            
            logger.info("Dependencies updated successfully")
            return True
        else:
            logger.warning("requirements.txt not found, skipping dependency update")
            return False
    
    except Exception as e:
        logger.error(f"Error updating dependencies: {str(e)}")
        return False

def migrate_user_data():
    """Migrate user data if needed after an update"""
    logger.info("Checking if data migration is needed...")
    
    # In a real application, you would implement version-specific migrations here
    # This is a placeholder for demonstration purposes
    
    return True

def main():
    """Main update function"""
    args = parse_args()
    
    logger.info("Starting update process...")
    
    # Create backup if requested
    if args.backup:
        backup_path = create_backup()
        if not backup_path:
            logger.error("Backup failed, aborting update")
            return 1
    
    # Update application
    app_updated = update_application(args.force)
    
    # Update dependencies unless skipped
    deps_updated = True
    if not args.skip_deps:
        deps_updated = update_dependencies()
    
    # Migrate user data if needed
    if app_updated:
        migration_successful = migrate_user_data()
        if not migration_successful:
            logger.error("Data migration failed")
            return 1
    
    # Report status
    if app_updated or deps_updated:
        logger.info("Update completed successfully")
    else:
        logger.info("No updates were applied")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 