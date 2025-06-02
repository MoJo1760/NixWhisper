"""Qt-based GUI for NixWhisper."""
import logging
import sys
import time
import math
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Tuple

from PyQt6.QtCore import Qt, QTimer, QPointF, QRect, QRectF, QPropertyAnimation, QEasingCurve, pyqtSignal, QThread, QSize
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QLabel, QHBoxLayout, QProgressBar, QMessageBox, QSystemTrayIcon, 
    QMenu, QStyle, QGraphicsOpacityEffect, QSizePolicy, QGroupBox,
    QCheckBox, QSlider
)
from PyQt6.QtGui import (
    QIcon, QAction, QPixmap, QPainter, QColor, QLinearGradient, QRadialGradient,
    QPen, QBrush, QPainterPath, QFont, QFontMetrics, QGuiApplication, QShortcut
)

import numpy as np
from nixwhisper.transcriber import create_transcriber
from nixwhisper.audio import AudioRecorder
from nixwhisper.model_manager import ModelManager

logger = logging.getLogger(__name__)

class OverlayWindow(QWidget):
    """Floating overlay window that shows recording status and audio visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("Creating OverlayWindow instance...")
        
        try:
            # Window flags for overlay behavior
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowTransparentForInput
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            
            # Visual properties
            self.radius = 15
            self.padding = 10
            self.spectrum = [0.0] * 32  # Initialize with zeros
            self.is_recording = False
            
            # Set initial size and position (will be overridden by parent)
            self.resize(400, 80)  # Smaller height since we don't need as much space
            
            # Disable test pattern by default
            self.test_pattern = False
            
            logger.debug("OverlayWindow initialized")
            
        except Exception as e:
            logger.error(f"Error initializing OverlayWindow: {e}", exc_info=True)
            raise
    
    def disable_test_pattern(self):
        """Disable the test pattern after initial display."""
        self.test_pattern = False
        self.update()
    
    def set_recording(self, recording: bool):
        """Update the recording status."""
        try:
            self.is_recording = recording
            self.update()
            logger.debug(f"Recording status updated: {'Recording...' if recording else 'Ready'}")
        except Exception as e:
            logger.error(f"Error in set_recording: {e}", exc_info=True)
        
    def setup_ui(self):
        """Initialize the UI components."""
        self.setMinimumSize(300, 100)
        self.setMaximumWidth(500)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {self.text_color.name()};
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }}
        """)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(self.padding, self.padding, self.padding, self.padding)
        layout.setSpacing(10)
        layout.addWidget(self.status_label)
        
        # Animation for pulsing effect when recording
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.pulse_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setStartValue(0.7)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setLoopCount(-1)  # Infinite loop
        
    def update_position(self):
        """Position the window at the bottom center of the screen."""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        window_size = self.sizeHint()
        x = (screen.width() - window_size.width()) // 2
        y = screen.height() - window_size.height() - 50  # 50px from bottom
        self.move(x, y)
        
    def paintEvent(self, event):
        """Handle paint events."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Get the rectangle as QRectF
            rect = QRectF(self.rect())
            
            # Draw background with rounded corners
            path = QPainterPath()
            path.addRoundedRect(rect, self.radius, self.radius)
            painter.setClipPath(path)
            
            # Semi-transparent background with border for visibility
            painter.fillRect(rect, QColor(30, 30, 40, 220))  # Darker for better contrast
            
            # Draw border for better visibility
            pen = QPen(QColor(100, 100, 150, 200), 2)
            painter.setPen(pen)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), self.radius, self.radius)
            
            # Draw test pattern if enabled
            if hasattr(self, 'test_pattern') and self.test_pattern:
                self.draw_test_pattern(painter, rect.toRect())
            # Otherwise draw audio visualization
            else:
                self.draw_audio_visualization(painter, rect.toRect())
            
            # Draw window title for debugging
            if hasattr(self, 'show_debug') and self.show_debug:
                debug_text = f"Spectrum bins: {len(self.spectrum) if hasattr(self, 'spectrum') else 0}"
                if hasattr(self, 'spectrum') and self.spectrum:
                    debug_text += f" | Max: {max(self.spectrum):.2f}"
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(10, 15, debug_text)
                
        except Exception as e:
            logger.error(f"Error in paintEvent: {e}", exc_info=True)
            painter.end()
            
    def draw_audio_visualization(self, painter: QPainter, rect: QRect):
        """Draw audio level and spectrum visualization with red light indicator."""
        try:
            padding = getattr(self, 'padding', 10)
            
            # Calculate the visualization area
            vis_rect = rect.adjusted(padding, padding, -padding, -padding)
            
            # Draw spectrum visualization
            if hasattr(self, 'spectrum') and self.spectrum:
                self.draw_spectrum(painter, vis_rect)
            
            # Draw red light indicator (circle on the left side)
            light_size = 16
            light_margin = 10
            light_x = rect.left() + light_margin
            light_y = rect.center().y() - light_size // 2
            
            # Draw outer glow if recording
            if hasattr(self, 'is_recording') and self.is_recording:
                glow_radius = light_size * 1.5
                glow_rect = QRectF(
                    light_x - (glow_radius - light_size) / 2,
                    light_y - (glow_radius - light_size) / 2,
                    glow_radius,
                    glow_radius
                )
                
                # Create radial gradient for glow effect
                gradient = QRadialGradient(
                    light_x + light_size / 2,
                    light_y + light_size / 2,
                    glow_radius / 2
                )
                gradient.setColorAt(0, QColor(255, 50, 50, 180))
                gradient.setColorAt(0.7, QColor(200, 0, 0, 100))
                gradient.setColorAt(1, QColor(100, 0, 0, 0))
                
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(gradient))
                painter.drawEllipse(glow_rect)
            
            # Draw the red light
            light_rect = QRect(light_x, light_y, light_size, light_size)
            painter.setPen(QPen(QColor(100, 0, 0, 200), 1))
            
            # Change light color based on recording state
            if hasattr(self, 'is_recording') and self.is_recording:
                # Pulsing red when recording
                gradient = QRadialGradient(
                    light_rect.center().x(),
                    light_rect.center().y(),
                    light_size / 2
                )
                gradient.setColorAt(0, QColor(255, 50, 50, 255))
                gradient.setColorAt(0.7, QColor(200, 0, 0, 200))
                gradient.setColorAt(1, QColor(150, 0, 0, 150))
                painter.setBrush(QBrush(gradient))
            else:
                # Dim red when not recording
                painter.setBrush(QColor(80, 0, 0, 150))
            
            painter.drawEllipse(light_rect)
                    
        except Exception as e:
            logger.error(f"Error in draw_audio_visualization: {e}", exc_info=True)
                
    def update_audio_level(self, level: float):
        """Update the audio level meter."""
        try:
            if not hasattr(self, 'levels'):
                self.levels = []
            
            # Keep a history of levels for smoothing
            self.levels.append(level)
            if len(self.levels) > 5:  # Keep last 5 levels for smoothing
                self.levels.pop(0)
                
            # Update peak level
            if not hasattr(self, 'peak_level') or level > self.peak_level:
                self.peak_level = level
            
            # Schedule peak decay
            if hasattr(self, '_peak_timer') and self._peak_timer is not None:
                try:
                    self._peak_timer.stop()
                except (AttributeError, RuntimeError):
                    pass  # Timer might be invalid or already stopped
            
            self._peak_timer = QTimer(self)
            self._peak_timer.setSingleShot(True)
            self._peak_timer.timeout.connect(self._decay_peak)
            self._peak_timer.start(1000)
            self.update()
            
        except Exception as e:
            logger.error(f"Error in update_audio_level: {e}", exc_info=True)
    
    def update_spectrum(self, spectrum: List[float]):
        """Update the frequency spectrum visualization."""
        try:
            if not isinstance(spectrum, (list, np.ndarray)):
                logger.warning(f"Invalid spectrum data type: {type(spectrum)}")
                return
                
            logger.debug(f"Updating spectrum with {len(spectrum)} frequency bins")
            if not spectrum:
                logger.warning("Received empty spectrum data")
                return
            
            # Ensure spectrum is a list of numbers
            try:
                spectrum = [float(x) for x in spectrum]
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting spectrum values to float: {e}")
                return
                
            # Store the spectrum for drawing
            self.spectrum = spectrum
            
            # Force a repaint
            self.update()
            
        except Exception as e:
            logger.error(f"Error in update_spectrum: {e}", exc_info=True)
    
    def _decay_peak(self):
        """Gradually reduce the peak level."""
        if hasattr(self, 'peak_level'):
            self.peak_level *= 0.9  # Reduce peak by 10%
            if self.peak_level < 0.01:  # Reset if very small
                del self.peak_level
            else:
                self.update()
                QTimer.singleShot(100, self._decay_peak)
    
    def draw_spectrum(self, painter: QPainter, rect: QRect):
        """Draw frequency spectrum visualization."""
        try:
            if not hasattr(self, 'spectrum') or not self.spectrum:
                return
                
            # Visualization parameters
            bar_width = 4
            bar_spacing = 1
            corner_radius = 2
            max_bars = min(32, len(self.spectrum))  # Limit number of bars
            
            if max_bars == 0:
                return
                
            # Calculate available width and height
            total_bars = max_bars
            total_width = (bar_width + bar_spacing) * total_bars - bar_spacing
            start_x = rect.left() + (rect.width() - total_width) // 2
            bar_height = rect.height()
            
            # Draw each frequency bar
            for i in range(max_bars):
                value = self.spectrum[i]
                if not (0 <= value <= 1):
                    value = 0.0
                    
                # Apply non-linear scaling for better visualization
                scaled_value = value ** 0.7
                
                # Calculate bar dimensions
                bar_x = start_x + i * (bar_width + bar_spacing)
                bar_height_scaled = int(bar_height * scaled_value)
                bar_rect = QRect(
                    int(bar_x),
                    rect.bottom() - bar_height_scaled,
                    bar_width,
                    bar_height_scaled
                )
                
                # Create gradient for the bar
                start = QPointF(bar_rect.left(), bar_rect.top())
                end = QPointF(bar_rect.right(), bar_rect.top())
                gradient = QLinearGradient(start, end)
                hue = 0.6 - (0.6 * scaled_value)  # Blue to cyan gradient
                gradient.setColorAt(0.0, QColor.fromHslF(hue, 0.8, 0.5, 0.9))
                gradient.setColorAt(1.0, QColor.fromHslF(hue, 0.9, 0.7, 0.9))
                
                # Draw the bar
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(gradient)
                painter.drawRoundedRect(bar_rect, corner_radius, corner_radius)
                
                # Add highlight at the top of the bar
                if bar_height_scaled > 5:
                    highlight_start = QPointF(bar_rect.left(), bar_rect.top())
                    highlight_end = QPointF(bar_rect.right(), bar_rect.top())
                    highlight = QLinearGradient(highlight_start, highlight_end)
                    highlight.setColorAt(0.0, QColor(255, 255, 255, 100))
                    highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
                    painter.setBrush(highlight)
                    highlight_rect = QRect(bar_rect)
                    highlight_rect.setHeight(min(5, bar_rect.height()))
                    painter.drawRoundedRect(highlight_rect, corner_radius, corner_radius)
        except Exception as e:
            logger.error(f"Error in draw_spectrum: {e}", exc_info=True)
                
    def draw_test_pattern(self, painter: QPainter, rect: QRect):
        """Draw a test pattern for debugging."""
        try:
            # Draw a gradient background
            gradient = QLinearGradient(0, 0, rect.width(), rect.height())
            gradient.setColorAt(0, QColor(50, 50, 100, 180))
            gradient.setColorAt(1, QColor(30, 30, 60, 200))
            painter.fillRect(rect, gradient)
            
            # Draw test pattern (diagonal lines)
            pen = QPen(QColor(100, 200, 255, 100), 1)
            painter.setPen(pen)
            for i in range(0, rect.width(), 10):
                painter.drawLine(i, 0, i, rect.height())
            for i in range(0, rect.height(), 10):
                painter.drawLine(0, i, rect.width(), i)
                
            # Draw test text
            font = painter.font()
            font.setBold(True)
            font.setPointSize(12)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "NixWhisper Overlay\nTest Pattern")
            
        except Exception as e:
            logger.error(f"Error in draw_test_pattern: {e}", exc_info=True)
                
    def mousePressEvent(self, event):
        """Allow moving the window by dragging."""
        self.drag_start = event.globalPosition().toPoint()
        
    def mouseMoveEvent(self, event):
        """Move the window when dragging."""
        if hasattr(self, 'drag_start'):
            delta = event.globalPosition().toPoint() - self.drag_start
            self.move(self.pos() + delta)
            self.drag_start = event.globalPosition().toPoint()
            
    def mouseReleaseEvent(self, event):
        """Snap to screen edges when released."""
        if hasattr(self, 'drag_start'):
            del self.drag_start
            self.update_position()
            
    def showEvent(self, event):
        """Ensure window stays on top when shown."""
        self.raise_()
        self.activateWindow()
        super().showEvent(event)

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
    update_level = pyqtSignal(float)  # Normalized audio level (0.0 to 1.0)
    update_spectrum = pyqtSignal(list)  # Frequency spectrum data
    finished = pyqtSignal(bytes)  # Recorded audio data
    silence_detected = pyqtSignal()  # Signal emitted when silence is detected
    
    # FFT parameters
    FFT_WINDOW_SIZE = 1024
    FFT_HOP_SIZE = 512
    SAMPLE_RATE = 16000
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, 
                 silence_threshold: float = 0.01, silence_duration: float = 2.0):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        
        self.recorder = AudioRecorder(
            sample_rate=sample_rate,
            channels=channels,
            blocksize=self.FFT_WINDOW_SIZE,
            silence_threshold=silence_threshold,
            silence_duration=silence_duration
        )
        self.is_recording = False
        self.audio_buffer = np.array([], dtype=np.float32)
        self.fft_window = np.hanning(self.FFT_WINDOW_SIZE)

    def _audio_callback(self, audio_data, rms, is_silent):
        """Callback for audio data from the recorder."""
        if not self.is_recording:
            return
            
        try:
            # Convert to float32 if needed
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / np.iinfo(audio_data.dtype).max
            
            # Calculate RMS level (0.0 to 1.0)
            current_rms = min(1.0, rms * 2.0)  # Scale RMS for better visibility
            self.update_level.emit(current_rms)
            
            # Process audio for spectrum analysis
            self.process_audio_spectrum(audio_data)
            
            # Buffer the audio data for transcription
            self.audio_buffer = np.append(self.audio_buffer, audio_data)
            
            # Handle silence detection
            if is_silent and self.is_recording:
                logger.info("Silence detected, stopping recording")
                self.silence_detected.emit()
                self.stop()
            
        except Exception as e:
            logger.error(f"Error in audio callback: {e}", exc_info=True)

    def process_audio_spectrum(self, audio_data):
        """Process audio data for spectrum visualization.
        
        Args:
            audio_data: Numpy array of audio samples
        """
        try:
            if audio_data is None or len(audio_data) == 0:
                logger.warning("Received empty audio data for spectrum processing")
                return
                
            # Apply window function
            windowed = audio_data * self.fft_window
            
            # Compute FFT
            fft = np.fft.rfft(windowed)
            fft = np.abs(fft) / (len(fft) * 2)  # Normalize
            
            # Convert to dB scale and apply some smoothing
            fft = 20 * np.log10(fft + 1e-10)  # Add small value to avoid log(0)
            fft = np.maximum(fft, -80)  # Clip at -80dB
            fft = (fft + 80) / 80  # Scale to 0-1 range
            
            # Downsample the spectrum to reduce the number of points
            target_bins = 32
            if len(fft) > target_bins:
                # Use max pooling for better visualization of peaks
                step = len(fft) // target_bins
                fft = np.array([np.max(fft[i:i+step]) for i in range(0, len(fft), step)])
            
            # Ensure we have exactly target_bins
            if len(fft) < target_bins:
                # Pad with minimum value if needed
                fft = np.pad(fft, (0, target_bins - len(fft)), 'minimum')
            elif len(fft) > target_bins:
                fft = fft[:target_bins]
                
            # Apply some smoothing between frames
            if not hasattr(self, 'prev_spectrum'):
                self.prev_spectrum = fft
            else:
                # Simple exponential smoothing
                smoothing_factor = 0.5
                fft = smoothing_factor * fft + (1 - smoothing_factor) * self.prev_spectrum
                self.prev_spectrum = fft
                
            # Ensure values are in valid range
            fft = np.clip(fft, 0.0, 1.0)
            
            # Log some debug info (but not too often)
            if not hasattr(self, 'last_spectrum_log') or time.time() - getattr(self, 'last_spectrum_log', 0) > 5.0:
                logger.debug(f"Spectrum range: min={np.min(fft):.2f}, max={np.max(fft):.2f}, mean={np.mean(fft):.2f}")
                self.last_spectrum_log = time.time()
                
            # Emit the spectrum data
            self.update_spectrum.emit(fft.tolist())
            
        except Exception as e:
            logger.error(f"Error processing audio spectrum: {e}", exc_info=True)
            # Emit empty spectrum to clear the display
            self.update_spectrum.emit([0] * 32)

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
        self.overlay = None
        self.recording_shortcut = None
        
        # Silence detection settings
        self.silence_threshold = 0.01  # Default threshold
        self.silence_duration = 2.0    # Default duration in seconds
        self.enable_silence_detection = True  # Default to enabled
        
        # Initialize UI components
        self.init_ui()
        self.init_tray_icon()
        self.init_overlay()
        self.setup_shortcuts()
        
        # Hide the main window initially
        self.hide()
        
    def init_overlay(self):
        """Initialize the overlay window."""
        logger.debug("Preparing overlay window...")
        self.overlay = None  # Will be created when needed during recording
        
    def setup_shortcuts(self):
        """Set up global keyboard shortcuts."""
        # Register global shortcut (Ctrl+Alt+Space)
        from PyQt6.QtGui import QKeySequence
        self.recording_shortcut = QShortcut(
            QKeySequence("Ctrl+Alt+Space"),
            self,
            self.toggle_recording
        )
        
    def show_overlay(self, show: bool = True):
        """Show or hide the overlay window."""
        if show:
            if not self.overlay:
                try:
                    logger.debug("Creating overlay window...")
                    self.overlay = OverlayWindow()
                    
                    # Position the overlay near the system tray icon
                    screen_geometry = QApplication.primaryScreen().availableGeometry()
                    overlay_width = 400
                    overlay_height = 100
                    
                    # Get the system tray icon geometry if available
                    tray_geometry = self.tray_icon.geometry() if self.tray_icon else None
                    
                    if tray_geometry and tray_geometry.isValid():
                        # Position to the left of the tray icon
                        x = tray_geometry.left() - overlay_width - 10  # 10px padding from tray
                        y = tray_geometry.top() - overlay_height // 2 + tray_geometry.height() // 2
                        
                        # Ensure the overlay stays on screen
                        if x < screen_geometry.left():
                            x = screen_geometry.left()
                        if y + overlay_height > screen_geometry.bottom():
                            y = screen_geometry.bottom() - overlay_height
                        if y < screen_geometry.top():
                            y = screen_geometry.top()
                    else:
                        # Fallback to bottom right if tray geometry is not available
                        x = screen_geometry.right() - overlay_width - 20  # 20px from right
                        y = screen_geometry.bottom() - overlay_height - 50  # 50px from bottom
                    
                    self.overlay.setGeometry(x, y, overlay_width, overlay_height)
                    logger.debug(f"Overlay window created at ({x}, {y}), size: {overlay_width}x{overlay_height}")
                except Exception as e:
                    logger.error(f"Error creating overlay: {e}", exc_info=True)
                    return
            
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()
        elif self.overlay:
            self.overlay.hide()
            # Clean up the overlay when not in use
            self.overlay.deleteLater()
            self.overlay = None
            
    def update_overlay_level(self, level: float):
        """Update the audio level in the overlay."""
        if self.overlay and self.overlay.isVisible():
            self.overlay.update_audio_level(level)
            
    def update_overlay_spectrum(self, spectrum: List[float]):
        """Update the audio spectrum in the overlay."""
        if self.overlay and self.overlay.isVisible():
            self.overlay.update_spectrum(spectrum)
    
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
        
        # Silence detection settings
        silence_group = QGroupBox("Silence Detection")
        silence_layout = QVBoxLayout()
        
        # Enable/disable silence detection
        self.silence_enable_cb = QCheckBox("Enable silence detection")
        self.silence_enable_cb.setChecked(self.enable_silence_detection)
        self.silence_enable_cb.stateChanged.connect(self.toggle_silence_detection)
        silence_layout.addWidget(self.silence_enable_cb)
        
        # Threshold slider
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Sensitivity:"))
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(1, 100)
        self.threshold_slider.setValue(int(self.silence_threshold * 1000))
        self.threshold_slider.valueChanged.connect(self.update_silence_threshold)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(QLabel(f"{self.silence_threshold:.3f}"))
        self.threshold_value = threshold_layout.itemAt(2).widget()
        silence_layout.addLayout(threshold_layout)
        
        # Duration slider
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_slider = QSlider(Qt.Orientation.Horizontal)
        self.duration_slider.setRange(1, 10)  # 1-10 seconds
        self.duration_slider.setValue(int(self.silence_duration))
        self.duration_slider.valueChanged.connect(self.update_silence_duration)
        duration_layout.addWidget(self.duration_slider)
        duration_layout.addWidget(QLabel(f"{self.silence_duration:.1f}"))
        self.duration_value = duration_layout.itemAt(2).widget()
        silence_layout.addLayout(duration_layout)
        
        silence_group.setLayout(silence_layout)
        layout.addWidget(silence_group)
        
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
        logger.debug("Starting recording...")
        self.record_button.setText("Stop Recording")
        self.status_label.setText("Recording...")
        self.transcription_display.setText("")
        self.copy_button.setEnabled(False)
        
        # Show overlay with recording feedback
        self.show_overlay(True)
        if self.overlay:
            logger.debug("Setting overlay to recording state")
            self.overlay.set_recording(True)
        else:
            logger.warning("Overlay is not initialized")
        
        try:
            # Start recording in a separate thread with current silence detection settings
            logger.debug("Creating recording thread")
            self.recording_thread = RecordingThread(
                silence_threshold=self.silence_threshold,
                silence_duration=self.silence_duration
            )
            
            # Connect signals
            logger.debug("Connecting signals")
            self.recording_thread.update_level.connect(self.update_level_meter)
            self.recording_thread.update_spectrum.connect(self.update_spectrum)
            self.recording_thread.finished.connect(self.on_recording_finished)
            self.recording_thread.silence_detected.connect(self.on_silence_detected)
            
            # Start the thread
            logger.debug("Starting recording thread")
            self.recording_thread.start()
            logger.debug("Recording thread started")
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            if self.overlay:
                self.overlay.hide()
        
    def update_spectrum(self, spectrum: List[float]):
        """Update the audio spectrum visualization."""
        try:
            if not isinstance(spectrum, (list, np.ndarray)):
                logger.error(f"Invalid spectrum data type: {type(spectrum)}")
                return
                
            logger.debug(f"Updating spectrum with {len(spectrum)} frequency bins")
            if not spectrum:
                logger.warning("Received empty spectrum data")
                return
            
            # Ensure spectrum is a list of numbers
            try:
                spectrum = [float(x) for x in spectrum]
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid spectrum data format: {e}")
                return
                
            # Log some debug info about the spectrum data
            logger.debug(f"Spectrum range: min={min(spectrum):.4f}, max={max(spectrum):.4f}, avg={sum(spectrum)/len(spectrum):.4f}")
            
            # Ensure the overlay exists and is visible
            if not hasattr(self, 'overlay') or not self.overlay:
                logger.warning("Overlay not available, recreating...")
                self.init_overlay()
                
            if self.overlay:
                # Make sure the overlay is visible
                if not self.overlay.isVisible():
                    self.overlay.show()
                # Update the spectrum
                self.overlay.update_spectrum(spectrum)
                # Force immediate repaint
                self.overlay.update()
                QApplication.processEvents()
                
        except Exception as e:
            logger.error(f"Error in update_spectrum: {e}", exc_info=True)
    
    def update_audio_level(self, level):
        """Update the audio level visualization."""
        if self._peak_timer:
            self._peak_timer.stop()
        self._peak_timer = QTimer()
        self._peak_timer.timeout.connect(self.reset_peak)
        self._peak_timer.start(500)
        self._peak_level = level
        self.update()
    
    def stop_recording(self):
        """Stop recording and start transcription."""
        if self.recording_thread and self.recording_thread.isRunning():
            # Update the overlay
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.set_recording(False)
            
            self.recording_thread.stop()
            self.record_button.setText("Processing...")
            self.record_button.setEnabled(False)
            
            # Only update status_label if it exists
            if hasattr(self, 'status_label'):
                self.status_label.setText("Processing...")
            
            # Hide the overlay after a short delay
            QTimer.singleShot(1000, lambda: self.show_overlay(False))
    
    def on_silence_detected(self):
        """Handle silence detection event."""
        logger.info("Silence detected, stopping recording")
        self.stop_recording()
        
    def toggle_silence_detection(self, state):
        """Toggle silence detection on/off."""
        self.enable_silence_detection = (state == Qt.CheckState.Checked.value)
        logger.debug(f"Silence detection {'enabled' if self.enable_silence_detection else 'disabled'}")
    
    def update_silence_threshold(self, value):
        """Update the silence threshold."""
        self.silence_threshold = value / 1000.0  # Convert from 1-100 to 0.001-0.1
        self.threshold_value.setText(f"{self.silence_threshold:.3f}")
        logger.debug(f"Silence threshold updated to {self.silence_threshold}")
    
    def update_silence_duration(self, value):
        """Update the silence duration."""
        self.silence_duration = value
        self.duration_value.setText(f"{self.silence_duration:.1f}")
        logger.debug(f"Silence duration updated to {self.silence_duration}s")

    def on_recording_finished(self, audio_data):
        """Handle recording finished event."""
        self.record_button.setText("Start Recording")
        self.record_button.setEnabled(True)
        
        if not audio_data:
            error_msg = "Recording failed - no audio data"
            if hasattr(self, 'status_label'):
                self.status_label.setText(error_msg)
            QTimer.singleShot(2000, lambda: self.show_overlay(False))
            return
        
        # Start transcription in a separate thread
        self.transcription_thread = TranscriptionThread(audio_data, self.model_manager)
        self.transcription_thread.finished.connect(self.on_transcription_finished)
        self.transcription_thread.error.connect(self.on_transcription_error)
        self.transcription_thread.start()
        
        # Update status if status_label exists
        if hasattr(self, 'status_label'):
            self.status_label.setText("Transcribing...")
    
    def on_transcription_finished(self, text):
        """Handle transcription finished event."""
        self.transcription_display.setText(text)
        if hasattr(self, 'status_label'):
            self.status_label.setText("Transcription complete")
        self.copy_button.setEnabled(True)
        
        # Hide overlay after a delay
        QTimer.singleShot(2000, lambda: self.show_overlay(False))
    
    def on_transcription_error(self, error):
        """Handle transcription error."""
        error_msg = f"Error: {error}"
        if hasattr(self, 'status_label'):
            self.status_label.setText(error_msg)
        self.record_button.setEnabled(True)
        
        # Hide overlay after a delay
        QTimer.singleShot(3000, lambda: self.show_overlay(False))
    
    def update_level_meter(self, level):
        """Update the audio level meter."""
        level = max(0.0, min(1.0, level))  # Clamp between 0 and 1
        self.level_meter.setValue(int(level * 100))
        self.update_overlay_level(level)
    
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
            
        # Clean up the overlay
        if self.overlay:
            self.overlay.deleteLater()
            self.overlay = None
        
        # Hide the window instead of closing it
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

def run_qt_gui():
    """Run the Qt-based GUI."""
    app = QApplication(sys.argv)
    
    # Set application style and name
    app.setStyle('Fusion')
    app.setApplicationName("NixWhisper")
    app.setApplicationDisplayName("NixWhisper")
    app.setDesktopFileName("nixwhisper")
    
    # Set dark theme by default
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(palette.ColorRole.Highlight, QColor(76, 163, 224))
    palette.setColor(palette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)
    
    # Initialize model manager
    model_manager = ModelManager()
    
    # Create and show main window
    window = NixWhisperWindow(model_manager)
    
    # Handle application state changes
    def on_application_state_changed(state):
        if state == Qt.ApplicationState.ApplicationActive and window.overlay:
            window.overlay.raise_()
            window.overlay.activateWindow()
    
    app.applicationStateChanged.connect(on_application_state_changed)
    
    # Show the window if system tray is not available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logger.info("System tray not available, showing main window")
        window.show()
    
    logger.info("Starting application event loop")
    sys.exit(app.exec())
