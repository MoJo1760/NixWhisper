"""Qt-based GUI for NixWhisper."""
import logging
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QLabel, QHBoxLayout, QProgressBar, QMessageBox, QSystemTrayIcon, QMenu, QStyle
)
from PyQt6.QtGui import QIcon, QAction, QPixmap

import numpy as np
from nixwhisper.transcriber import create_transcriber
from nixwhisper.audio import AudioRecorder
from nixwhisper.model_manager import ModelManager

logger = logging.getLogger(__name__)

class TranscriptionThread(QThread):
    """Thread for running transcription in the background."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, audio_data: bytes, model_manager: ModelManager):
        super().__init__()
        self.audio_data = audio_data
        self.model_manager = model_manager

    def run(self):
        """Run the transcription."""
        try:
            # Create a transcriber instance
            transcriber = create_transcriber(
                'faster-whisper',
                model_size='base',
                device='auto',
                compute_type='int8',
                model_dir=str(self.model_manager.cache_dir)
            )
            
            # Transcribe the audio data directly
            logger.debug(f"Starting transcription of {len(self.audio_data) if self.audio_data else 0} bytes of audio data")
            result = transcriber.transcribe(self.audio_data)
            
            if not result or not result.text:
                logger.warning("Transcription returned empty result")
                self.error.emit("No transcription result returned")
            else:
                logger.debug(f"Transcription successful: {result.text[:100]}...")
                self.finished.emit(result.text)
                
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            self.error.emit(f"Transcription failed: {str(e)}")

def calculate_volume_level(audio_data: np.ndarray) -> float:
    """Calculate the RMS volume level of audio data.
    
    Args:
        audio_data: Audio data as a numpy array
        
    Returns:
        float: RMS volume level (0.0 to 1.0)
    """
    if audio_data.size == 0:
        return 0.0
    
    # Calculate RMS and normalize to 0-1 range
    rms = np.sqrt(np.mean(np.square(audio_data), axis=0))
    return float(np.mean(rms))

class RecordingThread(QThread):
    """Thread for recording audio in the background."""
    update_level = pyqtSignal(float)
    finished = pyqtSignal(bytes)

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.recorder = AudioRecorder(
            sample_rate=sample_rate,
            channels=channels,
            blocksize=1024,
            silence_threshold=0.01,
            silence_duration=2.0
        )
        self.is_recording = False
        self.audio_buffer = []

    def _audio_callback(self, audio_data, rms, is_silent):
        """Callback for audio data from the recorder."""
        if not self.is_recording:
            return
            
        # Convert to float32 if needed
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32) / np.iinfo(audio_data.dtype).max
            
        # Add to buffer
        self.audio_buffer.append(audio_data.copy())
        
        # Emit volume level update
        self.update_level.emit(float(rms))

    def run(self):
        """Run the recording."""
        self.is_recording = True
        self.audio_buffer = []
        
        try:
            # Start recording with our callback
            self.recorder.start_recording(self._audio_callback)
            
            # Keep running while recording
            while self.is_recording:
                time.sleep(0.1)  # Small sleep to prevent high CPU usage
                
        except Exception as e:
            logger.error(f"Recording error: {e}", exc_info=True)
        finally:
            # Stop recording and get the full audio
            if hasattr(self.recorder, 'stop_recording'):
                try:
                    audio_data = self.recorder.stop_recording()
                    if audio_data is not None and len(audio_data) > 0:
                        self.finished.emit(audio_data.tobytes())
                    else:
                        logger.warning("No audio data recorded")
                        self.finished.emit(b'')
                except Exception as e:
                    logger.error(f"Error stopping recording: {e}", exc_info=True)
                    self.finished.emit(b'')
            else:
                logger.error("Recorder has no stop_recording method")
                self.finished.emit(b'')
    
    def stop(self):
        """Stop the recording."""
        self.is_recording = False

class NixWhisperWindow(QMainWindow):
    """Main application window for NixWhisper."""
    
    def __init__(self, model_manager: ModelManager):
        super().__init__()
        self.model_manager = model_manager
        self.recording_thread = None
        self.transcription_thread = None
        self.tray_icon = None
        
        self.init_ui()
        self.init_tray_icon()
        
        # Hide the main window initially
        self.hide()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("NixWhisper")
        self.setMinimumSize(400, 300)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Status label
        self.status_label = QLabel("Ready to record")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress bar for audio level
        self.level_meter = QProgressBar()
        self.level_meter.setRange(0, 100)
        self.level_meter.setTextVisible(False)
        self.level_meter.setFixedHeight(10)
        layout.addWidget(self.level_meter)
        
        # Transcription display
        self.transcription_display = QLabel("")
        self.transcription_display.setWordWrap(True)
        self.transcription_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transcription_display.setStyleSheet("""
            QLabel {
                font-size: 16px;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                min-height: 100px;
            }
        """)
        layout.addWidget(self.transcription_display)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Record button
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        button_layout.addWidget(self.record_button)
        
        # Copy button
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.setEnabled(False)
        button_layout.addWidget(self.copy_button)
        
        layout.addLayout(button_layout)
        
        # Set window icon
        self.setWindowIcon(self.style().standardIcon(
            getattr(QStyle.StandardPixmap, 'SP_MediaPlay')
        ))
    
    def init_tray_icon(self):
        """Initialize the system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(
            getattr(QStyle.StandardPixmap, 'SP_MediaPlay')
        ))
        
        # Create menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def tray_icon_activated(self, reason):
        """Handle system tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
    
    def toggle_recording(self):
        """Toggle recording on/off."""
        if self.recording_thread and self.recording_thread.isRunning():
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """Start recording audio."""
        self.record_button.setText("Stop Recording")
        self.status_label.setText("Recording...")
        self.transcription_display.setText("")
        self.copy_button.setEnabled(False)
        
        # Start recording in a separate thread
        self.recording_thread = RecordingThread()
        self.recording_thread.update_level.connect(self.update_level_meter)
        self.recording_thread.finished.connect(self.on_recording_finished)
        self.recording_thread.start()
    
    def stop_recording(self):
        """Stop recording and start transcription."""
        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.stop()
            self.recording_thread.wait()
            self.record_button.setEnabled(False)
            self.status_label.setText("Processing...")
    
    def on_recording_finished(self, audio_data):
        """Handle recording finished event."""
        self.record_button.setText("Start Recording")
        self.record_button.setEnabled(True)
        
        if not audio_data:
            self.status_label.setText("Recording failed")
            return
        
        # Start transcription in a separate thread
        self.transcription_thread = TranscriptionThread(audio_data, self.model_manager)
        self.transcription_thread.finished.connect(self.on_transcription_finished)
        self.transcription_thread.error.connect(self.on_transcription_error)
        self.transcription_thread.start()
    
    def on_transcription_finished(self, text):
        """Handle transcription finished event."""
        self.transcription_display.setText(text)
        self.status_label.setText("Transcription complete")
        self.copy_button.setEnabled(True)
    
    def on_transcription_error(self, error):
        """Handle transcription error."""
        self.status_label.setText(f"Error: {error}")
        self.record_button.setEnabled(True)
    
    def update_level_meter(self, level):
        """Update the audio level meter."""
        # Scale the level to 0-100 for the progress bar
        scaled_level = min(int(level * 100), 100)
        self.level_meter.setValue(scaled_level)
    
    def copy_to_clipboard(self):
        """Copy the transcription to the clipboard."""
        text = self.transcription_display.text()
        if text:
            QApplication.clipboard().setText(text)
            self.status_label.setText("Copied to clipboard")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Stop any running threads
        if self.recording_thread and self.recording_thread.isRunning():
            self.recording_thread.stop()
            self.recording_thread.wait()
        
        if self.transcription_thread and self.transcription_thread.isRunning():
            self.transcription_thread.quit()
            self.transcription_thread.wait()
        
        # Hide the window instead of closing it
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

def run_qt_gui():
    """Run the Qt-based GUI."""
    logger.info("Initializing Qt application")
    app = QApplication(sys.argv)
    app.setApplicationName("NixWhisper")
    app.setApplicationDisplayName("NixWhisper")
    
    # Set Fusion style for a more modern look
    app.setStyle('Fusion')
    
    # Initialize model manager
    logger.info("Initializing model manager")
    model_manager = ModelManager()
    
    # Create and show the main window
    logger.info("Creating main window")
    window = NixWhisperWindow(model_manager)
    
    # Check system tray availability
    tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    logger.info(f"System tray available: {tray_available}")
    
    if tray_available:
        logger.info("Hiding main window, running in system tray")
        window.hide()
    else:
        logger.info("Showing main window")
        window.show()
    
    logger.info("Starting application event loop")
    sys.exit(app.exec())
