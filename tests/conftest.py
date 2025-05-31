"""Test configuration and fixtures for NixWhisper."""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf
from pynput import keyboard

from nixwhisper.config import Config, AudioConfig, ModelConfig, HotkeyConfig, UIConfig
from nixwhisper.whisper_model import TranscriptionResult, TranscriptionSegment


# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "gui: mark tests that require GUI components"
    )
    config.addinivalue_line(
        "markers",
        "e2e: mark tests as end-to-end tests"
    )


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return the path to the test data directory."""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """Create and return a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="nixwhisper-test-")
    try:
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_config() -> Config:
    """Return a mock configuration for testing with fast settings."""
    return Config(
        audio=AudioConfig(
            sample_rate=16000,
            channels=1,
            device=None,
            silence_threshold=0.01,
            silence_duration=0.5,  # Shorter for faster tests
            blocksize=1024,
        ),
        model=ModelConfig(
            name="tiny",  # Fastest model for testing
            device="cpu",
            compute_type="int8",
            language="en",
            task="transcribe",
            beam_size=1,  # Faster decoding
            best_of=1,    # Faster decoding
            temperature=0.0,
            word_timestamps=False,
        ),
        hotkeys=HotkeyConfig(
            toggle_listening="<ctrl>+<alt>+space",
            copy_last="<ctrl>+<alt>+c",
            exit_app="<ctrl>+<alt>+x",
        ),
        ui=UIConfig(
            theme="system",
            show_spectrogram=True,
            show_confidence=True,
            font_family="Sans",
            font_size=12,
        ),
    )


@pytest.fixture
def mock_audio_file(test_data_dir: Path) -> Path:
    """Return the path to a test audio file with a 1-second 440Hz sine wave."""
    audio_file = test_data_dir / "test_audio.wav"
    if not audio_file.exists():
        rate = 16000
        duration = 1.0  # seconds
        t = np.linspace(0, duration, int(rate * duration), endpoint=False)
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.1  # 440 Hz sine wave at low volume
        sf.write(str(audio_file), audio_data, rate)
    
    return audio_file


@pytest.fixture
def short_audio_data() -> np.ndarray:
    """Generate a short audio signal for testing."""
    sample_rate = 16000
    duration = 0.5  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return np.sin(2 * np.pi * 440 * t) * 0.1  # 440 Hz sine wave


@pytest.fixture
def mock_transcription_result() -> TranscriptionResult:
    """Create a mock transcription result for testing."""
    return TranscriptionResult(
        text="This is a test transcription.",
        language="en",
        segments=[
            TranscriptionSegment(
                id=0,
                start=0.0,
                end=2.5,
                text="This is a test transcription.",
                tokens=[],
                temperature=0.0,
                avg_logprob=0.0,
                compression_ratio=0.0,
                no_speech_prob=0.0,
            )
        ]
    )


@pytest.fixture
def mock_whisper_model():
    """Create a mock Whisper model for testing."""
    with patch('nixwhisper.whisper_model.WhisperTranscriber') as mock_transcriber:
        mock_model = MagicMock()
        mock_transcriber.return_value = mock_model
        
        # Set up a default transcription result
        mock_result = TranscriptionResult(
            text="This is a test transcription.",
            language="en",
            segments=[]
        )
        mock_model.transcribe.return_value = mock_result
        
        yield mock_model


@pytest.fixture
def mock_keyboard_listener():
    """Create a mock keyboard listener for testing."""
    with patch('pynput.keyboard.Listener') as mock_listener:
        mock_listener_instance = MagicMock()
        mock_listener.return_value = mock_listener_instance
        yield mock_listener_instance


@pytest.fixture
def mock_audio_stream():
    """Create a mock audio stream for testing."""
    with patch('sounddevice.InputStream') as mock_stream:
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        yield mock_stream_instance


@pytest.fixture
def mock_audio_device():
    """Mock audio device query for testing."""
    with patch('sounddevice.query_devices') as mock_query_devices:
        mock_devices = [
            {'name': 'Test Input', 'max_input_channels': 1, 'default_samplerate': 16000},
            {'name': 'Test Output', 'max_output_channels': 2, 'default_samplerate': 44100},
        ]
        mock_query_devices.return_value = mock_devices
        yield mock_devices


@pytest.fixture
def mock_imports():
    """Mock imports for testing without actual dependencies."""
    with patch.dict('sys.modules', {
        'sounddevice': MagicMock(),
        'numpy': MagicMock(),
        'torch': MagicMock(),
        'faster_whisper': MagicMock(),
        'gi': MagicMock(),
        'gi.repository': MagicMock(),
    }):
        yield
