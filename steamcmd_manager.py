#!/usr/bin/env python3
"""
SteamCMD Manager Module for Steam Games Downloader
Handles installation, verification and management of SteamCMD
"""

import os
import sys
import logging
import subprocess
import platform
import urllib.request
import shutil
import tarfile
import zipfile
import time
from pathlib import Path

# Configure logger
logger = logging.getLogger(__name__)

class SteamCMD:
    """
    Manages the SteamCMD installation and operations
    """
    
    def __init__(self, path=None):
        """Initialize SteamCMD manager"""
        try:
            # Set default path if not provided
            if path is None:
                if os.name == 'nt':  # Windows
                    path = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\steamcmd'), 'steamcmd')
                elif os.path.exists('/app'):  # Container
                    path = '/root/steamcmd'
                else:  # Linux/MacOS
                    path = os.path.join(os.path.expanduser('~'), 'steamcmd')
            
            self.path = Path(path)
            
            # Determine system type
            self.system = 'windows' if os.name == 'nt' else 'linux'
            if platform.system() == 'Darwin':
                self.system = 'macos'
            
            # In container flag
            self.in_container = self._check_if_container()
            
            logger.info(f"SteamCMD manager initialized with path: {self.path}")
            logger.info(f"Platform detected as: {self.system}")
            logger.info(f"Running in container: {self.in_container}")
            
            # Create directory if it doesn't exist
            self.path.mkdir(parents=True, exist_ok=True)
            
            # Set executable path based on system
            if self.system == 'windows':
                self.executable = self.path / 'steamcmd.exe'
            else:
                self.executable = self.path / 'steamcmd.sh'
            
            # URLs for downloading SteamCMD
            self.download_urls = {
                'windows': 'https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip',
                'linux': 'https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz',
                'macos': 'https://steamcdn-a.akamaihd.net/client/installer/steamcmd_osx.tar.gz'
            }
        
        except Exception as e:
            logger.error(f"Error initializing SteamCMD manager: {str(e)}")
            raise
    
    def _check_if_container(self):
        """Check if running in a container"""
        if os.path.exists('/.dockerenv'):
            return True
        if os.path.exists('/app') and os.path.exists('/data'):
            return True
        return False
    
    def is_installed(self):
        """Check if SteamCMD is installed"""
        return self.executable.exists()
    
    def install(self, force=False):
        """Install SteamCMD if not already installed"""
        try:
            if self.is_installed() and not force:
                logger.info("SteamCMD is already installed")
                return True
            
            logger.info(f"Installing SteamCMD to {self.path}")
            
            # Download SteamCMD
            download_url = self.download_urls.get(self.system)
            if not download_url:
                logger.error(f"No download URL available for {self.system}")
                return False
            
            # Define archive path based on system
            if self.system == 'windows':
                archive_path = self.path / 'steamcmd.zip'
            else:
                archive_path = self.path / 'steamcmd.tar.gz'
            
            # Download archive
            logger.info(f"Downloading SteamCMD from {download_url}")
            try:
                urllib.request.urlretrieve(download_url, archive_path)
            except Exception as e:
                logger.error(f"Failed to download SteamCMD: {str(e)}")
                
                # Attempt alternative download methods
                if self.system != 'windows':
                    try:
                        logger.info("Attempting to download with curl")
                        subprocess.run(
                            ["curl", "-sqL", download_url, "-o", str(archive_path)],
                            check=True
                        )
                    except:
                        try:
                            logger.info("Attempting to download with wget")
                            subprocess.run(
                                ["wget", "-q", download_url, "-O", str(archive_path)],
                                check=True
                            )
                        except:
                            logger.error("All download methods failed")
                            return False
            
            # Extract archive
            logger.info(f"Extracting SteamCMD to {self.path}")
            try:
                if self.system == 'windows':
                    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                        zip_ref.extractall(self.path)
                else:
                    with tarfile.open(archive_path, 'r:gz') as tar:
                        tar.extractall(path=self.path)
            except Exception as e:
                logger.error(f"Failed to extract SteamCMD: {str(e)}")
                return False
            
            # Make script executable on Unix-like systems
            if self.system != 'windows':
                try:
                    os.chmod(self.executable, 0o755)
                except:
                    logger.warning("Failed to make steamcmd.sh executable")
            
            # Clean up archive
            try:
                os.remove(archive_path)
            except:
                logger.warning(f"Failed to remove archive {archive_path}")
            
            # Run SteamCMD once to update
            logger.info("Running SteamCMD to complete setup")
            result = self.run_command("+quit")
            
            # Verify installation
            if self.is_installed():
                logger.info("SteamCMD installed successfully")
                return True
            else:
                logger.error("SteamCMD installation failed")
                return False
        
        except Exception as e:
            logger.error(f"Error installing SteamCMD: {str(e)}")
            return False
    
    def verify(self):
        """Verify SteamCMD installation"""
        try:
            if not self.is_installed():
                logger.warning("SteamCMD is not installed")
                return False
            
            # Run a simple command to check if SteamCMD works
            logger.info("Verifying SteamCMD installation")
            result = self.run_command("+quit")
            
            if result.returncode == 0:
                logger.info("SteamCMD verification successful")
                return True
            else:
                logger.warning("SteamCMD verification failed")
                return False
        
        except Exception as e:
            logger.error(f"Error verifying SteamCMD: {str(e)}")
            return False
    
    def run_command(self, command, capture_output=True):
        """Run a SteamCMD command"""
        try:
            if not self.is_installed():
                logger.error("Cannot run command, SteamCMD is not installed")
                class FakeResult:
                    def __init__(self):
                        self.returncode = 1
                        self.stdout = "SteamCMD not installed"
                        self.stderr = "Error: SteamCMD not installed"
                return FakeResult()
            
            # Build command
            if self.system == 'windows':
                cmd = [str(self.executable)]
            else:
                cmd = ["bash", str(self.executable)]
            
            # Add command
            cmd.append(command)
            
            # Run command
            logger.info(f"Running SteamCMD command: {' '.join(cmd)}")
            
            if capture_output:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
            else:
                result = subprocess.run(cmd, check=False)
            
            return result
        
        except Exception as e:
            logger.error(f"Error running SteamCMD command: {str(e)}")
            class FakeResult:
                def __init__(self, error):
                    self.returncode = 1
                    self.stdout = ""
                    self.stderr = f"Error: {error}"
            return FakeResult(str(e))
    
    def download_game(self, app_id, install_dir, platform=None, validate=True, username=None, password=None):
        """Download a game using SteamCMD"""
        try:
            if not self.is_installed():
                logger.error("Cannot download game, SteamCMD is not installed")
                return False, "SteamCMD is not installed"
            
            # Ensure install directory exists
            install_dir = Path(install_dir)
            install_dir.mkdir(parents=True, exist_ok=True)
            
            # Build command
            command = []
            
            # Login
            if username and password:
                command.append(f"+login {username} {password}")
            else:
                command.append("+login anonymous")
            
            # Set install directory
            command.append(f"+force_install_dir {install_dir}")
            
            # Set platform if specified
            if platform and platform != "windows":
                command.append(f"+@sSteamCmdForcePlatformType {platform}")
            
            # Download app
            validate_flag = " validate" if validate else ""
            command.append(f"+app_update {app_id}{validate_flag}")
            
            # Quit
            command.append("+quit")
            
            # Join commands
            cmd_str = " ".join(command)
            
            # Run command
            logger.info(f"Downloading game {app_id} to {install_dir}")
            result = self.run_command(cmd_str, capture_output=True)
            
            if result.returncode == 0:
                logger.info(f"Game {app_id} downloaded successfully")
                return True, "Download completed successfully"
            else:
                logger.error(f"Game {app_id} download failed: {result.stderr}")
                return False, f"Download failed: {result.stderr}"
        
        except Exception as e:
            logger.error(f"Error downloading game {app_id}: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def fix_installation(self):
        """Attempt to fix SteamCMD installation"""
        try:
            logger.info("Attempting to fix SteamCMD installation")
            
            # Check if fix script exists and we're in a container
            fix_script = "/app/fix_steamcmd.sh"
            if self.in_container and os.path.exists(fix_script):
                logger.info(f"Running fix script: {fix_script}")
                subprocess.run(
                    ["bash", fix_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                # Verify installation
                if self.verify():
                    logger.info("SteamCMD installation fixed with script")
                    return True
            
            # If script doesn't exist or didn't fix the issue, force reinstall
            logger.info("Reinstalling SteamCMD")
            
            # Remove installation if it exists
            if self.path.exists():
                try:
                    shutil.rmtree(self.path)
                    logger.info(f"Removed existing SteamCMD installation at {self.path}")
                except:
                    logger.warning(f"Failed to remove directory {self.path}")
            
            # Install SteamCMD
            if self.install(force=True):
                logger.info("SteamCMD reinstalled successfully")
                return True
            else:
                logger.error("Failed to fix SteamCMD installation")
                return False
        
        except Exception as e:
            logger.error(f"Error fixing SteamCMD installation: {str(e)}")
            return False

# Singleton instance
_instance = None

def get_steamcmd(path=None):
    """Get the singleton SteamCMD instance"""
    global _instance
    if _instance is None:
        _instance = SteamCMD(path)
    return _instance

# For direct testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Get SteamCMD instance
    steamcmd = get_steamcmd()
    
    # Check if installed
    if not steamcmd.is_installed():
        print("SteamCMD is not installed. Installing...")
        steamcmd.install()
    else:
        print("SteamCMD is already installed. Verifying...")
        steamcmd.verify()
    
    # Print status
    print(f"SteamCMD path: {steamcmd.path}")
    print(f"SteamCMD executable: {steamcmd.executable}")
    print(f"System type: {steamcmd.system}")
    print(f"In container: {steamcmd.in_container}")