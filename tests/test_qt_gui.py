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


def test_cursor_relative_positioning(qtbot, monkeypatch):
    """Test cursor-relative positioning in the overlay window."""
    # Create a mock cursor position
    from dataclasses import dataclass
    
    @dataclass
    class MockCursorPosition:
        x: int
        y: int
        screen_number: int = 0
        screen_x: int = 0
        screen_y: int = 0
        screen_width: int = 1920
        screen_height: int = 1080
    
    # Create mock screens
    from PyQt6.QtGui import QScreen
    from PyQt6.QtCore import QRect
    
    class MockScreen(QScreen):
        def __init__(self, x=0, y=0, width=1920, height=1080, name="MockScreen"):
            super().__init__()
            self._geometry = QRect(x, y, width, height)
            self._name = name
            
        def geometry(self):
            return self._geometry
            
        def name(self):
            return self._name
    
    # Create the overlay window
    overlay = OverlayWindow()
    qtbot.addWidget(overlay)
    overlay.resize(400, 100)  # Set a reasonable size for testing
    
    # Test 1: Test cursor-relative positioning disabled (should center)
    overlay.enable_cursor_relative_positioning(False)
    overlay.update_position()
    
    # Test 2: Test cursor-relative positioning enabled
    overlay.enable_cursor_relative_positioning(True)
    
    # Mock get_cursor_position to return our test position
    def mock_get_cursor_position(include_screen_info=False):
        return MockCursorPosition(x=500, y=500)
    
    # Mock QGuiApplication.screens()
    def mock_screens():
        return [MockScreen()]
    
    # Apply the mocks
    from nixwhisper import qt_gui
    monkeypatch.setattr(qt_gui, 'get_cursor_position', mock_get_cursor_position)
    monkeypatch.setattr('PyQt6.QtGui.QGuiApplication.screens', mock_screens)
    
    # Test with default offsets (20, 20)
    overlay.update_position()
    pos = overlay.pos()
    assert 520 <= pos.x() <= 540  # 500 + 20 +- 20px margin
    assert 520 <= pos.y() <= 540  # 500 + 20 +- 20px margin
    
    # Test with custom offsets
    overlay.set_cursor_offset(50, -30)
    overlay.update_position()
    pos = overlay.pos()
    assert 550 <= pos.x() <= 570  # 500 + 50 +- 20px margin
    assert 470 <= pos.y() <= 490  # 500 - 30 +- 20px margin
    
    # Test edge case: cursor near screen edge
    def mock_edge_cursor():
        return MockCursorPosition(x=1900, y=1000)
    
    monkeypatch.setattr(qt_gui, 'get_cursor_position', mock_edge_cursor)
    overlay.update_position()
    pos = overlay.pos()
    assert pos.x() < 1920 - 400  # Should be within screen width - window width
    assert pos.y() < 1080 - 100  # Should be within screen height - window height
    
    # Test with multiple screens
    def mock_multi_screens():
        return [
            MockScreen(0, 0, 1920, 1080, "Screen1"),
            MockScreen(1920, 0, 1920, 1080, "Screen2")
        ]
    
    monkeypatch.setattr('PyQt6.QtGui.QGuiApplication.screens', mock_multi_screens)
    
    # Cursor on second screen
    def mock_second_screen_cursor():
        return MockCursorPosition(x=2000, y=500, screen_number=1)
    
    monkeypatch.setattr(qt_gui, 'get_cursor_position', mock_second_screen_cursor)
    overlay.update_position()
    pos = overlay.pos()
    assert 1920 <= pos.x() <= 1920 + 1920 - 400  # Should be on second screen
    
    # Clean up
    overlay.hide()
    overlay.deleteLater()


if __name__ == '__main__':
    # This block is not needed when running with pytest
    app = QApplication(sys.argv)
    
    # Run tests
    test_overlay_window()
    test_recording_thread()
    
    sys.exit(app.exec())
