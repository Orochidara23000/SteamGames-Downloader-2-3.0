"""
Settings Tab for Steam Games Downloader
"""

import logging
import gradio as gr
import os

# Configure logger
logger = logging.getLogger(__name__)

class SettingsTab:
    """Settings Tab for Steam Games Downloader"""
    
    def __init__(self):
        """Initialize the settings tab"""
        logger.info("Initializing Settings Tab")
    
    def create_tab(self):
        """Create the settings tab UI"""
        with gr.Column():
            gr.Markdown("## Settings")
            gr.Markdown("This is a minimal implementation of the settings tab.")
            
            with gr.Row():
                download_path = gr.Textbox(
                    label="Download Path",
                    value="/data/downloads",
                    interactive=True
                )
                
                steamcmd_path = gr.Textbox(
                    label="SteamCMD Path",
                    value="/root/steamcmd",
                    interactive=True
                )
            
            # Login settings
            with gr.Row():
                anonymous_login = gr.Checkbox(
                    label="Use Anonymous Login",
                    value=True,
                    interactive=True
                )
            
            with gr.Row(visible=False) as login_row:
                username = gr.Textbox(
                    label="Steam Username",
                    interactive=True
                )
                
                password = gr.Textbox(
                    label="Steam Password",
                    type="password",
                    interactive=True
                )
            
            # Make login fields visible based on anonymous login checkbox
            anonymous_login.change(
                fn=lambda x: gr.Row(visible=not x),
                inputs=[anonymous_login],
                outputs=[login_row]
            )
            
            # Buttons
            with gr.Row():
                test_btn = gr.Button("Test SteamCMD")
                save_btn = gr.Button("Save Settings")
                reset_btn = gr.Button("Reset to Defaults")
            
            result = gr.Textbox(label="Result")
            
            # Test SteamCMD function
            def test_steamcmd(steamcmd_path):
                try:
                    if not steamcmd_path:
                        return "SteamCMD path is empty"
                    
                    if not os.path.exists(steamcmd_path):
                        return f"SteamCMD path {steamcmd_path} does not exist"
                    
                    # Check for steamcmd.sh
                    script_path = os.path.join(steamcmd_path, "steamcmd.sh")
                    if not os.path.exists(script_path):
                        return f"SteamCMD script not found at {script_path}"
                    
                    # Test SteamCMD
                    import subprocess
                    process = subprocess.run(
                        [script_path, "+quit"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
                    
                    if process.returncode == 0:
                        return "SteamCMD is working correctly"
                    else:
                        return f"SteamCMD test failed with error: {process.stderr}"
                
                except Exception as e:
                    logger.error(f"Error testing SteamCMD: {str(e)}")
                    return f"Error: {str(e)}"
            
            # Connect events
            test_btn.click(
                fn=test_steamcmd,
                inputs=[steamcmd_path],
                outputs=[result]
            )

# Singleton instance
_instance = None

def get_settings_tab():
    """Get the singleton settings tab instance"""
    global _instance
    if _instance is None:
        _instance = SettingsTab()
    return _instance

# For testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create tab
    settings_tab = get_settings_tab()
    
    # Create interface
    with gr.Blocks() as interface:
        settings_tab.create_tab()
    
    # Launch interface
    interface.launch(server_name="0.0.0.0", server_port=7860) 