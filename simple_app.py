import gradio as gr
import os
import platform
import time
import logging
import json
from datetime import datetime

# Configure minimal logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

def get_default_download_location():
    """Get the default download location based on platform"""
    home = os.path.expanduser("~")
    if platform.system() == "Windows":
        return os.path.join(home, "SteamLibrary")
    elif platform.system() == "Darwin":  # macOS
        return os.path.join(home, "Library", "Application Support", "SteamLibrary")
    else:  # Linux and other Unix-like systems
        return os.path.join(home, "SteamLibrary")

def parse_game_input(input_str):
    """Extract a Steam AppID from user input."""
    if not input_str or input_str.strip() == "":
        return None
    
    # If input is just a number, assume it's an AppID
    if input_str.strip().isdigit():
        return input_str.strip()
    
    return None

def handle_game_check(input_text):
    """Check the game details from user input"""
    logger.info(f"Game check requested for: {input_text}")
    
    # Simple validation
    appid = parse_game_input(input_text)
    if not appid:
        return [
            None, 
            gr.update(visible=False), 
            None, 
            None, 
            None, 
            None, 
            "Invalid input. Please enter a valid Steam AppID."
        ]
    
    # Mock game info for testing
    game_info = {
        "name": f"Game {appid}",
        "short_description": "This is a test game description for diagnostic purposes.",
        "size_estimate": 1500000000
    }
    
    # Return mock data
    return [
        game_info,  # Store the full game info JSON
        gr.update(visible=True),  # Show the game details container
        None,  # Game image - none for test
        f"Game {appid}",  # Game title
        "This is a test game description for diagnostic purposes.",  # Game description
        "Estimated size: 1.5 GB",  # Estimated size
        f"Game found: Game {appid}. Ready to download."  # Status message
    ]

def handle_download(game_input_text, username_val, password_val, guard_code_val, 
                  anonymous_val, validate_val, game_info_json):
    """Handle game download request (mock implementation)"""
    logger.info(f"Download requested for: {game_input_text}")
    
    # Validate inputs
    if not game_input_text:
        return "Please enter a game ID."
        
    if not anonymous_val and (not username_val or not password_val):
        return "Steam username and password are required for non-anonymous downloads."
    
    # Parse game input
    appid = parse_game_input(game_input_text)
    if not appid:
        return "Invalid game ID format."
    
    # Simulate starting a download
    time.sleep(1)  # Small delay to simulate work
    
    return f"Download started for Game {appid}. This is a simulated download in diagnostic mode."

def handle_queue(game_input_text, username_val, password_val, guard_code_val, 
                anonymous_val, validate_val, game_info_json):
    """Add a game to download queue (mock implementation)"""
    logger.info(f"Queue requested for: {game_input_text}")
    
    # Validate inputs
    if not game_input_text:
        return "Please enter a game ID."
    
    # Parse game input
    appid = parse_game_input(game_input_text)
    if not appid:
        return "Invalid game ID format."
    
    # Simulate adding to queue
    time.sleep(0.5)  # Small delay to simulate work
    
    return f"Added Game {appid} to download queue. (Simulated in diagnostic mode)"

def toggle_login_visibility(anonymous):
    """Show/hide login fields based on anonymous selection"""
    return gr.update(visible=not anonymous)

def create_download_games_tab():
    """Create the main download tab interface"""
    with gr.Tab("Download Games") as tab:
        with gr.Row():
            with gr.Column(scale=2):
                # Game Information Section
                with gr.Group():
                    gr.Markdown("### Game Information")
                    
                    game_input = gr.Textbox(
                        label="Game ID",
                        placeholder="Enter AppID (e.g., 570)",
                        info="Enter a valid Steam game ID"
                    )
                    
                    check_button = gr.Button("Check Game Details", variant="secondary")
                    
                    game_info_json = gr.JSON(visible=False)
                    
                    with gr.Row(visible=False) as game_details_container:
                        game_image = gr.Image(label="Game Image", show_label=False, type="filepath")
                        
                        with gr.Column():
                            game_title = gr.Textbox(label="Game", interactive=False)
                            game_description = gr.Textbox(label="Description", interactive=False, max_lines=3)
                            game_size = gr.Textbox(label="Estimated Size", interactive=False)
                
                # Account Information Section
                with gr.Group():
                    gr.Markdown("### Steam Account")
                    
                    anonymous_login = gr.Checkbox(
                        label="Anonymous Login (Free Games Only)",
                        value=True,
                        info="Use for free games. Paid games require login."
                    )
                    
                    with gr.Column(visible=False) as login_container:
                        username = gr.Textbox(
                            label="Steam Username",
                            placeholder="Your Steam account username"
                        )
                        password = gr.Textbox(
                            label="Steam Password",
                            placeholder="Your Steam account password",
                            type="password",
                            info="Credentials are only used for the current session and not stored"
                        )
                        
                        with gr.Accordion("Steam Guard (if enabled)", open=False):
                            guard_code = gr.Textbox(
                                label="Steam Guard Code",
                                placeholder="Enter the code sent to your email or mobile app",
                                info="Required if Steam Guard is enabled on your account"
                            )
                
                # Download Options Section
                with gr.Group():
                    gr.Markdown("### Download Options")
                    
                    download_path = gr.Textbox(
                        label="Download Location",
                        value=get_default_download_location(),
                        interactive=False,
                        info="Set in application settings"
                    )
                    
                    validate_download = gr.Checkbox(
                        label="Verify Files After Download",
                        value=True,
                        info="Recommended to ensure download integrity"
                    )
                    
                    with gr.Row():
                        download_button = gr.Button("Download Now", variant="primary")
                        queue_button = gr.Button("Add to Queue", variant="secondary")
            
            # Right column for help/information
            with gr.Column(scale=1):
                gr.Markdown("### Download Information")
                gr.Markdown("""
                - Free games can be downloaded with Anonymous Login
                - Paid games require your Steam account credentials
                - Your credentials are never stored
                - Downloads will be placed in the configured directory
                - You can queue multiple downloads
                """)
                
                gr.Markdown("### Status")
                status_box = gr.Textbox(label="", interactive=False)
        
        # Event handlers
        anonymous_login.change(fn=toggle_login_visibility, inputs=anonymous_login, outputs=login_container)
        
        check_button.click(
            fn=handle_game_check,
            inputs=game_input,
            outputs=[game_info_json, game_details_container, game_image, game_title, 
                     game_description, game_size, status_box]
        )
        
        download_button.click(
            fn=handle_download,
            inputs=[game_input, username, password, guard_code, anonymous_login, 
                   validate_download, game_info_json],
            outputs=[status_box]
        )
        
        queue_button.click(
            fn=handle_queue,
            inputs=[game_input, username, password, guard_code, anonymous_login, 
                   validate_download, game_info_json],
            outputs=[status_box]
        )
    
    return tab

def create_simplified_interface():
    """Create a simplified gradio interface"""
    with gr.Blocks(title="Steam Games Downloader - Diagnostic Mode") as app:
        gr.Markdown("# Steam Games Downloader (Diagnostic Mode)")
        gr.Markdown("This is a simplified version for testing")
        
        with gr.Tabs():
            download_tab = create_download_games_tab()
    
    return app

if __name__ == "__main__":
    print("="*50)
    print("Starting Steam Downloader in DIAGNOSTIC MODE")
    print("This is a simplified version for troubleshooting")
    print("="*50)
    
    app = create_simplified_interface()
    
    # Launch with minimal options and debug mode
    app.launch(
        server_port=7861,
        server_name="0.0.0.0",
        share=True,
        debug=True
    ) 