"""Integration tests for the GUI components."""

import os
import signal
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import gi
import pytest
from gi.repository import GLib

# Import GTK after setting up the environment
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from nixwhisper.gui import NixWhisperWindow
from nixwhisper.config import Config


@pytest.fixture(scope="module")
def glib_main_loop():
    """Set up the GLib main loop for GTK testing."""
    loop = GLib.MainLoop()
    return loop


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Config()
    # Use a smaller model for faster tests
    config.model.name = "tiny"
    config.model.device = "cpu"
    return config


@pytest.fixture
def app_window(qtbot, mock_config):
    """Create and return the application window for testing."""
    # Patch the AudioRecorder to avoid actual audio recording
    with patch('nixwhisper.gui.AudioRecorder') as mock_recorder_class:
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder
        
        # Create the application window
        window = NixWhisperWindow(mock_config)
        window.show()
        qtbot.addWidget(window._window)
        
        # Process pending events
        Gtk.main_iteration_do(False)
        
        yield window, mock_recorder
        
        # Clean up
        window._window.destroy()
        Gtk.main_iteration_do(False)


@pytest.mark.gui
class TestNixWhisperGUI:
    """Integration tests for the NixWhisper GUI."""
    
    def test_window_initialization(self, app_window):
        """Test that the window initializes correctly."""
        window, _ = app_window
        
        # Check that the window was created
        assert window._window is not None
        assert isinstance(window._window, Gtk.Window)
        
        # Check that the window has the correct title
        assert "NixWhisper" in window._window.get_title()
        
        # Check that the record button exists
        assert hasattr(window, 'record_button')
        assert window.record_button is not None
        
        # Check that the text view exists
        assert hasattr(window, 'text_view')
        assert window.text_view is not None
    
    def test_record_button_click(self, app_window, qtbot):
        """Test clicking the record button starts and stops recording."""
        window, mock_recorder = app_window
        
        # Click the record button to start recording
        window.record_button.emit('clicked')
        Gtk.main_iteration_do(False)
        
        # Check that the audio recorder was started
        mock_recorder.start_recording.assert_called_once()
        assert "Recording" in window.record_button.get_label()
        
        # Click the record button again to stop recording
        window.record_button.emit('clicked')
        Gtk.main_iteration_do(False)
        
        # Check that the audio recorder was stopped
        mock_recorder.stop_recording.assert_called_once()
        assert "Record" in window.record_button.get_label()
    
    def test_clear_button(self, app_window, qtbot):
        """Test that the clear button clears the text view."""
        window, _ = app_window
        
        # Add some text to the text buffer
        text_buffer = window.text_view.get_buffer()
        text_buffer.set_text("Test text")
        
        # Click the clear button
        window.clear_button.emit('clicked')
        Gtk.main_iteration_do(False)
        
        # Check that the text was cleared
        start_iter = text_buffer.get_start_iter()
        end_iter = text_buffer.get_end_iter()
        assert text_buffer.get_text(start_iter, end_iter, False) == ""
    
    def test_copy_button(self, app_window, qtbot):
        """Test that the copy button copies text to the clipboard."""
        window, _ = app_window
        
        # Add some text to the text buffer
        test_text = "Text to copy"
        text_buffer = window.text_view.get_buffer()
        text_buffer.set_text(test_text)
        
        # Mock the clipboard
        with patch('gi.repository.Gtk.Clipboard') as mock_clipboard:
            # Click the copy button
            window.copy_button.emit('clicked')
            Gtk.main_iteration_do(False)
            
            # Check that the clipboard was set with the correct text
            mock_clipboard.get.assert_called_once_with(Gdk.SELECTION_CLIPBOARD)
            mock_clipboard.get.return_value.set_text.assert_called_once_with(test_text, -1)
    
    def test_auto_scroll(self, app_window, qtbot):
        """Test that the text view auto-scrolls when new text is added."""
        window, _ = app_window
        
        # Add a long text to the text buffer
        long_text = "\n".join(f"Line {i}" for i in range(100))
        window._update_text(long_text)
        
        # Get the vertical adjustment
        vadj = window.scrolled_window.get_vadjustment()
        
        # The view should be scrolled to the bottom
        assert vadj.get_value() == vadj.get_upper() - vadj.get_page_size()
    
    def test_settings_dialog(self, app_window, qtbot):
        """Test opening and interacting with the settings dialog."""
        window, _ = app_window
        
        # Click the settings button
        window.settings_button.emit('clicked')
        Gtk.main_iteration_do(False)
        
        # Check that the settings dialog was created
        assert hasattr(window, 'settings_dialog')
        assert window.settings_dialog is not None
        assert isinstance(window.settings_dialog, Gtk.Dialog)
        
        # Close the settings dialog
        window.settings_dialog.response(Gtk.ResponseType.CANCEL)
        Gtk.main_iteration_do(False)
        
        # The dialog should be destroyed
        assert window.settings_dialog is None


# This is needed for the tests to run with pytest-qt
class GtkQApp:
    """Wrapper to make Gtk work with pytest-qt."""
    def __init__(self):
        self.app = Gtk.Application(application_id='com.example.test')
        self.app.register()
    
    def __enter__(self):
        return self.app
    
    def __exit__(self, *args):
        if hasattr(self, 'app'):
            self.app.quit()


@pytest.fixture(scope="session")
def qt_app():
    """Create a Gtk application for testing."""
    with GtkQApp() as app:
        yield app
