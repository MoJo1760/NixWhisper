"""NixWhisper: Privacy-focused offline speech-to-text for Linux."""

import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path.home() / '.cache' / 'nixwhisper' / 'nixwhisper.log')
    ]
)

# Set up package logger
logger = logging.getLogger(__name__)

# Check for GUI dependencies
GUI_AVAILABLE = False
try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    GUI_AVAILABLE = True
except (ImportError, ValueError) as e:
    logger.debug("GUI dependencies not available: %s", e)


__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Import main components
from .audio import AudioRecorder
from .config import Config, load_config
from .whisper_model import WhisperTranscriber, TranscriptionResult
from .input import TextInput

# Make these available at the package level
__all__ = [
    'AudioRecorder',
    'Config',
    'load_config',
    'WhisperTranscriber',
    'TranscriptionResult',
    'TextInput',
]
