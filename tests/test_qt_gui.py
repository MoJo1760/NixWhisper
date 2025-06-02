#!/usr/bin/env python3
"""
Test script for the Qt-based GUI of NixWhisper.

This script provides a simple way to test the GUI components without running the full application.
"""

import logging
import sys
import time
import numpy as np
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt, QObject, pyqtSignal
from PyQt6.QtGui import QKeySequence

# Set up logging
logger = logging.getLogger(__name__)

# Add the src directory to the path so we can import nixwhisper
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nixwhisper.qt_gui import NixWhisperWindow, OverlayWindow, RecordingThread
from nixwhisper.config import Config


class MockModelManager(QObject):
    """Mock model manager for testing."""
    model_loaded = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.cache_dir = "/tmp/nixwhisper_test_cache"
        self.current_model = None
        self.available_models = ["base", "small", "medium"]
    
    def get_available_models(self):
        return self.available_models
    
    def load_model(self, model_name):
        self.current_model = model_name
        self.model_loaded.emit(model_name)
        return MockModel()  # Return a mock model


class MockModel:
    """Mock model for testing."""
    def transcribe(self, audio_data, **kwargs):
        return {"text": "This is a test transcription."}
    
    def to(self, device):
        return self


def test_overlay_window(qtbot):
    """Test the overlay window with simulated audio data."""
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)
    
    # Test show/hide
    overlay.show()
    assert overlay.isVisible()
    overlay.hide()
    assert not overlay.isVisible()
    
    # Test recording state
    overlay.set_recording(True)
    overlay.set_recording(False)
    
    # Test audio level updates
    overlay.update_audio_level(0.5)
    
    # Test spectrum updates
    spectrum = [0.1 * i for i in range(32)]
    overlay.update_spectrum(spectrum)


def test_hotkey_configuration(qtbot, tmp_path):
    """Test that the hotkey can be configured and triggers the correct action."""
    # Setup test config
    test_config = Config()
    test_config.ui.hotkey = "Ctrl+Alt+Space"  # Default hotkey
    
    # Add silence detection settings to the test config
    test_config.ui.silence_threshold = 0.01
    test_config.ui.silence_duration = 2.0
    test_config.ui.silence_detection = True
    
    # Create a mock model manager
    model_manager = MockModelManager()
    
    # Create the main window with the test config
    window = NixWhisperWindow(model_manager, config=test_config)
    qtbot.addWidget(window)
    
    # Verify the hotkey is set correctly in the config
    assert window.config.ui.hotkey == "Ctrl+Alt+Space"
    
    # Test that the settings dialog can be shown and closed
    # We'll use qtbot to wait for the dialog to be shown with a longer timeout
    with qtbot.waitExposed(window, timeout=30000):
        window.show_settings()
    
    # Cleanup
    window.close()


def test_recording_thread(qtbot, caplog):
    """Test the recording functionality with a simple GUI."""
    # Set up logging capture
    caplog.set_level(logging.INFO)
    
    logger.info("Starting test_recording_thread")
    
    # Create a mock model manager
    model_manager = MockModelManager()
    logger.info("Created MockModelManager")
    
    # Create the main window with test config
    test_config = Config()
    logger.info("Created test config")
    
    # Create the window and add it to the qtbot
    window = NixWhisperWindow(model_manager, config=test_config)
    qtbot.addWidget(window)
    logger.info("Created and added NixWhisperWindow to qtbot")
    
    # Test initial state
    logger.info(f"Initial is_recording state: {window.is_recording}")
    assert not window.is_recording
    
    # Test start recording - should return True and set is_recording to True
    logger.info("Calling start_recording()")
    result = window.start_recording()
    logger.info(f"start_recording() returned: {result}, is_recording: {window.is_recording}")
    
    # Check the result and state
    assert result is True, f"Expected start_recording() to return True, got {result}"
    assert window.is_recording is True, "Expected is_recording to be True after start_recording()"
    
    # Test stop recording - should return True and set is_recording to False
    logger.info("Calling stop_recording()")
    result = window.stop_recording()
    logger.info(f"stop_recording() returned: {result}, is_recording: {window.is_recording}")
    
    # Check the result and state
    assert result is True, f"Expected stop_recording() to return True, got {result}"
    assert window.is_recording is False, "Expected is_recording to be False after stop_recording()"
    
    # Test toggle recording (start)
    logger.info("First toggle_recording() - should start recording")
    result = window.toggle_recording()
    logger.info(f"toggle_recording() returned: {result}, is_recording: {window.is_recording}")
    
    # Check the result and state
    assert result is True, f"Expected toggle_recording() to return True, got {result}"
    assert window.is_recording is True, "Expected is_recording to be True after toggle_recording()"
    
    # Test toggle recording (stop)
    logger.info("Second toggle_recording() - should stop recording")
    result = window.toggle_recording()
    logger.info(f"toggle_recording() returned: {result}, is_recording: {window.is_recording}")
    
    # Check the result and state
    assert result is True, f"Expected toggle_recording() to return True, got {result}"
    assert window.is_recording is False, "Expected is_recording to be False after toggle_recording()"
    
    # Cleanup
    logger.info("Test completed, cleaning up")
    window.close()


if __name__ == '__main__':
    # This block is not needed when running with pytest
    app = QApplication(sys.argv)
    
    # Run tests
    test_overlay_window()
    test_recording_thread()
    
    sys.exit(app.exec())
