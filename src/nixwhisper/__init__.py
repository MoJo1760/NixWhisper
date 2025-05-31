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
