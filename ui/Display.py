# Reusable terminal display helpers for the e-voting system.

from utils.colors import (
    RESET,
    BOLD,
    DIM,
    YELLOW,
    RED,
    GREEN,
    GRAY,
    BRIGHT_WHITE,
)
from utils.display import (
    colored,
    header,
    subheader,
    table_header,
    table_divider,
    prompt,
    clear_screen,
    pause,
)
from utils.helpers import masked_input


def display_error(msg):
    """Display an error message."""
    print(f"  {RED}{BOLD} {msg}{RESET}")


def display_success(msg):
    """Display a success message."""
    print(f"  {GREEN}{BOLD} {msg}{RESET}")


def display_warning(msg):
    """Display a warning message."""
    print(f"  {YELLOW}{BOLD} {msg}{RESET}")


def display_info_message(msg):
    """Display an informational message."""
    print(f"  {GRAY}{msg}{RESET}")


def menu_item(number, text, color):
    """Display a numbered menu item."""
    print(f"  {color}{BOLD}{number:>3}.{RESET}  {text}")


def status_badge(text, is_good):
    """Return a colored status badge."""
    if is_good:
        return f"{GREEN}{text}{RESET}"
    return f"{RED}{text}{RESET}"