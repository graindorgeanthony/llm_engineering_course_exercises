"""
Utility functions for logging and colors
"""
import logging
import sys

# Foreground colors
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[94m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'

# Background colors
BG_BLACK = '\033[40m'
BG_BLUE = '\033[44m'

# Reset code
RESET = '\033[0m'

# HTML color mapper for Gradio
HTML_COLOR_MAP = {
    BG_BLACK + RED: "#dd0000",
    BG_BLACK + GREEN: "#00dd00",
    BG_BLACK + YELLOW: "#dddd00",
    BG_BLACK + BLUE: "#4da3ff",
    BG_BLACK + MAGENTA: "#aa00dd",
    BG_BLACK + CYAN: "#00dddd",
    BG_BLACK + WHITE: "#87CEEB",
    BG_BLUE + WHITE: "#ff7800"
}


def init_logging():
    """
    Initialize logging configuration
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [Agents] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


def reformat_for_html(message: str) -> str:
    """
    Convert terminal color codes to HTML color spans for Gradio
    """
    for key, value in HTML_COLOR_MAP.items():
        message = message.replace(key, f'<span style="color: {value}">')
    message = message.replace(RESET, '</span>')
    return message


class BaseAgent:
    """
    Base class for all agents with consistent logging
    """
    name: str = "Agent"
    color: str = WHITE

    def log(self, message: str):
        """
        Log a message with agent identification and color
        """
        color_code = BG_BLACK + self.color
        formatted_message = f"[{self.name}] {message}"
        logging.info(color_code + formatted_message + RESET)
