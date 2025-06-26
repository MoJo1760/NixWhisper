"""Qt-based GUI for NixWhisper."""
import logging
import sys
import time
import math
from typing import Optional

from nixwhisper.config import Config
from nixwhisper.x11_cursor import get_cursor_position, get_cursor_tracker  # Import cursor tracking functions
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Tuple

from PyQt6.QtCore import (
    Qt, QTimer, QPointF, QPoint, QRect, QRectF, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QThread, QSize, QEvent, QMetaObject
)
from evdev import InputDevice, categorize, ecodes, list_devices
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QLabel, QHBoxLayout, QProgressBar, QMessageBox, QSystemTrayIcon,
    QMenu, QDialog, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox,
    QFileDialog, QComboBox, QScrollArea, QFrame, QGroupBox,
    QDialogButtonBox, QStyle, QSizePolicy, QSlider
)
from PyQt6.QtGui import (
    QIcon, QAction, QPixmap, QPainter, QColor, QLinearGradient, QRadialGradient,
    QPen, QBrush, QPainterPath, QFont, QFontMetrics, QGuiApplication, QShortcut,
    QKeySequence
)
from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq
import threading
import re

import numpy as np
from nixwhisper.transcriber import create_transcriber
from nixwhisper.audio import AudioRecorder
from nixwhisper.model_manager import ModelManager
from nixwhisper.universal_typing import UniversalTyping

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
            
            # Install event filter to handle screen changes
            QGuiApplication.instance().primaryScreenChanged.connect(self._handle_primary_screen_changed)
            QGuiApplication.instance().screenAdded.connect(self._handle_screen_changed)
            QGuiApplication.instance().screenRemoved.connect(self._handle_screen_changed)
            
            # Animation settings with defaults
            self._animation_enabled = True
            self._animation_duration = 200  # ms
            self._animation_easing = QEasingCurve.Type.OutQuad
            
            # Performance optimization settings
            self._min_movement_threshold = 2  # pixels
            self._skip_animation_distance = 5  # pixels (don't animate small movements)
            self._last_animation_time = 0
            self._min_animation_interval = 16  # ~60fps (ms)
            self._last_position = QPoint(0, 0)
            
            # Available easing curves for configuration
            self._easing_curve_map = {
                'linear': QEasingCurve.Type.Linear,
                'in_quad': QEasingCurve.Type.InQuad,
                'out_quad': QEasingCurve.Type.OutQuad,
                'in_out_quad': QEasingCurve.Type.InOutQuad,
                'out_in_quad': QEasingCurve.Type.OutInQuad,
                'in_cubic': QEasingCurve.Type.InCubic,
                'out_cubic': QEasingCurve.Type.OutCubic,
                'in_out_cubic': QEasingCurve.Type.InOutCubic,
                'out_in_cubic': QEasingCurve.Type.OutInCubic,
                'in_quart': QEasingCurve.Type.InQuart,
                'out_quart': QEasingCurve.Type.OutQuart,
                'in_out_quart': QEasingCurve.Type.InOutQuart,
                'out_in_quart': QEasingCurve.Type.OutInQuart,
                'in_quint': QEasingCurve.Type.InQuint,
                'out_quint': QEasingCurve.Type.OutQuint,
                'in_out_quint': QEasingCurve.Type.InOutQuint,
                'out_in_quint': QEasingCurve.Type.OutInQuint,
                'in_sine': QEasingCurve.Type.InSine,
                'out_sine': QEasingCurve.Type.OutSine,
                'in_out_sine': QEasingCurve.Type.InOutSine,
                'out_in_sine': QEasingCurve.Type.OutInSine,
                'in_expo': QEasingCurve.Type.InExpo,
                'out_expo': QEasingCurve.Type.OutExpo,
                'in_out_expo': QEasingCurve.Type.InOutExpo,
                'out_in_expo': QEasingCurve.Type.OutInExpo,
                'in_circ': QEasingCurve.Type.InCirc,
                'out_circ': QEasingCurve.Type.OutCirc,
                'in_out_circ': QEasingCurve.Type.InOutCirc,
                'out_in_circ': QEasingCurve.Type.OutInCirc,
                'in_elastic': QEasingCurve.Type.InElastic,
                'out_elastic': QEasingCurve.Type.OutElastic,
                'in_out_elastic': QEasingCurve.Type.InOutElastic,
                'out_in_elastic': QEasingCurve.Type.OutInElastic,
                'in_back': QEasingCurve.Type.InBack,
                'out_back': QEasingCurve.Type.OutBack,
                'in_out_back': QEasingCurve.Type.InOutBack,
                'out_in_back': QEasingCurve.Type.OutInBack,
                'in_bounce': QEasingCurve.Type.InBounce,
                'out_bounce': QEasingCurve.Type.OutBounce,
                'in_out_bounce': QEasingCurve.Type.InOutBounce,
                'out_in_bounce': QEasingCurve.Type.OutInBounce,
            }
            
            # Initialize animation
            self._animation = QPropertyAnimation(self, b"pos")
            self._update_animation_settings()
            self._animation.finished.connect(self._on_animation_finished)
            self._is_animating = False
            self._pending_position = None  # Store position if animation is in progress
            
            # Visual properties
            self.radius = 15
            self.padding = 10
            self.spectrum = [0.0] * 32  # Initialize with zeros
            self.is_recording = False
            
            # Cursor-relative positioning properties
            self.cursor_relative_positioning = False  # Default to center positioning
            self.cursor_offset_x = 20  # Default horizontal offset from cursor
            self.cursor_offset_y = 20  # Default vertical offset from cursor
            self.last_cursor_position = None
            
            # Visual connection indicator properties
            self.show_cursor_connection = True  # Show visual connection to cursor
            self.connection_style = 'arrow'  # 'arrow', 'line', or 'none'
            self.connection_color = QColor(100, 200, 255, 180)  # Light blue with transparency
            self.connection_width = 2  # Line thickness
            self.arrow_size = 8  # Arrow head size in pixels
            self.connection_animated = True  # Enable pulsing/fading animation
            self._connection_animation_phase = 0.0  # Animation phase (0-1)
            
            # Set initial size and position (will be overridden by parent)
            self.resize(400, 80)  # Smaller height since we don't need as much space
            
            # Disable test pattern by default
            self.test_pattern = False
            
            # Setup animation timer for visual connection
            self._connection_timer = QTimer(self)
            self._connection_timer.timeout.connect(self._update_connection_animation)
            self._connection_timer.start(50)  # 20 FPS for smooth animation
            
            logger.debug("OverlayWindow initialized")
            
        except Exception as e:
            logger.error(f"Error initializing OverlayWindow: {e}", exc_info=True)
            raise
    
    def disable_test_pattern(self):
        """Disable the test pattern after initial display."""
        self.test_pattern = False
        self.update()
    
    def _update_connection_animation(self):
        """Update the animation phase for the cursor connection indicator."""
        if self.connection_animated and self.show_cursor_connection:
            self._connection_animation_phase += 0.05  # Increment animation
            if self._connection_animation_phase > 1.0:
                self._connection_animation_phase = 0.0
            self.update()  # Trigger repaint
    
    def _on_cursor_position_changed(self, cursor_pos):
        """Handle cursor position changes.
        
        Args:
            cursor_pos: CursorPosition object with the new cursor position and screen info
        """
        if not self.cursor_relative_positioning:
            logger.debug("Ignoring cursor position change - cursor-relative positioning is disabled")
            return
            
        try:
            logger.debug(
                f"Cursor position changed - x={cursor_pos.x}, y={cursor_pos.y}, "
                f"screen={cursor_pos.screen_number}, "
                f"screen_geometry=({cursor_pos.screen_x},{cursor_pos.screen_y} {cursor_pos.screen_width}x{cursor_pos.screen_height})"
            )
            
            # Update the last cursor position
            prev_pos = self.last_cursor_position
            self.last_cursor_position = (cursor_pos.x, cursor_pos.y)
            
            # Calculate movement delta if we had a previous position
            if prev_pos is not None:
                dx = cursor_pos.x - prev_pos[0]
                dy = cursor_pos.y - prev_pos[1]
                distance = (dx**2 + dy**2) ** 0.5
                logger.debug(f"Cursor moved {distance:.1f}px (dx={dx}, dy={dy}) from previous position")
            
            # Only update position if window is visible
            if self.isVisible():
                logger.debug("Window is visible, updating position...")
                self.update_position()
            else:
                logger.debug("Window is not visible, skipping position update")
                
        except Exception as e:
            logger.error(f"Error in cursor position callback: {e}", exc_info=True)
    
    def enable_cursor_relative_positioning(self, enabled: bool = True):
        """Enable or disable cursor-relative positioning.
        
        Args:
            enabled: True to enable cursor-relative positioning, False for center positioning
        """
        logger.debug(f"enable_cursor_relative_positioning({enabled}) called")
        
        if enabled == self.cursor_relative_positioning:
            logger.debug("Cursor-relative positioning already in the requested state, no change needed")
            return  # No change needed
            
        self.cursor_relative_positioning = enabled
        logger.info(f"{'Enabling' if enabled else 'Disabling'} cursor-relative positioning")
        
        if enabled:
            # Get cursor tracker instance
            cursor_tracker = get_cursor_tracker()
            
            if cursor_tracker:
                # Log current cursor position for debugging
                try:
                    cursor_pos = get_cursor_position(include_screen_info=True)
                    if cursor_pos:
                        logger.debug(
                            f"Current cursor position: x={cursor_pos.x}, y={cursor_pos.y}, "
                            f"screen={cursor_pos.screen_number}, "
                            f"screen_geometry=({cursor_pos.screen_x},{cursor_pos.screen_y} {cursor_pos.screen_width}x{cursor_pos.screen_height})"
                        )
                except Exception as e:
                    logger.warning(f"Failed to get initial cursor position: {e}")
                
                # Register callback and start polling
                try:
                    # Store the callback reference to prevent garbage collection
                    self._cursor_callback = self._on_cursor_position_changed
                    cursor_tracker.register_callback(self._cursor_callback)
                    logger.debug("Successfully registered cursor position callback")
                    
                    cursor_tracker.start_polling()
                    logger.info("Started cursor position polling")
                    
                    # Log polling status
                    logger.debug(
                        f"Cursor tracker status - is_polling: {cursor_tracker.is_polling()}, "
                        f"polling_interval: {cursor_tracker.polling_interval}ms, "
                        f"callbacks_registered: {len(cursor_tracker.callbacks) if hasattr(cursor_tracker, 'callbacks') else 'N/A'}"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to enable cursor tracking: {e}", exc_info=True)
                    self.cursor_relative_positioning = False
                    return
            else:
                logger.error("Failed to get cursor tracker, cursor-relative positioning disabled")
                self.cursor_relative_positioning = False
        else:
            # Unregister cursor position callback
            cursor_tracker = get_cursor_tracker()
            if cursor_tracker and hasattr(self, '_cursor_callback'):
                try:
                    cursor_tracker.unregister_callback(self._cursor_callback)
                    logger.debug("Successfully unregistered cursor position callback")
                    
                    cursor_tracker.stop_polling()
                    logger.info("Stopped cursor position polling")
                    
                    # Log final status
                    logger.debug(
                        f"Cursor tracker status after stopping - is_polling: {cursor_tracker.is_polling()}, "
                        f"callbacks_registered: {len(cursor_tracker.callbacks) if hasattr(cursor_tracker, 'callbacks') else 'N/A'}"
                    )
                    
                    del self._cursor_callback
                except Exception as e:
                    logger.error(f"Error removing cursor callback: {e}", exc_info=True)
        
        self.cursor_relative_positioning = enabled
        
        # Update the position immediately when toggling
        self.update_position()
    
    def set_cursor_offset(self, x_offset: int = 20, y_offset: int = 20):
        """Set the offset from cursor position.
        
        Args:
            x_offset: Horizontal offset in pixels (default: 20, min: -1000, max: 1000)
            y_offset: Vertical offset in pixels (default: 20, min: -1000, max: 1000)
            
        Note:
            Negative values position the window to the left/above the cursor.
            Positive values position the window to the right/below the cursor.
        """
        # Validate input ranges
        x_offset = max(-1000, min(1000, int(x_offset)))
        y_offset = max(-1000, min(1000, int(y_offset)))
        
        # Only update if the values have changed
        if self.cursor_offset_x == x_offset and self.cursor_offset_y == y_offset:
            return
            
        self.cursor_offset_x = x_offset
        self.cursor_offset_y = y_offset
        
        logger.debug(f"Cursor offset set to ({x_offset}, {y_offset})")
        
        # Update position if we're in cursor-relative mode
        if self.cursor_relative_positioning:
            logger.debug("Updating window position due to offset change")
            self.update_position()
    
    def set_cursor_connection_style(self, style: str = 'arrow'):
        """Set the visual connection style between overlay and cursor.
        
        Args:
            style: Connection style - 'arrow', 'line', or 'none'
        """
        valid_styles = ['arrow', 'line', 'none']
        if style not in valid_styles:
            logger.warning(f"Invalid connection style '{style}', using 'arrow'")
            style = 'arrow'
        
        self.connection_style = style
        logger.debug(f"Cursor connection style set to '{style}'")
        self.update()  # Trigger repaint
    
    def set_cursor_connection_enabled(self, enabled: bool = True):
        """Enable or disable the visual cursor connection.
        
        Args:
            enabled: True to show connection, False to hide
        """
        self.show_cursor_connection = enabled
        logger.debug(f"Cursor connection {'enabled' if enabled else 'disabled'}")
        self.update()  # Trigger repaint
    
    def set_cursor_connection_color(self, color: QColor = None):
        """Set the color of the cursor connection indicator.
        
        Args:
            color: QColor object, defaults to light blue if None
        """
        if color is None:
            color = QColor(100, 200, 255, 180)
        
        self.connection_color = color
        logger.debug(f"Cursor connection color set to {color.name()}")
        self.update()  # Trigger repaint
    
    def set_cursor_connection_animated(self, animated: bool = True):
        """Enable or disable animation for the cursor connection.
        
        Args:
            animated: True for pulsing animation, False for static
        """
        self.connection_animated = animated
        logger.debug(f"Cursor connection animation {'enabled' if animated else 'disabled'}")
    
    def get_cursor_connection_settings(self) -> dict:
        """Get current cursor connection settings.
        
        Returns:
            Dictionary with connection settings
        """
        return {
            'enabled': self.show_cursor_connection,
            'style': self.connection_style,
            'color': self.connection_color.name(),
            'width': self.connection_width,
            'arrow_size': self.arrow_size,
            'animated': self.connection_animated
        }
    
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
        """Position the window based on cursor position or center of screen.
        
        This method handles both single and multi-monitor setups by using the screen
        that contains the cursor for positioning the overlay window. It includes
        comprehensive error handling and fallback mechanisms.
        """
        logger.debug("Updating overlay window position...")
        
        if not self.cursor_relative_positioning:
            logger.debug("Cursor-relative positioning is disabled, using center positioning")
            cursor_pos = get_cursor_position(include_screen_info=True)
            screen_num = cursor_pos.screen_number if cursor_pos else None
            logger.debug(f"Positioning at center of screen {screen_num}")
            self._position_at_center(screen_num)
            return

        try:
            logger.debug("Getting cursor position with screen info...")
            cursor_pos = get_cursor_position(include_screen_info=True)
            if cursor_pos is None:
                logger.warning("Failed to get cursor position, falling back to center positioning")
                self._position_at_center()
                return
            
            logger.debug(f"Cursor position: x={cursor_pos.x}, y={cursor_pos.y}, "
                         f"screen={cursor_pos.screen_number}, "
                         f"screen_geometry=({cursor_pos.screen_x},{cursor_pos.screen_y} {cursor_pos.screen_width}x{cursor_pos.screen_height})")
            
            # Update the last cursor position
            self.last_cursor_position = (cursor_pos.x, cursor_pos.y)
            
            # Get available screens
            screens = QGuiApplication.screens()
            logger.debug(f"Found {len(screens)} screens")
            
            if not screens:
                logger.warning("No screens found, falling back to center positioning")
                self._position_at_center()
                return
                
            # Log all screens for debugging
            for i, screen in enumerate(screens):
                geom = screen.geometry()
                logger.debug(f"  Screen {i}: {geom.x()},{geom.y()} {geom.width()}x{geom.height()}")
                
            # Find the screen that contains the cursor
            # Use the screen number from our cursor tracking system since it's already calculated correctly
            target_screen = None
            screen_geometry = None
            
            if 0 <= cursor_pos.screen_number < len(screens):
                target_screen = screens[cursor_pos.screen_number]
                screen_geometry = target_screen.geometry()
                logger.debug(f"Using screen {cursor_pos.screen_number}: {target_screen.name()} at {screen_geometry}")
            else:
                logger.warning(f"Invalid screen number {cursor_pos.screen_number}, searching manually")
                # Fallback to manual search using absolute cursor coordinates
                cursor_abs_x = cursor_pos.screen_x + cursor_pos.x
                cursor_abs_y = cursor_pos.screen_y + cursor_pos.y
                
                for screen in screens:
                    try:
                        geom = screen.geometry()
                        if geom.contains(cursor_abs_x, cursor_abs_y):
                            target_screen = screen
                            screen_geometry = geom
                            logger.debug(f"Found cursor on screen: {screen.name()} at {geom}")
                            break
                    except Exception as e:
                        logger.warning(f"Error checking screen {screen.name()}: {e}")
            
            # Fall back to primary screen if no screen contains the cursor
            if target_screen is None or screen_geometry is None:
                logger.warning("Cursor not found on any screen, falling back to primary screen")
                target_screen = QGuiApplication.primaryScreen()
                if target_screen is None:
                    logger.error("No primary screen available")
                    return
                screen_geometry = target_screen.geometry()
            
            # Get window dimensions
            window_size = self.size()
            if not window_size.isValid() or window_size.width() <= 0 or window_size.height() <= 0:
                logger.error(f"Invalid window size: {window_size}")
                return
                
            # Calculate the window position relative to the cursor with offset
            # Convert cursor position to absolute coordinates first
            cursor_abs_x = cursor_pos.screen_x + cursor_pos.x
            cursor_abs_y = cursor_pos.screen_y + cursor_pos.y
            
            x = cursor_abs_x + self.cursor_offset_x
            y = cursor_abs_y + self.cursor_offset_y
            
            # Get screen boundaries with safe margins
            screen_left = screen_geometry.x() + 10  # 10px margin
            screen_top = screen_geometry.y() + 10
            screen_right = screen_geometry.x() + screen_geometry.width() - 10
            screen_bottom = screen_geometry.y() + screen_geometry.height() - 10
            
            # Adjust position to keep window on screen with margins
            if x + window_size.width() > screen_right:
                x = screen_right - window_size.width()
            if y + window_size.height() > screen_bottom:
                y = screen_bottom - window_size.height()
            if x < screen_left:
                x = screen_left
            if y < screen_top:
                y = screen_top
                
            # Only reposition if the overlay would actually go off-screen
            # (removed aggressive 50px threshold repositioning)
            if x + window_size.width() > screen_right:
                x = max(screen_left, cursor_abs_x - window_size.width() - abs(self.cursor_offset_x))
            
            if y + window_size.height() > screen_bottom:
                y = max(screen_top, cursor_abs_y - window_size.height() - abs(self.cursor_offset_y))
            
            # Final bounds check
            x = max(screen_left, min(x, screen_right - window_size.width()))
            y = max(screen_top, min(y, screen_bottom - window_size.height()))
            
            # Move the window to the calculated position
            self.move(int(x), int(y))
            
            logger.info(
                f"Positioning overlay at ({x}, {y}) - "
                f"Screen {cursor_pos.screen_number} ({target_screen.name() if target_screen else 'unknown'}), "
                f"Cursor: rel=({cursor_pos.x}, {cursor_pos.y}) abs=({cursor_abs_x}, {cursor_abs_y}), "
                f"Screen geometry: {screen_geometry.x()},{screen_geometry.y()} {screen_geometry.width()}x{screen_geometry.height()}"
            )
            
        except Exception as e:
            logger.error(f"Error in update_position: {e}", exc_info=True)
            # Fall back to center positioning on any error
            self._position_at_center()
    
    def _position_at_center(self, screen_number: Optional[int] = None, force: bool = False):
        """Position the window at the bottom center of the specified screen or primary screen.
        
        Args:
            screen_number: The index of the screen to center on. If None, uses the primary screen.
            force: If True, forces repositioning even if the window is already in a valid position.
            
        Returns:
            bool: True if positioning was successful, False otherwise
        """
        logger.debug(f"_position_at_center called with screen_number={screen_number}, force={force}")
        
        try:
            # Get all available screens
            screens = QGuiApplication.screens()
            logger.debug(f"Found {len(screens)} screens in total")
            
            # Log all screens for debugging
            for i, scrn in enumerate(screens):
                geom = scrn.geometry()
                logger.debug(f"  Screen {i}: {geom.x()},{geom.y()} {geom.width()}x{geom.height()} "
                            f"(name: {scrn.name()}, model: {scrn.model() if hasattr(scrn, 'model') else 'N/A'})")
            
            if not screens:
                logger.error("No screens found, cannot position window")
                return False
            
            # Get the target screen
            if screen_number is None or screen_number >= len(screens) or screen_number < 0:
                logger.debug("Using primary screen (screen_number not specified or invalid)")
                screen = QGuiApplication.primaryScreen()
                if screen:
                    screen_number = screens.index(screen)
                    logger.debug(f"Primary screen is at index {screen_number}")
                else:
                    logger.warning("No primary screen found, using first available screen")
                    screen = screens[0]
                    screen_number = 0
            else:
                logger.debug(f"Using screen {screen_number} as specified")
                screen = screens[screen_number]
            
            if not screen:
                logger.error(f"Failed to get screen {screen_number} for positioning")
                return False
                
            # Get both available and full geometry
            screen_geom = screen.availableGeometry()
            full_geom = screen.geometry()
            logger.debug(f"Screen {screen_number} - Available: {screen_geom.x()},{screen_geom.y()} "
                        f"{screen_geom.width()}x{screen_geom.height()}, Full: {full_geom.x()},{full_geom.y()} "
                        f"{full_geom.width()}x{full_geom.height()}")
            
            window_size = self.size()
            logger.debug(f"Window size: {window_size.width()}x{window_size.height()}")
            
            # Calculate center-bottom position with some margin from bottom
            x = screen_geom.x() + (screen_geom.width() - window_size.width()) // 2
            y = screen_geom.y() + screen_geom.height() - window_size.height() - 50  # 50px from bottom
            
            # Ensure position is within screen bounds
            x = max(screen_geom.x(), min(x, screen_geom.x() + screen_geom.width() - window_size.width()))
            y = max(screen_geom.y(), min(y, screen_geom.y() + screen_geom.height() - window_size.height()))
            
            # Get current position for comparison
            current_pos = self.pos()
            position_changed = (abs(current_pos.x() - x) >= 2 or abs(current_pos.y() - y) >= 2)
            
            # Skip if position hasn't changed and we're not forcing a move
            if not force and not position_changed:
                logger.debug("Window already in correct position, skipping move")
                return True
            
            # Log the move operation
            logger.info(
                f"Positioning overlay at ({x}, {y}) - "
                f"Screen {screen_number} ({screen.name() if screen else 'unknown'}), "
                f"Current: ({current_pos.x()}, {current_pos.y()}), "
                f"Screen geometry: {screen_geom.x()},{screen_geom.y()} {screen_geom.width()}x{screen_geom.height()}"
            )
            
            # Move the window
            self.move(x, y)
            return True
            
        except Exception as e:
            logger.error(f"Error in _position_at_center: {e}", exc_info=True)
            
            # Fallback to primary screen if there's an error
            try:
                logger.warning("Attempting fallback to primary screen positioning")
                primary_screen = QGuiApplication.primaryScreen()
                if not primary_screen:
                    logger.error("No primary screen available for fallback positioning")
                    return False
                    
                screen_geom = primary_screen.availableGeometry()
                window_size = self.size()
                x = screen_geom.x() + (screen_geom.width() - window_size.width()) // 2
                y = screen_geom.y() + screen_geom.height() - window_size.height() - 50
                
                # Ensure position is within screen bounds
                x = max(screen_geom.x(), min(x, screen_geom.x() + screen_geom.width() - window_size.width()))
                y = max(screen_geom.y(), min(y, screen_geom.y() + screen_geom.height() - window_size.height()))
                
                logger.warning(
                    f"Moving to fallback position: ({x}, {y}) on primary screen "
                    f"(geometry: {screen_geom.x()},{screen_geom.y()} {screen_geom.width()}x{screen_geom.height()})"
                )
                
                self.move(x, y)
                return True
                
            except Exception as fallback_error:
                logger.error(
                    f"Critical error in fallback positioning: {fallback_error}", 
                    exc_info=True
                )
                return False
                
    def _handle_primary_screen_changed(self, screen):
        """Handle primary screen change events."""
        logger.debug(f"Primary screen changed to: {screen.name() if screen else 'None'}")
        if not self.cursor_relative_positioning:
            # If we're not in cursor-relative mode, update the position
            self.update_position()
    
    def _handle_screen_changed(self, screen):
        """Handle screen added/removed events."""
        logger.debug(f"Screen configuration changed: {screen.name() if screen else 'Unknown screen'}")
        # Always update position when screens change to ensure we're on a valid screen
        self.update_position()
    
    def showEvent(self, event):
        """Handle show events to ensure proper positioning."""
        super().showEvent(event)
        # Update position when shown to ensure we're on a valid screen
        self.update_position()
    
    def moveEvent(self, event):
        """Handle move events to ensure we stay on screen."""
        super().moveEvent(event)
        if self.cursor_relative_positioning:
            # If we're in cursor-relative mode, ensure we're still on screen
            # after the move (in case of screen configuration changes)
            QTimer.singleShot(0, self._ensure_on_screen)
    
    def _ensure_on_screen(self):
        """Ensure the window is on a visible screen."""
        try:
            # Get the geometry of the window
            window_geom = self.geometry()
            
            # Check if the window is on any screen
            on_screen = False
            for screen in QGuiApplication.screens():
                if screen.geometry().intersects(window_geom):
                    on_screen = True
                    break
            
            # If not on any screen, move to primary screen
            if not on_screen:
                logger.warning("Window not on any screen, moving to primary screen")
                self._position_at_center()
        except Exception as e:
            logger.error(f"Error ensuring window is on screen: {e}", exc_info=True)
            
    def _should_skip_animation(self, target_pos: QPoint) -> bool:
        """Determine if we should skip animation for this move.
        
        Args:
            target_pos: The target position to move to
            
        Returns:
            bool: True if animation should be skipped, False otherwise
        """
        current_time = time.time() * 1000  # Convert to ms
        
        # Skip if we're animating too frequently
        if (current_time - self._last_animation_time) < self._min_animation_interval:
            return True
            
        # Skip if movement is very small (reduces jitter)
        if (abs(self._last_position.x() - target_pos.x()) < self._min_movement_threshold and
            abs(self._last_position.y() - target_pos.y()) < self._min_movement_threshold):
            return True
            
        # Skip if the distance is very small (avoids unnecessary animations)
        if (abs(self.pos().x() - target_pos.x()) < self._skip_animation_distance and
            abs(self.pos().y() - target_pos.y()) < self._skip_animation_distance):
            return True
            
        return False
    
    def _animate_to_position(self, x: int, y: int):
        """Animate the window to the specified position.
        
        Args:
            x: Target x-coordinate
            y: Target y-coordinate
        """
        try:
            target_pos = QPoint(x, y)
            
            # If we're already at the target position, do nothing
            if self.pos() == target_pos:
                return
                
            # Check if we should skip animation for this move
            if self._should_skip_animation(target_pos):
                super().move(x, y)
                self._last_position = target_pos
                return
                
            # If we're already animating, store the target position and let the
            # animation finish before starting a new one
            if self._is_animating:
                self._pending_position = target_pos
                return
                
            # Stop any running animation
            if self._animation.state() == QPropertyAnimation.State.Running:
                self._animation.stop()
                
            # Set up the animation
            self._animation.setStartValue(self.pos())
            self._animation.setEndValue(target_pos)
            self._is_animating = True
            
            # Start the animation
            self._animation.start()
            self._last_animation_time = time.time() * 1000  # Update last animation time
            self._last_position = target_pos
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"Animating window from {self.pos().x()},{self.pos().y()} to {x},{y} "
                    f"(distance: {abs(self.pos().x() - x) + abs(self.pos().y() - y)}px)"
                )
            
        except Exception as e:
            logger.error(f"Error animating window: {e}", exc_info=True)
            # Fall back to direct move if animation fails
            self.move(x, y)
    
    def _update_animation_settings(self):
        """Update animation settings based on current configuration."""
        self._animation.setDuration(self._animation_duration)
        self._animation.setEasingCurve(QEasingCurve(self._animation_easing))
        logger.debug(f"Updated animation settings: duration={self._animation_duration}ms, "
                   f"easing={self.get_easing_curve_name()}")
    
    def set_animation_enabled(self, enabled: bool):
        """Enable or disable window movement animations.
        
        Args:
            enabled: Whether to enable animations
        """
        if self._animation_enabled != enabled:
            self._animation_enabled = enabled
            logger.debug(f"Animations {'enabled' if enabled else 'disabled'}")
    
    def set_animation_duration(self, duration_ms: int):
        """Set the animation duration in milliseconds.
        
        Args:
            duration_ms: Duration in milliseconds (50-2000ms)
        """
        duration_ms = max(0, min(2000, int(duration_ms)))
        if self._animation_duration != duration_ms:
            self._animation_duration = duration_ms
            self._update_animation_settings()
    
    def set_animation_easing(self, easing_curve: str):
        """Set the animation easing curve.
        
        Args:
            easing_curve: Name of the easing curve (e.g., 'out_quad', 'in_out_cubic')
        """
        curve = self._easing_curve_map.get(easing_curve.lower())
        if curve is not None and self._animation_easing != curve:
            self._animation_easing = curve
            self._update_animation_settings()
    
    def get_easing_curve_name(self) -> str:
        """Get the name of the current easing curve.
        
        Returns:
            str: Name of the current easing curve
        """
        for name, curve in self._easing_curve_map.items():
            if curve == self._animation_easing:
                return name
        return 'unknown'
    
    def _on_animation_finished(self):
        """Handle animation finished event."""
        self._is_animating = False
        
        # If there's a pending position, animate to it
        if self._pending_position is not None:
            pending = self._pending_position
            self._pending_position = None
            self._animate_to_position(pending.x(), pending.y())
    
    def move(self, x: int, y: int):
        """Move the window to the specified position with animation if enabled.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Note:
            If animations are enabled, this will smoothly animate to the new position.
            If animations are disabled or the window isn't visible, it will move instantly.
        """
        try:
            # If animations are disabled, we're not visible, or not in cursor-relative mode, move directly
            if not self._animation_enabled or not self.isVisible() or not self.cursor_relative_positioning:
                # Stop any running animation
                if self._animation.state() == QPropertyAnimation.State.Running:
                    self._animation.stop()
                super().move(x, y)
                return
                
            # Otherwise, animate the move
            self._animate_to_position(x, y)
            
        except Exception as e:
            logger.error(f"Error moving window: {e}", exc_info=True)
            # Fall back to direct move if there's an error
            super().move(x, y)
    
    def handle_screen_change(self):
        """Handle screen resolution or configuration changes in a multi-monitor setup.
        
        This method is called when the screen configuration changes (e.g., monitor connected/disconnected,
        resolution changed, etc.). It ensures the overlay window stays properly positioned.
        """
        try:
            # Log the screen change event
            screens = QGuiApplication.screens()
            logger.debug(
                f"Screen configuration changed. Detected {len(screens)} screens. "
                f"Current window position: {self.x()}, {self.y()}"
            )
            
            # Log details about each screen for debugging
            for i, screen in enumerate(screens):
                geom = screen.availableGeometry()
                logger.debug(
                    f"  Screen {i}: {screen.name()} - "
                    f"{geom.width()}x{geom.height()} at ({geom.x()}, {geom.y()})"
                )
            
            # Update the window position
            if self.cursor_relative_positioning and self.last_cursor_position:
                # If we were tracking the cursor, try to maintain that relationship
                self.update_position()
            else:
                # Otherwise, just make sure we're on a valid screen
                self._ensure_on_screen()
                
        except Exception as e:
            logger.error(f"Error handling screen change: {e}", exc_info=True)
            # Fallback to primary screen if there's an error
            self._position_at_center(0)
    
    def _ensure_on_screen(self):
        """Ensure the window is visible on at least one screen."""
        try:
            screens = QGuiApplication.screens()
            if not screens:
                logger.warning("No screens found, cannot ensure window visibility")
                return
                
            window_rect = self.frameGeometry()
            
            # Check if the window is on any screen
            for screen in screens:
                if screen.availableGeometry().intersects(window_rect):
                    # Window is on this screen, no need to move it
                    return
            
            # If we get here, the window is not on any screen
            logger.warning("Window is not on any screen, moving to primary screen")
            self._position_at_center(0)
            
        except Exception as e:
            logger.error(f"Error ensuring window is on screen: {e}", exc_info=True)
            # Fallback to primary screen if there's an error
            self._position_at_center(0)
    
    def get_cursor_relative_settings(self) -> dict:
        """Get current cursor-relative positioning settings.
        
        Returns:
            Dictionary with current settings
        """
        return {
            'enabled': self.cursor_relative_positioning,
            'offset_x': self.cursor_offset_x,
            'offset_y': self.cursor_offset_y,
            'last_cursor_position': self.last_cursor_position
        }
    
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
            
            # Draw cursor connection indicator
            if (self.show_cursor_connection and self.cursor_relative_positioning and 
                self.connection_style != 'none'):
                self.draw_cursor_connection(painter)
            
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
    
    def draw_cursor_connection(self, painter: QPainter):
        """Draw visual connection between overlay and cursor position."""
        try:
            # Get current cursor position
            from nixwhisper.x11_cursor import get_cursor_position
            cursor_pos = get_cursor_position(include_screen_info=True)
            if not cursor_pos:
                return
            
            # Calculate absolute cursor position
            cursor_abs_x = cursor_pos.screen_x + cursor_pos.x
            cursor_abs_y = cursor_pos.screen_y + cursor_pos.y
            
            # Get overlay position and find connection point on overlay edge
            overlay_pos = self.pos()
            overlay_rect = self.rect()
            
            # Calculate the connection point on the overlay (closest edge to cursor)
            overlay_center_x = overlay_pos.x() + overlay_rect.width() / 2
            overlay_center_y = overlay_pos.y() + overlay_rect.height() / 2
            
            # Find the best connection point on overlay edge
            connection_point = self._find_connection_point(
                overlay_pos.x(), overlay_pos.y(), 
                overlay_rect.width(), overlay_rect.height(),
                cursor_abs_x, cursor_abs_y
            )
            
            # Convert connection point to local coordinates for drawing
            local_x = connection_point[0] - overlay_pos.x()
            local_y = connection_point[1] - overlay_pos.y()
            
            # Calculate direction vector from connection point to cursor
            dx = cursor_abs_x - connection_point[0]
            dy = cursor_abs_y - connection_point[1]
            distance = (dx * dx + dy * dy) ** 0.5
            
            if distance < 1:  # Too close, don't draw
                return
            
            # Normalize direction
            dx /= distance
            dy /= distance
            
            # Apply animation effect
            alpha = 180
            if self.connection_animated:
                # Pulsing effect
                pulse = math.sin(self._connection_animation_phase * 2 * math.pi)
                alpha = int(180 + pulse * 50)  # Vary between 130-230
            
            # Set up pen for drawing
            color = QColor(self.connection_color)
            color.setAlpha(alpha)
            pen = QPen(color, self.connection_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
            # Draw based on style
            if self.connection_style == 'line':
                # Simple line to cursor
                line_length = min(distance, 100)  # Limit line length
                end_x = local_x + dx * line_length
                end_y = local_y + dy * line_length
                painter.drawLine(QPointF(local_x, local_y), QPointF(end_x, end_y))
                
            elif self.connection_style == 'arrow':
                # Arrow pointing toward cursor
                arrow_length = min(distance, 60)  # Limit arrow length
                end_x = local_x + dx * arrow_length
                end_y = local_y + dy * arrow_length
                
                # Draw arrow shaft
                painter.drawLine(QPointF(local_x, local_y), QPointF(end_x, end_y))
                
                # Draw arrow head
                self._draw_arrow_head(painter, end_x, end_y, dx, dy, self.arrow_size, color)
                
        except Exception as e:
            logger.error(f"Error in draw_cursor_connection: {e}", exc_info=True)
    
    def _find_connection_point(self, rect_x, rect_y, rect_width, rect_height, target_x, target_y):
        """Find the best connection point on rectangle edge toward target."""
        # Calculate center of rectangle
        center_x = rect_x + rect_width / 2
        center_y = rect_y + rect_height / 2
        
        # Vector from center to target
        dx = target_x - center_x
        dy = target_y - center_y
        
        # Find intersection with rectangle edge
        if abs(dx) / rect_width > abs(dy) / rect_height:
            # Intersection with left or right edge
            if dx > 0:  # Right edge
                edge_x = rect_x + rect_width
                edge_y = center_y + dy * (rect_width / 2) / abs(dx)
            else:  # Left edge
                edge_x = rect_x
                edge_y = center_y - dy * (rect_width / 2) / abs(dx)
        else:
            # Intersection with top or bottom edge
            if dy > 0:  # Bottom edge
                edge_x = center_x + dx * (rect_height / 2) / abs(dy)
                edge_y = rect_y + rect_height
            else:  # Top edge
                edge_x = center_x - dx * (rect_height / 2) / abs(dy)
                edge_y = rect_y
        
        # Clamp to rectangle bounds
        edge_x = max(rect_x, min(rect_x + rect_width, edge_x))
        edge_y = max(rect_y, min(rect_y + rect_height, edge_y))
        
        return (edge_x, edge_y)
    
    def _draw_arrow_head(self, painter, x, y, dx, dy, size, color):
        """Draw an arrow head at the specified position."""
        # Calculate arrow head points
        head_angle = math.pi / 6  # 30 degrees
        
        # Left arrow head point
        left_x = x - size * (dx * math.cos(head_angle) - dy * math.sin(head_angle))
        left_y = y - size * (dy * math.cos(head_angle) + dx * math.sin(head_angle))
        
        # Right arrow head point
        right_x = x - size * (dx * math.cos(head_angle) + dy * math.sin(head_angle))
        right_y = y - size * (dy * math.cos(head_angle) - dx * math.sin(head_angle))
        
        # Draw arrow head lines
        painter.drawLine(QPointF(x, y), QPointF(left_x, left_y))
        painter.drawLine(QPointF(x, y), QPointF(right_x, right_y))
                
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
            
            # Log some debug info about the spectrum data
            logger.debug(f"Spectrum range: min={np.min(fft):.2f}, max={np.max(fft):.2f}, mean={np.mean(fft):.2f}")
            
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
    
    def __init__(self, model_manager: ModelManager, config: Optional[Config] = None):
        super().__init__()
        self.model_manager = model_manager
        self.config = config or Config()
        self.is_recording = False
        self._hotkey_thread = None  # Global hotkey thread
        self._stop_hotkey = False  # Flag to stop hotkey thread
        self.settings_dialog = None  # Store settings dialog reference
        self.recording_thread = None
        self.transcription_thread = None
        self.tray_icon = None
        self._toggle_recording_lock = threading.Lock()
        self._recording_signal = threading.Event()
        self.overlay = None
        self.universal_typer = UniversalTyping()  # Create a single instance
        
        # Initialize UI components
        self.silence_threshold = self.config.ui.silence_threshold
        self.silence_duration = self.config.ui.silence_duration
        self.enable_silence_detection = self.config.ui.silence_detection
        
        # Initialize peak level
        self._peak_level = 0.0
        
        # Define the reset_peak method before setting up the timer
        def reset_peak():
            """Reset the peak level for the audio level meter."""
            try:
                self._peak_level = 0.0
                if hasattr(self, 'overlay') and self.overlay and self.overlay.isVisible():
                    self.overlay.update()
            except Exception as e:
                logger.error(f"Error in reset_peak: {e}", exc_info=True)
        
        # Store the method reference
        self.reset_peak = reset_peak
        
        # Initialize peak timer for audio level visualization
        self._peak_timer = QTimer(self)  # Make it a child of the window
        self._peak_timer.setInterval(500)  # Update every 500ms
        self._peak_timer.timeout.connect(self.reset_peak)
        
        # Initialize UI components first
        self.init_ui()
        
        # Then set up the rest
        self.init_tray_icon()
        self.init_overlay()
        self.setup_shortcuts()
        
        # Initialize recording state
        self.update_recording_ui()
        
        # Hide the main window initially
        self.hide()
    
    def setup_shortcuts(self):
        """Set up global keyboard shortcuts using evdev."""
        try:
            # Kill any existing hotkey thread
            if self._hotkey_thread and self._hotkey_thread.is_alive():
                self._stop_hotkey = True
                self._hotkey_thread.join(timeout=1)

            # Start the hotkey listener thread
            self._stop_hotkey = False
            self._hotkey_thread = threading.Thread(
                target=self._hotkey_listener,
                args=(self.config.ui.hotkey,),
                daemon=True
            )
            self._hotkey_thread.start()
            logger.info(f"Started global hotkey listener thread with hotkey: {self.config.ui.hotkey}")
        except Exception as e:
            logger.error(f"Error setting up shortcuts: {e}", exc_info=True)

    def _parse_qt_hotkey(self, hotkey):
        """Parse Qt hotkey format into X11 format."""
        try:
            logger.debug(f"Parsing hotkey: {hotkey}")
            parts = hotkey.split('+')
            key = parts[-1].lower()
            modifiers = set(parts[:-1])
            return key, modifiers
        except Exception as e:
            logger.error(f"Error parsing hotkey: {e}")
            return None, None

    def _hotkey_listener(self, hotkey):
        """Listen for global hotkeys using evdev."""
        logger.debug(f"Starting hotkey listener with hotkey: {hotkey}")
        
        # Import evdev here to avoid import errors on non-Linux systems
        try:
            from evdev import InputDevice, list_devices, ecodes, categorize
        except ImportError as e:
            logger.error(f"Failed to import evdev: {e}")
            return
    
        try:
            # Parse Qt hotkey format
            parts = hotkey.lower().split('+')
            key = parts[-1]
            modifiers = set(parts[:-1])
            
            # Map modifiers and key to evdev codes
            modifier_map = {
                'ctrl': ecodes.KEY_LEFTCTRL,
                'control': ecodes.KEY_LEFTCTRL,
                'alt': ecodes.KEY_LEFTALT,
                'shift': ecodes.KEY_LEFTSHIFT,
                'meta': ecodes.KEY_LEFTMETA,
                'super': ecodes.KEY_LEFTMETA
            }
            
            key_map = {
                'space': ecodes.KEY_SPACE,
                'return': ecodes.KEY_ENTER,
                'enter': ecodes.KEY_ENTER,
                'esc': ecodes.KEY_ESC,
                'tab': ecodes.KEY_TAB
            }
            
            # Convert modifiers to evdev codes
            mod_codes = set(modifier_map[mod] for mod in modifiers if mod in modifier_map)
            
            # Convert key to evdev code
            if key in key_map:
                key_code = key_map[key]
            else:
                # Try to find key code by name
                key_name = f'KEY_{key.upper()}'
                if hasattr(ecodes, key_name):
                    key_code = getattr(ecodes, key_name)
                else:
                    logger.error(f"Unknown key: {key}")
                    return
            
            # Find all keyboard devices
            keyboards = [InputDevice(fn) for fn in list_devices()]
            keyboards = [dev for dev in keyboards if dev.name != 'py-evdev-uinput']
            
            if not keyboards:
                logger.error("No keyboard devices found")
                return
                
            pressed_keys = set()
            
            async def read_events():
                tasks = [handle_device(device) for device in keyboards]
                await asyncio.gather(*tasks)
            
            async def handle_device(device):
                try:
                    async for event in device.async_read_loop():
                        if event.type == ecodes.EV_KEY:
                            key_event = categorize(event)
                            
                            if key_event.keystate == key_event.key_down:
                                pressed_keys.add(key_event.scancode)
                                
                                # Check if hotkey is pressed
                                if key_event.scancode == key_code and mod_codes.issubset(pressed_keys):
                                    logger.debug("Hotkey activated!")
                                    # Schedule toggle_recording in the main thread
                                    try:
                                        logger.debug("Posting hotkey event to main thread")
                                        QApplication.postEvent(
                                            self,
                                            QEvent(QEvent.Type.User)
                                        )
                                    except Exception as e:
                                        logger.error(f"Error posting event: {e}", exc_info=True)
                            
                            elif key_event.keystate == key_event.key_up:
                                pressed_keys.discard(key_event.scancode)
                except Exception as e:
                    logger.error(f"Error reading device {device.name}: {e}")
            
            # Run event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while not self._stop_hotkey:
                try:
                    loop.run_until_complete(read_events())
                except Exception as e:
                    logger.error(f"Error in event loop: {e}")
                    time.sleep(0.1)  # Prevent tight loop on error
            
            # Cleanup
            for device in keyboards:
                try:
                    device.close()
                except Exception as e:
                    logger.error(f"Error closing device {device.name}: {e}")
            
            try:
                loop.close()
            except Exception as e:
                logger.error(f"Error closing event loop: {e}")
            
        except Exception as e:
            logger.error(f"Error in hotkey listener: {e}", exc_info=True)

    def toggle_recording(self):
        """Toggle recording state.
        
        This method is thread-safe and can be called from any thread.
        """
        try:
            with self._toggle_recording_lock:
                if self.is_recording:
                    self.stop_recording()
                else:
                    self.start_recording()
        except Exception as e:
            logger.error(f"Error in toggle_recording: {e}", exc_info=True)

    def update_recording_ui(self):
        """Update the UI to reflect the current recording state."""
        if hasattr(self, 'status_label'):
            self.status_label.setText("Recording..." if self.is_recording else "Ready to record")

    def init_ui(self):
        """Initialize the main window UI components."""
        try:
            self.setWindowTitle("NixWhisper")
            self.setWindowIcon(QIcon.fromTheme("audio-input-microphone"))
            
            # Create central widget and layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Status label
            self.status_label = QLabel("Ready to record")
            self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.status_label)
            
            # Start/Stop button
            self.record_button = QPushButton("Start Recording (Ctrl+Space)")
            self.record_button.clicked.connect(self.toggle_recording)
            layout.addWidget(self.record_button)
            
            # Settings button
            settings_button = QPushButton("Settings")
            settings_button.clicked.connect(self.show_settings)
            layout.addWidget(settings_button)
            
            # Quit button
            quit_button = QPushButton("Quit")
            quit_button.clicked.connect(QApplication.quit)
            layout.addWidget(quit_button)
            
            # Set window size
            self.resize(400, 200)
            
            # Show overlay when starting
            self.show_overlay(True)
            
        except Exception as e:
            logger.error(f"Error initializing UI: {e}", exc_info=True)
            raise

    def init_overlay(self, show: bool = False):
        """Initialize the overlay window.
        
        Args:
            show: If True, show the overlay after initialization
        """
        try:
            # Create overlay if it doesn't exist
            if not hasattr(self, 'overlay') or not self.overlay:
                self.overlay = OverlayWindow()
                logger.debug("Overlay window initialized")
                
                # Enable cursor positioning by default
                self.overlay.enable_cursor_relative_positioning(True)
                self.overlay.set_cursor_offset(40, 40)  # Default offset
                
                # Apply overlay config settings if available
                if hasattr(self.config, 'overlay') and self.config.overlay:
                    self.overlay.set_cursor_connection_enabled(self.config.overlay.cursor_connection_enabled)
                    self.overlay.set_cursor_connection_style(self.config.overlay.cursor_connection_style)
                    self.overlay.set_cursor_connection_animated(self.config.overlay.cursor_connection_animated)
                    # Convert color string to QColor
                    try:
                        color = QColor(self.config.overlay.cursor_connection_color)
                        if color.isValid():
                            self.overlay.set_cursor_connection_color(color)
                    except:
                        pass  # Use default color if invalid
                else:
                    # Enable visual connections by default if no config
                    self.overlay.set_cursor_connection_enabled(True)
                    self.overlay.set_cursor_connection_style('arrow')
                    self.overlay.set_cursor_connection_color(QColor(100, 200, 255, 200))
                
                # Set initial size
                overlay_width = 400
                overlay_height = 100
                self.overlay.resize(overlay_width, overlay_height)
                
                # Force immediate cursor-relative positioning
                from nixwhisper.x11_cursor import get_cursor_position
                cursor_pos = get_cursor_position(include_screen_info=True)
                if cursor_pos:
                    # Position relative to current cursor position
                    abs_x = cursor_pos.screen_x + cursor_pos.x
                    abs_y = cursor_pos.screen_y + cursor_pos.y
                    x = abs_x + 40  # Use default offset
                    y = abs_y + 40
                    self.overlay.setGeometry(x, y, overlay_width, overlay_height)
                else:
                    # Fallback to primary screen if cursor tracking fails
                    screen_geometry = QApplication.primaryScreen().availableGeometry()
                    x = screen_geometry.right() - overlay_width - 20
                    y = screen_geometry.bottom() - overlay_height - 50
                    self.overlay.setGeometry(x, y, overlay_width, overlay_height)
                
                # Only show if explicitly requested
                if show:
                    self.overlay.show()
                    self.overlay.raise_()
                    self.overlay.activateWindow()
                
                logger.debug(f"Overlay window initialized at ({x}, {y})")
                return True
            return False
        except Exception as e:
            logger.error(f"Error initializing overlay: {e}", exc_info=True)
            return False

    def show_overlay(self, show: bool = True):
        """Show or hide the overlay window.
        
        Args:
            show: If True, show the overlay. If False, hide it.
        """
        try:
            if show:
                # Try to initialize overlay if it doesn't exist or is invalid
                if not hasattr(self, 'overlay') or not self.overlay:
                    if not self.init_overlay():
                        logger.warning("Failed to initialize overlay")
                        return
                
                # Ensure the overlay is properly shown
                try:
                    if not self.overlay.isVisible():
                        self.overlay.show()
                    self.overlay.raise_()
                    self.overlay.activateWindow()
                    logger.debug("Overlay shown and activated")
                except Exception as e:
                    logger.error(f"Error showing overlay: {e}", exc_info=True)
                    # Attempt to recreate the overlay
                    self.overlay = None
                    if self.init_overlay():
                        self.overlay.show()
                        self.overlay.raise_()
                        self.overlay.activateWindow()
            
            elif hasattr(self, 'overlay') and self.overlay:
                try:
                    self.overlay.hide()
                except Exception as e:
                    logger.error(f"Error hiding overlay: {e}", exc_info=True)
                finally:
                    # Clean up the overlay when not in use
                    try:
                        self.overlay.deleteLater()
                    except Exception as e:
                        logger.error(f"Error cleaning up overlay: {e}", exc_info=True)
                    self.overlay = None
        except Exception as e:
            logger.error(f"Unexpected error in show_overlay: {e}", exc_info=True)
            
    def update_overlay_level(self, level: float):
        """Update the audio level in the overlay.
        
        Args:
            level: The audio level to display (0.0 to 1.0)
        """
        try:
            if not hasattr(self, 'overlay') or not self.overlay:
                if not self.init_overlay():
                    logger.debug("Overlay not available for level update")
                    return
                    
            if not self.overlay.isVisible():
                self.show_overlay(True)
                
            self.overlay.update_audio_level(level)
            
        except Exception as e:
            logger.error(f"Error updating overlay level: {e}", exc_info=True)
            # Attempt to recover by reinitializing the overlay
            try:
                self.overlay = None
                if self.init_overlay():
                    self.overlay.update_audio_level(level)
            except Exception as inner_e:
                logger.error(f"Failed to recover overlay after level update error: {inner_e}")
                
    def update_overlay_spectrum(self, spectrum: List[float]):
        """Update the audio spectrum in the overlay.
        
        Args:
            spectrum: List of frequency band levels to display
        """
        try:
            if not hasattr(self, 'overlay') or not self.overlay:
                if not self.init_overlay():
                    logger.debug("Overlay not available for spectrum update")
                    return
                    
            if not self.overlay.isVisible():
                self.show_overlay(True)
                
            self.overlay.update_spectrum(spectrum)
            
        except Exception as e:
            logger.error(f"Error updating overlay spectrum: {e}", exc_info=True)
            # Attempt to recover by reinitializing the overlay
            try:
                self.overlay = None
                if self.init_overlay():
                    self.overlay.update_spectrum(spectrum)
            except Exception as inner_e:
                logger.error(f"Failed to recover overlay after spectrum update error: {inner_e}")
    
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
        
        # Button layout for copy and type actions
        action_layout = QHBoxLayout()
        
        # Copy button
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.setEnabled(False)
        action_layout.addWidget(self.copy_button)
        
        # Type button
        self.type_button = QPushButton("Type Text")
        self.type_button.clicked.connect(self.type_text)
        self.type_button.setEnabled(False)
        action_layout.addWidget(self.type_button)
        
        button_layout.addLayout(action_layout)
        
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
        
        # Create tray menu
        menu = QMenu()
        menu.addAction("Show/Hide", self.toggle_window)
        menu.addAction("Start Recording", self.start_recording)
        menu.addAction("Stop Recording", self.stop_recording)
        menu.addAction("Settings", self.show_settings)
        menu.addAction("Quit", self.quit_app)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
        
        # Handle double click
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def tray_icon_activated(self, reason):
        """Handle system tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()
    
    def toggle_window(self):
        """Toggle window visibility."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
    
    def quit_app(self):
        """Quit the application."""
        self.close()
    
    def start_recording(self):
        """Start recording."""
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
        try:
            if hasattr(self, '_peak_timer') and self._peak_timer:
                self._peak_timer.stop()
            else:
                self._peak_timer = QTimer(self)
                self._peak_timer.timeout.connect(self.reset_peak)
                
            self._peak_level = level
            self._peak_timer.start(500)  # Restart the timer
            self.update()
        except Exception as e:
            logger.error(f"Error in update_audio_level: {e}", exc_info=True)
    

    
    def update_level_meter(self, level):
        """Update the audio level meter with a new level."""
        if hasattr(self, '_peak_timer') and self._peak_timer:
            self._peak_timer.stop()
            self._peak_timer.start(500)  # Restart the timer
        self._peak_level = level
        
        # Update the overlay if it exists
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.update_audio_level(level)
        self.update()
    
    def stop_recording(self):
        """Stop recording."""
        if self.recording_thread:
            self.recording_thread.stop()
            self.recording_thread.wait()
            self.recording_thread = None
    
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
        try:
            # Clean up the recording thread
            if self.recording_thread:
                if self.recording_thread.isRunning():
                    self.recording_thread.wait(1000)  # Wait up to 1 second
                self.recording_thread = None
                
            # Update UI
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
            self.transcription_thread.finished.connect(self.cleanup_transcription_thread)
            self.transcription_thread.start()
            
            # Update status if status_label exists
            if hasattr(self, 'status_label'):
                self.status_label.setText("Transcribing...")
                
        except Exception as e:
            logger.error(f"Error in on_recording_finished: {e}", exc_info=True)
            if hasattr(self, 'status_label'):
                self.status_label.setText("Error processing recording")
            QTimer.singleShot(2000, lambda: self.show_overlay(False))
    
    def cleanup_transcription_thread(self):
        """Clean up the transcription thread."""
        if self.transcription_thread:
            if self.transcription_thread.isRunning():
                self.transcription_thread.wait(1000)  # Wait up to 1 second
            self.transcription_thread = None
    
    def on_transcription_finished(self, text):
        """Handle transcription finished event."""
        self.transcription_display.setText(text)
        if hasattr(self, 'status_label'):
            self.status_label.setText("Transcription complete")
        self.copy_button.setEnabled(True)
        self.type_button.setEnabled(True)
        
        # Automatically type the transcribed text
        self.type_text()
        
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
            
    def type_text(self):
        """Type the transcription text into the active window."""
        text = self.transcription_display.text()
        if not text:
            return
            
        try:
            if hasattr(self, 'universal_typer') and self.universal_typer:
                self.universal_typer.type_text(text)
                if hasattr(self, 'status_label'):
                    self.status_label.setText("Text typed into active window")
            else:
                logger.error("UniversalTyping instance not available")
                if hasattr(self, 'status_label'):
                    self.status_label.setText("Error: Typing service not available")
        except Exception as e:
            error_msg = f"Failed to type text: {str(e)}"
            if hasattr(self, 'status_label'):
                self.status_label.setText(error_msg)
            logger.error(error_msg, exc_info=True)
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Stop any running threads
        if hasattr(self, 'recording_thread') and self.recording_thread is not None:
            if hasattr(self.recording_thread, 'isRunning') and self.recording_thread.isRunning():
                self.recording_thread.stop()
                self.recording_thread.wait()
        
        if hasattr(self, 'transcription_thread') and self.transcription_thread is not None:
            if hasattr(self.transcription_thread, 'isRunning') and self.transcription_thread.isRunning():
                self.transcription_thread.wait()
        
        # Clean up global hotkey
        if hasattr(self, '_hotkey_thread') and self._hotkey_thread is not None:
            self._stop_hotkey = True
            self._hotkey_thread.join()
            self._hotkey_thread = None
        
        # Hide to tray instead of closing
        event.ignore()
        self.hide()
        
        # Save window position and size if window is not minimized
        if not self.isMinimized():
            self.config.ui.window_width = self.width()
            self.config.ui.window_height = self.height()
            self.config.ui.window_x = self.x()
            self.config.ui.window_y = self.y()
        
        # Save config
        try:
            self.config.save()
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def event(self, event):
        """Handle custom events."""
        if event.type() == QEvent.Type.User:
            # Handle global hotkey event
            try:
                logger.debug("Processing hotkey event from global hotkey")
                # Use a singleShot timer to ensure we're in the main thread
                QTimer.singleShot(0, self.toggle_recording)
            except Exception as e:
                logger.error(f"Error in hotkey event handler: {e}", exc_info=True)
            return True
        return super().event(event)

    def show_settings(self):
        """Show the settings dialog."""
        # Store the dialog reference before showing it
        self.settings_dialog = SettingsDialog(self)
        
        # Show the dialog and wait for it to close
        result = self.settings_dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Get the default config path and save the configuration
            from nixwhisper.config import get_default_config_path
            config_path = get_default_config_path()
            self.config.save(config_path)
            
            # Re-initialize shortcuts with new configuration
            self.setup_shortcuts()
            
        # Clear the reference when done
        self.settings_dialog = None

class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NixWhisper Settings")
        self.setFixedSize(450, 400)
        
        # Store parent window reference for config access
        self.parent_window = parent
        
        layout = QVBoxLayout()
        
        # Hotkey configuration
        hotkey_group = QGroupBox("Global Hotkey")
        hotkey_layout = QVBoxLayout()
        
        # Main hotkey input
        hotkey_input_layout = QHBoxLayout()
        hotkey_label = QLabel("Shortcut:")
        self.hotkey_input = QLineEdit(self.parent_window.config.ui.hotkey)
        self.hotkey_input.setPlaceholderText("Click and press keys...")
        self.hotkey_input.setReadOnly(True)
        self.hotkey_input.installEventFilter(self)
        self.hotkey_status = QLabel()
        self.hotkey_status.setStyleSheet("color: gray;")
        hotkey_input_layout.addWidget(hotkey_label)
        hotkey_input_layout.addWidget(self.hotkey_input)
        hotkey_input_layout.addWidget(self.hotkey_status)
        hotkey_layout.addLayout(hotkey_input_layout)
        
        # Help text
        help_text = QLabel("Click the input field and press your desired key combination.\nThe hotkey will work globally even when the app is in background.")
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: gray; font-size: 10pt;")
        hotkey_layout.addWidget(help_text)
        
        hotkey_group.setLayout(hotkey_layout)
        layout.addWidget(hotkey_group)
        
        # Silence detection settings
        silence_layout = QVBoxLayout()
        
        # Enable/disable silence detection
        self.silence_enable_cb = QCheckBox("Enable silence detection")
        self.silence_enable_cb.setChecked(self.parent_window.config.ui.silence_detection)
        self.silence_enable_cb.stateChanged.connect(self.toggle_silence_detection)
        silence_layout.addWidget(self.silence_enable_cb)
        
        # Threshold slider
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Sensitivity:"))
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(1, 100)
        self.threshold_slider.setValue(int(self.parent_window.config.ui.silence_threshold * 1000))
        self.threshold_slider.valueChanged.connect(self.update_silence_threshold)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(QLabel(f"{self.parent_window.config.ui.silence_threshold:.3f}"))
        self.threshold_value = threshold_layout.itemAt(2).widget()
        silence_layout.addLayout(threshold_layout)
        
        # Duration spinbox
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Silence duration (s):"))
        self.duration_spinbox = QDoubleSpinBox()
        self.duration_spinbox.setRange(0.1, 10.0)
        self.duration_spinbox.setSingleStep(0.1)
        self.duration_spinbox.setValue(self.parent_window.config.ui.silence_duration)
        self.duration_spinbox.valueChanged.connect(self.update_silence_duration)
        duration_layout.addWidget(self.duration_spinbox)
        duration_layout.addWidget(QLabel("seconds"))
        silence_layout.addLayout(duration_layout)
        
        silence_group = QGroupBox("Silence Detection")
        silence_group.setLayout(silence_layout)
        layout.addWidget(silence_group)
        
        # Visual Connection settings
        visual_layout = QVBoxLayout()
        
        # Enable/disable visual connection
        self.visual_enable_cb = QCheckBox("Show cursor connection indicator")
        # Load from config if available, otherwise use default
        if hasattr(self.parent_window.config, 'overlay'):
            self.visual_enable_cb.setChecked(self.parent_window.config.overlay.cursor_connection_enabled)
        else:
            self.visual_enable_cb.setChecked(True)
        visual_layout.addWidget(self.visual_enable_cb)
        
        # Connection style selector
        style_layout = QHBoxLayout()
        style_layout.addWidget(QLabel("Style:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(['arrow', 'line', 'none'])
        if hasattr(self.parent_window.config, 'overlay'):
            current_style = self.parent_window.config.overlay.cursor_connection_style
            index = self.style_combo.findText(current_style)
            if index >= 0:
                self.style_combo.setCurrentIndex(index)
        style_layout.addWidget(self.style_combo)
        visual_layout.addLayout(style_layout)
        
        # Color picker (simplified as a text input for now)
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.color_input = QLineEdit()
        if hasattr(self.parent_window.config, 'overlay'):
            self.color_input.setText(self.parent_window.config.overlay.cursor_connection_color)
        else:
            self.color_input.setText("#64c8ff")
        self.color_input.setPlaceholderText("#RRGGBB or color name")
        color_layout.addWidget(self.color_input)
        visual_layout.addLayout(color_layout)
        
        # Animation toggle
        self.animation_cb = QCheckBox("Animate connection indicator")
        if hasattr(self.parent_window.config, 'overlay'):
            self.animation_cb.setChecked(self.parent_window.config.overlay.cursor_connection_animated)
        else:
            self.animation_cb.setChecked(True)
        visual_layout.addWidget(self.animation_cb)
        
        visual_group = QGroupBox("Visual Connection")
        visual_group.setLayout(visual_layout)
        layout.addWidget(visual_group)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def accept(self):
        """Override accept to save visual connection settings."""
        # Save visual connection settings to config
        if not hasattr(self.parent_window.config, 'overlay'):
            # If overlay config doesn't exist, create it
            from nixwhisper.config import OverlayConfig
            self.parent_window.config.overlay = OverlayConfig()
        
        # Update config with UI values
        self.parent_window.config.overlay.cursor_connection_enabled = self.visual_enable_cb.isChecked()
        self.parent_window.config.overlay.cursor_connection_style = self.style_combo.currentText()
        self.parent_window.config.overlay.cursor_connection_color = self.color_input.text()
        self.parent_window.config.overlay.cursor_connection_animated = self.animation_cb.isChecked()
        
        # Apply settings to overlay if it exists
        if hasattr(self.parent_window, 'overlay') and self.parent_window.overlay:
            self.parent_window.overlay.set_cursor_connection_enabled(self.visual_enable_cb.isChecked())
            self.parent_window.overlay.set_cursor_connection_style(self.style_combo.currentText())
            # Convert color string to QColor
            color_text = self.color_input.text()
            if color_text:
                try:
                    color = QColor(color_text)
                    if color.isValid():
                        self.parent_window.overlay.set_cursor_connection_color(color)
                except:
                    pass  # Keep current color if invalid
            self.parent_window.overlay.set_cursor_connection_animated(self.animation_cb.isChecked())
        
        # Update hotkey setting
        self.parent_window.config.ui.hotkey = self.hotkey_input.text()
        
        super().accept()
    
    def toggle_silence_detection(self, state):
        """Toggle silence detection on/off."""
        self.parent_window.config.ui.silence_detection = (state == Qt.CheckState.Checked.value)
        logger.debug(f"Silence detection {'enabled' if self.parent_window.config.ui.silence_detection else 'disabled'}")
    
    def update_silence_threshold(self, value):
        """Update the silence threshold."""
        self.config.ui.silence_threshold = value / 1000.0  # Convert from 1-100 to 0.001-0.1
        self.threshold_value.setText(f"{self.config.ui.silence_threshold:.3f}")
        logger.debug(f"Silence threshold updated to {self.config.ui.silence_threshold}")
    
    def update_silence_duration(self, value):
        """Update the silence duration."""
        self.config.ui.silence_duration = value
        self.duration_value.setText(f"{self.config.ui.silence_duration:.1f}")
        logger.debug(f"Silence duration updated to {self.config.ui.silence_duration}s")
        
    def eventFilter(self, obj, event) -> bool:
        """Handle hotkey input events."""
        if obj == self.hotkey_input:
            if event.type() == QEvent.Type.KeyPress:
                # Get the key sequence
                key = event.key()
                modifiers = event.modifiers()
                
                logger.debug(f"Hotkey input - key: {key}, modifiers: {modifiers}")
                
                # Skip modifier-only key events
                if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
                    return True
                
                # Build the key sequence
                key_seq = []
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    key_seq.append('Ctrl')
                if modifiers & Qt.KeyboardModifier.ShiftModifier:
                    key_seq.append('Shift')
                if modifiers & Qt.KeyboardModifier.AltModifier:
                    key_seq.append('Alt')
                if modifiers & Qt.KeyboardModifier.MetaModifier:
                    key_seq.append('Meta')
                
                # Add the main key
                key_text = QKeySequence(key).toString()
                if key_text:
                    key_seq.append(key_text)
                
                logger.debug(f"Key sequence: {key_seq}")
                
                # Build the final key sequence
                hotkey = '+'.join(key_seq)
                logger.debug(f"Final hotkey: {hotkey}")
                
                # Validate the hotkey
                if len(key_seq) < 2:
                    self.hotkey_status.setText('❌ Add at least one modifier (Ctrl, Alt, etc.)')
                    self.hotkey_status.setStyleSheet('color: red;')
                    return True
                
                # Update the input field and config
                self.hotkey_input.setText(hotkey)
                self.parent_window.config.ui.hotkey = hotkey
                self.hotkey_status.setText('✓ Valid shortcut')
                self.hotkey_status.setStyleSheet('color: green;')
                
                # Update parent's shortcuts
                logger.debug("Updating parent's shortcuts")
                self.parent_window.setup_shortcuts()
                
                return True
            
            elif event.type() == QEvent.Type.FocusIn:
                self.hotkey_status.setText('🔵 Press your desired key combination')
                self.hotkey_status.setStyleSheet('color: blue;')
                return False
            
            elif event.type() == QEvent.Type.FocusOut:
                if not self.hotkey_input.text():
                    self.hotkey_status.setText('')
                return False
        
        return super().eventFilter(obj, event)

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
