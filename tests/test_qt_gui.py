#!/usr/bin/env python3
"""
Test script for the Qt-based GUI of NixWhisper.

This script provides a simple way to test the GUI components without running the full application.
"""

import sys
import time
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt

# Add the src directory to the path so we can import nixwhisper
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nixwhisper.qt_gui import NixWhisperWindow, OverlayWindow, RecordingThread


def test_overlay_window():
    """Test the overlay window with simulated audio data."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Create and show the overlay window
    overlay = OverlayWindow()
    overlay.show()
    overlay.set_recording(True)
    
    # Simulate audio data updates
    def update_audio():
        # Generate random audio levels and spectrum
        level = np.random.uniform(0.1, 1.0)
        spectrum = np.random.uniform(0, 1, 32).tolist()
        
        # Update the overlay
        overlay.update_audio_level(level)
        overlay.update_spectrum(spectrum)
    
    # Set up a timer to update the audio visualization
    timer = QTimer()
    timer.timeout.connect(update_audio)
    timer.start(50)  # Update every 50ms
    
    # Run the application
    sys.exit(app.exec())


def test_recording_thread():
    """Test the recording thread with a simple GUI."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Create and show the main window
    window = NixWhisperWindow()
    window.show()
    
    # Start the recording thread
    def start_recording():
        window.toggle_recording()
        
        # Auto-stop after 5 seconds for testing
        QTimer.singleShot(5000, window.toggle_recording)
    
    # Start recording after a short delay
    QTimer.singleShot(1000, start_recording)
    
    # Run the application
    sys.exit(app.exec())


if __name__ == '__main__':
    # Uncomment the test you want to run
    test_overlay_window()
    # test_recording_thread()
