import gradio as gr
import os
import sys
import logging
from main import create_download_games_tab, toggle_login_visibility

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting Hugging Face Spaces application")

# Minimally required functions
def handle_game_check(input_text):
    logger.info(f"Game check requested for: {input_text}")
    return [None, gr.update(visible=True), None, f"Game {input_text}", 
            "Test game description for Hugging Face Spaces deployment.", 
            "Estimated size: 1.5 GB", f"Game found: {input_text}. Ready to download."]

def handle_download(game_input_text, username_val, password_val, guard_code_val, 
                  anonymous_val, validate_val, game_info_json):
    logger.info(f"Download requested for: {game_input_text}")
    
    # This is a demo for Hugging Face Spaces
    return "This is a demo deployment on Hugging Face Spaces. Downloads are simulated only."

def handle_queue(game_input_text, username_val, password_val, guard_code_val, 
                anonymous_val, validate_val, game_info_json):
    logger.info(f"Queue requested for: {game_input_text}")
    
    # This is a demo for Hugging Face Spaces
    return "This is a demo deployment on Hugging Face Spaces. Queue functionality is simulated only."

def get_default_download_location():
    return "/content/downloads"

def parse_game_input(input_str):
    return input_str if input_str and input_str.strip().isdigit() else None

# Create the application interface
with gr.Blocks(title="Steam Games Downloader - Hugging Face Demo") as app:
    gr.Markdown("# Steam Games Downloader (Hugging Face Spaces Demo)")
    gr.Markdown("""
    This is a demo deployment of the Steam Games Downloader.
    
    In this demo, game downloads are simulated and not actually processed. 
    For a full functional version, please deploy using Docker or run locally.
    """)
    
    with gr.Tabs():
        download_tab = create_download_games_tab()

# Export for Hugging Face Spaces
if __name__ == "__main__":
    app.launch() 