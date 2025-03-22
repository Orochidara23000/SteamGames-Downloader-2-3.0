"""
Main UI component for Steam Games Downloader
"""

import os
import sys
import logging
import gradio as gr
import importlib
import time
import traceback
from pathlib import Path

# Configure logger
logger = logging.getLogger(__name__)

def safe_import(module_name, path_hints=None):
    """Safely import a module with detailed error logging and fallback attempts"""
    logger.debug(f"Attempting to import {module_name}")
    
    # Try direct import first
    try:
        module = importlib.import_module(module_name)
        logger.debug(f"Successfully imported {module_name}")
        return module
    except ImportError as e:
        logger.debug(f"Direct import of {module_name} failed: {str(e)}")
    
    # If path hints are provided, try each one
    if path_hints:
        for path in path_hints:
            try:
                # Add path to sys.path if not already there
                if path not in sys.path:
                    logger.debug(f"Adding {path} to sys.path")
                    sys.path.append(path)
                
                # Try import again
                module = importlib.import_module(module_name)
                logger.debug(f"Successfully imported {module_name} after adding {path} to sys.path")
                return module
            except ImportError as e:
                logger.debug(f"Import of {module_name} failed after adding {path} to sys.path: {str(e)}")
    
    # If still not imported, try relative imports
    try:
        relative_module = '.' + module_name
        module = importlib.import_module(relative_module, package='ui')
        logger.debug(f"Successfully imported {module_name} as relative import")
        return module
    except ImportError as e:
        logger.debug(f"Relative import of {module_name} failed: {str(e)}")
    
    # Final attempt: check if the module file exists in the current directory
    module_file = f"{module_name}.py"
    if os.path.exists(module_file):
        logger.debug(f"Found {module_file} in current directory")
        # Use importlib.util directly for more control
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            if spec:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                logger.debug(f"Successfully imported {module_name} from file {module_file}")
                return module
        except Exception as e:
            logger.debug(f"Failed to import {module_name} from file {module_file}: {str(e)}")
    
    # If all attempts failed, raise an ImportError
    logger.error(f"All import attempts for {module_name} failed")
    raise ImportError(f"Failed to import {module_name} after multiple attempts")

class MainUI:
    """Main UI for the Steam Games Downloader application"""
    
    def __init__(self):
        """Initialize the main UI"""
        logger.info("Initializing Main UI")
        
        # Load tabs
        try:
            # Try different import paths for flexibility in different environments
            path_hints = [
                os.path.abspath('ui'),
                os.path.join(os.path.dirname(__file__)),
                os.path.abspath('.')
            ]
            
            # Try to import tabs - if any fail, log but continue
            try:
                self.download_tab = safe_import('download_tab', path_hints).get_download_tab()
                logger.info("Successfully imported download_tab")
            except Exception as e:
                logger.error(f"Error importing download_tab: {str(e)}")
                self.download_tab = None
            
            try:
                self.library_tab = safe_import('library_tab', path_hints).get_library_tab()
                logger.info("Successfully imported library_tab")
            except Exception as e:
                logger.error(f"Error importing library_tab: {str(e)}")
                self.library_tab = None
            
            try:
                self.settings_tab = safe_import('settings_tab', path_hints).get_settings_tab()
                logger.info("Successfully imported settings_tab")
            except Exception as e:
                logger.error(f"Error importing settings_tab: {str(e)}")
                self.settings_tab = None
                
        except Exception as e:
            logger.error(f"Error during tab imports: {str(e)}")
            logger.error(traceback.format_exc())
    
    def create_ui(self):
        """Create and return the Gradio UI interface"""
        try:
            # Create interface with tabs
            interface = gr.Blocks(
                title="Steam Games Downloader",
                theme=gr.themes.Soft(primary_hue="blue", secondary_hue="slate"),
                css=self._get_custom_css()
            )
            
            with interface:
                gr.Markdown("# Steam Games Downloader")
                
                with gr.Tabs() as tabs:
                    # Only create tabs that loaded successfully
                    if self.download_tab is not None:
                        with gr.Tab("Download", id="download_tab"):
                            try:
                                self.download_tab.create_tab()
                            except Exception as e:
                                logger.error(f"Error creating download_tab: {str(e)}")
                                gr.Markdown("## Error loading Download Tab")
                                gr.Markdown(f"An error occurred: {str(e)}")
                    
                    if self.library_tab is not None:
                        with gr.Tab("Library", id="library_tab"):
                            try:
                                self.library_tab.create_tab()
                            except Exception as e:
                                logger.error(f"Error creating library_tab: {str(e)}")
                                gr.Markdown("## Error loading Library Tab")
                                gr.Markdown(f"An error occurred: {str(e)}")
                    
                    if self.settings_tab is not None:
                        with gr.Tab("Settings", id="settings_tab"):
                            try:
                                self.settings_tab.create_tab()
                            except Exception as e:
                                logger.error(f"Error creating settings_tab: {str(e)}")
                                gr.Markdown("## Error loading Settings Tab")
                                gr.Markdown(f"An error occurred: {str(e)}")
                    
                    # If no tabs loaded, add a fallback tab
                    if not any([self.download_tab, self.library_tab, self.settings_tab]):
                        with gr.Tab("Status", id="status_tab"):
                            gr.Markdown("## Steam Games Downloader")
                            gr.Markdown("No UI components could be loaded. See logs for more information.")
            
            logger.info("UI interface created successfully")
            return interface
        
        except Exception as e:
            logger.error(f"Error creating UI interface: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Create a fallback interface
            fallback = gr.Blocks(title="Steam Games Downloader - Error")
            with fallback:
                gr.Markdown("# Steam Games Downloader")
                gr.Markdown("## Error Starting Application")
                gr.Markdown(f"An error occurred: {str(e)}")
                gr.Markdown("Please check the logs for more information.")
            
            return fallback
    
    def _get_custom_css(self):
        """Return custom CSS for the UI"""
        return """
        .status-pending { color: #6c757d; }
        .status-downloading { color: #007bff; font-weight: bold; }
        .status-completed { color: #28a745; font-weight: bold; }
        .status-failed { color: #dc3545; font-weight: bold; }
        .status-cancelled { color: #6c757d; font-style: italic; }
        
        /* Make table more compact */
        .gr-dataframe { font-size: 0.9em; }
        
        /* Better spacing */
        .container { margin: 0.5em 0; }
        """

# Singleton instance
_instance = None

def get_main_ui():
    """Get the singleton main UI instance"""
    global _instance
    if _instance is None:
        _instance = MainUI()
    return _instance

def create_ui():
    """Create the Gradio interface"""
    logger.info("Creating simple UI interface")
    
    interface = gr.Blocks(
        title="Steam Games Downloader",
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="slate")
    )
    
    with interface:
        gr.Markdown("# Steam Games Downloader")
        gr.Markdown("### Minimal Interface")
        
        simple_ui = SimpleUI()
        simple_ui.create_tab()
    
    logger.info("UI interface created successfully")
    return interface

# For testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and launch UI
    ui = create_ui()
    ui.launch(server_name="0.0.0.0", server_port=7860) 