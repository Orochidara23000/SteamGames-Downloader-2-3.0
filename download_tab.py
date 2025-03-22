"""
Download Tab for Steam Games Downloader
"""

import logging
import gradio as gr

# Configure logger
logger = logging.getLogger(__name__)

class DownloadTab:
    """Download Tab for Steam Games Downloader"""
    
    def __init__(self):
        """Initialize the download tab"""
        logger.info("Initializing Download Tab")
    
    def create_tab(self):
        """Create the download tab UI"""
        with gr.Column():
            gr.Markdown("## Download Games")
            gr.Markdown("This is a minimal implementation of the download tab.")
            
            with gr.Row():
                app_id = gr.Textbox(label="App ID")
                app_name = gr.Textbox(label="Game Name")
            
            download_btn = gr.Button("Download Game")
            result = gr.Textbox(label="Result")
            
            def download_game(app_id, app_name):
                if not app_id:
                    return "Please enter an App ID"
                if not app_name:
                    return "Please enter a Game Name"
                
                try:
                    # Import download manager
                    from download_manager import get_download_manager
                    dm = get_download_manager()
                    
                    # Add download
                    dl_id = dm.add_download(app_id, app_name)
                    
                    if dl_id:
                        return f"Download started with ID: {dl_id}"
                    else:
                        return "Failed to start download"
                except Exception as e:
                    logger.error(f"Error starting download: {str(e)}")
                    return f"Error: {str(e)}"
            
            download_btn.click(download_game, inputs=[app_id, app_name], outputs=[result])

# Singleton instance
_instance = None

def get_download_tab():
    """Get the singleton download tab instance"""
    global _instance
    if _instance is None:
        _instance = DownloadTab()
    return _instance

# For testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create tab
    download_tab = get_download_tab()
    
    # Create interface
    with gr.Blocks() as interface:
        download_tab.create_tab()
    
    # Launch interface
    interface.launch(server_name="0.0.0.0", server_port=7860) 