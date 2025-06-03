"""Shell utilities for NixWhisper."""

import subprocess
import shlex
from typing import Optional


def type_text_xdotool(text: str) -> bool:
    """Type text using xdotool.

    Args:
        text: Text to type

    Returns:
        True if successful, False otherwise
    """
    try:
        # Escape special characters for shell
        escaped_text = shlex.quote(text)

        # Type the text
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--", escaped_text],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
