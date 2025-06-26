"""
X11 cursor position tracking for NixWhisper.

This module provides functions to track the cursor position in X11 environments.
"""

import time
import threading
from typing import Optional, Tuple, Callable, Union, List
from dataclasses import dataclass
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import QRect
import sys

# Set up logging
logger = logging.getLogger(__name__)

# Try to import X11 libraries
try:
    import Xlib.display
    import Xlib.X
    import Xlib.ext.xtest
    X11_AVAILABLE = True
except ImportError:
    X11_AVAILABLE = False

@dataclass
class CursorPosition:
    """Represents a cursor position with timestamp and screen information."""
    x: int
    y: int
    screen_number: int = 0
    screen_x: int = 0
    screen_y: int = 0
    screen_width: int = 0
    screen_height: int = 0
    timestamp: float = 0.0

@dataclass
class WindowInfo:
    """Represents information about the active window."""
    window_id: int
    window_name: str
    window_class: str
    timestamp: float

class X11CursorTracker:
    """Tracks cursor position using X11."""
    
    def __init__(self):
        """Initialize the X11 cursor tracker."""
        self.display = None
        self.screen = None
        self.root = None
        self._polling_active = False
        self._polling_thread = None
        self._polling_interval = 0.1  # 100ms default
        self._last_position = None
        self._position_callbacks = []
        self._lock = threading.Lock()
        
        # Debouncing settings
        self._debounce_threshold = 5  # pixels - minimum movement to trigger callback
        self._debounce_time = 0.05  # 50ms - minimum time between callbacks
        self._last_callback_time = 0.0
        
        # Window focus tracking
        self._track_window_focus = False
        self._last_window_info = None
        self._window_callbacks = []
        
        if X11_AVAILABLE:
            try:
                self.display = Xlib.display.Display()
                self.screen = self.display.screen()
                self.root = self.screen.root
            except Exception as e:
                print(f"Warning: Failed to initialize X11 display: {e}")
                self.display = None
                self.screen = None
                self.root = None
    
    def get_cursor_position(self) -> Optional[CursorPosition]:
        """Get the current cursor position with screen information."""
        try:
            # Ensure QApplication is initialized
            app = QApplication.instance()
            if app is None:
                # Create a hidden QApplication if one doesn't exist
                import sys
                app = QApplication(sys.argv)
            
            # Get cursor position using QCursor
            from PyQt6.QtGui import QCursor
            cursor_pos = QCursor.pos()
            x, y = cursor_pos.x(), cursor_pos.y()
            
            # Get screen information
            screens = QApplication.screens()
            if not screens:
                logger.warning("No screens found")
                return None
                
            # Find which screen the cursor is on
            for i, screen in enumerate(screens):
                screen_geom = screen.geometry()
                # Use x,y coordinates directly for the contains check
                # Use Qt's contains method which handles the boundaries correctly
                if screen_geom.contains(x, y):
                    # Calculate position relative to screen
                    rel_x = x - screen_geom.x()
                    rel_y = y - screen_geom.y()
                    
                    return CursorPosition(
                        x=rel_x,
                        y=rel_y,
                        screen_number=i,
                        screen_x=screen_geom.x(),
                        screen_y=screen_geom.y(),
                        screen_width=screen_geom.width(),
                        screen_height=screen_geom.height(),
                        timestamp=time.time()
                    )
            
            # If we get here, cursor is not on any screen
            logger.warning(f"Cursor position ({x}, {y}) not on any known screen")
            
            # Fall back to primary screen if cursor is not found on any screen
            primary_geom = QApplication.primaryScreen().geometry()
            return CursorPosition(
                x=x - primary_geom.x(),
                y=y - primary_geom.y(),
                screen_number=0,
                screen_x=primary_geom.x(),
                screen_y=primary_geom.y(),
                screen_width=primary_geom.width(),
                screen_height=primary_geom.height(),
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Error getting cursor position: {e}", exc_info=True)
            return None
    
    def move_cursor(self, x: int, y: int) -> bool:
        """Move the cursor to the specified position.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful, False otherwise.
        """
        if not X11_AVAILABLE or not self.root:
            return False
        
        try:
            self.root.warp_pointer(x, y)
            self.display.sync()
            return True
        except Exception as e:
            print(f"Warning: Failed to move cursor: {e}")
            return False
    
    def simulate_click(self, button: int = 1) -> bool:
        """Simulate a mouse click.
        
        Args:
            button: Mouse button number (1=left, 2=middle, 3=right)
            
        Returns:
            True if successful, False otherwise.
        """
        if not X11_AVAILABLE or not self.display:
            return False
        
        try:
            # Press button
            Xlib.ext.xtest.fake_input(self.display, Xlib.X.ButtonPress, button)
            self.display.sync()
            
            # Release button
            Xlib.ext.xtest.fake_input(self.display, Xlib.X.ButtonRelease, button)
            self.display.sync()
            
            return True
        except Exception as e:
            print(f"Warning: Failed to simulate click: {e}")
            return False
    
    def get_active_window_info(self) -> Optional[WindowInfo]:
        """Get information about the currently active window.
        
        Returns:
            WindowInfo object or None if unavailable.
        """
        if not X11_AVAILABLE or not self.display or not self.root:
            return None
        
        try:
            # Get the active window
            active_window_atom = self.display.intern_atom('_NET_ACTIVE_WINDOW')
            active_window_prop = self.root.get_full_property(active_window_atom, Xlib.X.AnyPropertyType)
            
            if not active_window_prop or not active_window_prop.value:
                return None
            
            window_id = active_window_prop.value[0]
            if window_id == 0:
                return None
            
            # Get window object
            window = self.display.create_resource_object('window', window_id)
            
            # Get window name
            window_name = ""
            try:
                name_prop = window.get_full_property(self.display.intern_atom('_NET_WM_NAME'), Xlib.X.AnyPropertyType)
                if name_prop and name_prop.value:
                    window_name = name_prop.value.decode('utf-8', errors='ignore')
                else:
                    # Fallback to WM_NAME
                    name_prop = window.get_full_property(Xlib.X.XA_WM_NAME, Xlib.X.AnyPropertyType)
                    if name_prop and name_prop.value:
                        window_name = name_prop.value.decode('utf-8', errors='ignore')
            except Exception:
                pass
            
            # Get window class
            window_class = ""
            try:
                class_prop = window.get_full_property(Xlib.X.XA_WM_CLASS, Xlib.X.AnyPropertyType)
                if class_prop and class_prop.value:
                    # WM_CLASS contains instance and class separated by null bytes
                    class_data = class_prop.value.decode('utf-8', errors='ignore')
                    class_parts = class_data.split('\x00')
                    if len(class_parts) >= 2:
                        window_class = class_parts[1]  # Use the class name
                    elif len(class_parts) >= 1:
                        window_class = class_parts[0]  # Use the instance name
            except Exception:
                pass
            
            return WindowInfo(
                window_id=window_id,
                window_name=window_name,
                window_class=window_class,
                timestamp=time.time()
            )
            
        except Exception as e:
            print(f"Warning: Failed to get active window info: {e}")
            return None
    
    def enable_window_focus_tracking(self) -> bool:
        """Enable tracking of window focus changes.
        
        Returns:
            True if tracking was enabled, False otherwise.
        """
        if not X11_AVAILABLE:
            return False
        
        self._track_window_focus = True
        return True
    
    def disable_window_focus_tracking(self) -> None:
        """Disable tracking of window focus changes."""
        self._track_window_focus = False
    
    def add_window_callback(self, callback: Callable[[WindowInfo], None]) -> None:
        """Add a callback to be called when active window changes.
        
        Args:
            callback: Function to call with new window information
        """
        with self._lock:
            if callback not in self._window_callbacks:
                self._window_callbacks.append(callback)
    
    def remove_window_callback(self, callback: Callable[[WindowInfo], None]) -> None:
        """Remove a window change callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        with self._lock:
            if callback in self._window_callbacks:
                self._window_callbacks.remove(callback)
    
    def get_last_window_info(self) -> Optional[WindowInfo]:
        """Get the last known active window information.
        
        Returns:
            Last window info or None if not available.
        """
        return self._last_window_info
    
    def start_polling(self, interval: float = 0.1) -> bool:
        """Start polling for cursor position changes.
        
        Args:
            interval: Polling interval in seconds (default: 0.1 = 100ms)
            
        Returns:
            True if polling started successfully, False otherwise.
        """
        if not X11_AVAILABLE or self._polling_active:
            return False
        
        self._polling_interval = max(0.01, interval)  # Minimum 10ms
        self._polling_active = True
        
        # Start polling thread
        self._polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._polling_thread.start()
        
        return True
    
    def stop_polling(self) -> None:
        """Stop polling for cursor position changes."""
        self._polling_active = False
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=1.0)
        self._polling_thread = None
    
    def add_position_callback(self, callback: Callable[[CursorPosition], None]) -> None:
        """Add a callback to be called when cursor position changes.
        
        Args:
            callback: Function to call with new cursor position
        """
        with self._lock:
            if callback not in self._position_callbacks:
                self._position_callbacks.append(callback)
    
    def remove_position_callback(self, callback: Callable[[CursorPosition], None]) -> None:
        """Remove a position change callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        with self._lock:
            if callback in self._position_callbacks:
                self._position_callbacks.remove(callback)
    
    def register_callback(self, callback: Callable[[CursorPosition], None]) -> None:
        """Register a callback for cursor position changes (alias for add_position_callback).
        
        Args:
            callback: Function to call with new cursor position
        """
        self.add_position_callback(callback)
    
    def unregister_callback(self, callback: Callable[[CursorPosition], None]) -> None:
        """Unregister a callback for cursor position changes (alias for remove_position_callback).
        
        Args:
            callback: Function to remove from callbacks
        """
        self.remove_position_callback(callback)
    
    def _polling_loop(self) -> None:
        """Main polling loop that runs in a separate thread."""
        logger.debug("Starting cursor polling thread")
        poll_count = 0
        
        while self._polling_active:
            try:
                poll_count += 1
                
                # Log thread status periodically
                if poll_count % 10 == 0:  # Every 10 polls (1 second at 100ms interval)
                    logger.debug(
                        f"Cursor polling active - callbacks: {len(self._position_callbacks)}, "
                        f"last position: {self._last_position}"
                    )
                
                # Get current position
                cursor_pos = self.get_cursor_position()
                if cursor_pos is None:
                    logger.debug("Failed to get cursor position, will retry...")
                    time.sleep(self._polling_interval)
                    continue
                
                current_time = time.time()
                cursor_pos.timestamp = current_time  # Update timestamp
                
                # Check if position changed
                position_changed = False
                if self._last_position is None:
                    position_changed = True
                    logger.debug("Initial cursor position detected")
                else:
                    dx = abs(self._last_position.x - cursor_pos.x)
                    dy = abs(self._last_position.y - cursor_pos.y)
                    if dx > self._debounce_threshold or dy > self._debounce_threshold:
                        position_changed = True
                        logger.debug(f"Cursor moved: ({dx:.1f}, {dy:.1f}) pixels")
                
                if position_changed:
                    self._last_position = cursor_pos
                    time_since_last_callback = current_time - self._last_callback_time
                    
                    # Check debounce time
                    if time_since_last_callback >= self._debounce_time:
                        self._last_callback_time = current_time
                        
                        # Make a thread-safe copy of callbacks
                        with self._lock:
                            callbacks = list(self._position_callbacks)
                        
                        if callbacks:
                            logger.debug(
                                f"Triggering {len(callbacks)} callbacks "
                                f"(debounce: {self._debounce_time:.3f}s, "
                                f"last callback: {time_since_last_callback:.3f}s ago)"
                            )
                            
                            # Call each callback
                            for i, callback in enumerate(callbacks):
                                try:
                                    callback_name = getattr(callback, "__name__", f"callback_{i}")
                                    logger.debug(f"  - Calling {callback_name}")
                                    callback(cursor_pos)
                                except Exception as e:
                                    logger.error(
                                        f"Error in cursor position callback {callback_name}: {e}",
                                        exc_info=True
                                    )
                    else:
                        logger.debug(
                            f"Skipping callback due to debounce time "
                            f"({time_since_last_callback:.3f}s < {self._debounce_time:.3f}s)"
                        )
                
                # Check for window focus changes if enabled
                if self._track_window_focus and (poll_count % 5 == 0):  # Check every 500ms
                    try:
                        window_info = self.get_active_window_info()
                        if window_info and (
                            self._last_window_info is None or 
                            self._last_window_info.window_id != window_info.window_id
                        ):
                            self._last_window_info = window_info
                            with self._lock:
                                callbacks = list(self._window_callbacks)
                            
                            for callback in callbacks:
                                try:
                                    callback(window_info)
                                except Exception as e:
                                    logger.error(
                                        f"Error in window focus callback: {e}",
                                        exc_info=True
                                    )
                    except Exception as e:
                        logger.error(f"Error checking window focus: {e}", exc_info=True)
                
                time.sleep(self._polling_interval)
                
            except Exception as e:
                logger.error(f"Error in cursor polling loop: {e}", exc_info=True)
                time.sleep(self._polling_interval)
        
        logger.debug("Cursor polling thread stopped")
        
    def get_last_position(self) -> Optional[CursorPosition]:
        """Get the last known cursor position.
        
        Returns:
            Last cursor position or None if not available.
        """
        return self._last_position
    
    def set_polling_interval(self, interval: float) -> None:
        """Set the polling interval.
        
        Args:
            interval: New polling interval in seconds (minimum: 0.01)
        """
        self._polling_interval = max(0.01, interval)
    
    def set_debounce_threshold(self, threshold: int) -> None:
        """Set the debounce threshold for cursor movement.
        
        Args:
            threshold: Minimum pixel movement to trigger callback (minimum: 1)
        """
        self._debounce_threshold = max(1, threshold)
    
    def set_debounce_time(self, debounce_time: float) -> None:
        """Set the minimum time between callbacks.
        
        Args:
            debounce_time: Minimum time in seconds between callbacks (minimum: 0.01)
        """
        self._debounce_time = max(0.01, debounce_time)
    
    def get_debounce_settings(self) -> dict:
        """Get current debouncing settings.
        
        Returns:
            Dictionary with debouncing configuration
        """
        return {
            'threshold': self._debounce_threshold,
            'time': self._debounce_time,
            'polling_interval': self._polling_interval
        }
    
    def is_polling_active(self) -> bool:
        """Check if cursor position polling is active.
        
        Returns:
            True if polling is active, False otherwise.
        """
        return self._polling_active
    
    def is_polling(self) -> bool:
        """Check if cursor position polling is active (alias for is_polling_active).
        
        Returns:
            True if polling is active, False otherwise.
        """
        return self.is_polling_active()
    
    @property
    def polling_interval(self) -> float:
        """Get the current polling interval in milliseconds.
        
        Returns:
            Polling interval in milliseconds
        """
        return self._polling_interval * 1000  # Convert seconds to milliseconds
    
    @property
    def callbacks(self) -> List[Callable[[CursorPosition], None]]:
        """Get a copy of the current position callbacks list.
        
        Returns:
            List of registered position callbacks
        """
        with self._lock:
            return list(self._position_callbacks)
    
    def cleanup(self) -> None:
        """Clean up X11 resources."""
        # Stop polling first
        self.stop_polling()
        
        if self.display:
            try:
                self.display.close()
            except Exception as e:
                print(f"Warning: Error closing X11 display: {e}")
        
        self.display = None
        self.screen = None
        self.root = None
        self._last_position = None
        
        with self._lock:
            self._position_callbacks.clear()

# Global cursor tracker instance
cursor_tracker = X11CursorTracker()

# Convenience functions
def get_cursor_position(include_screen_info: bool = False) -> Union[Optional[Tuple[int, int]], Optional[CursorPosition]]:
    """Get the current cursor position.
    
    Args:
        include_screen_info: If True, returns a CursorPosition object with screen information.
                           If False, returns a tuple of (x, y) coordinates for backward compatibility.
                           
    Returns:
        If include_screen_info is True, returns a CursorPosition object or None if unavailable.
        If include_screen_info is False, returns a tuple of (x, y) coordinates or None if unavailable.
    """
    pos = cursor_tracker.get_cursor_position()
    if pos is None:
        return None
    return pos if include_screen_info else (pos.x, pos.y)

def move_cursor(x: int, y: int) -> bool:
    """Move the cursor to the specified position.
    
    Args:
        x: X coordinate
        y: Y coordinate
        
    Returns:
        True if successful, False otherwise.
    """
    return cursor_tracker.move_cursor(x, y)

def simulate_click(button: int = 1) -> bool:
    """Simulate a mouse click.
    
    Args:
        button: Mouse button number (1=left, 2=middle, 3=right)
        
    Returns:
        True if successful, False otherwise.
    """
    return cursor_tracker.simulate_click(button)

def start_cursor_polling(interval: float = 0.1) -> bool:
    """Start polling for cursor position changes.
    
    Args:
        interval: Polling interval in seconds (default: 0.1 = 100ms)
        
    Returns:
        True if polling started successfully, False otherwise.
    """
    return cursor_tracker.start_polling(interval)

def stop_cursor_polling() -> None:
    """Stop polling for cursor position changes."""
    cursor_tracker.stop_polling()

def add_cursor_callback(callback: Callable[[CursorPosition], None]) -> None:
    """Add a callback to be called when cursor position changes.
    
    Args:
        callback: Function to call with new cursor position
    """
    cursor_tracker.add_position_callback(callback)

def remove_cursor_callback(callback: Callable[[CursorPosition], None]) -> None:
    """Remove a position change callback.
    
    Args:
        callback: Function to remove from callbacks
    """
    cursor_tracker.remove_position_callback(callback)

def set_cursor_debounce_threshold(threshold: int) -> None:
    """Set the debounce threshold for cursor movement.
    
    Args:
        threshold: Minimum pixel movement to trigger callback (minimum: 1)
    """
    cursor_tracker.set_debounce_threshold(threshold)

def set_cursor_debounce_time(debounce_time: float) -> None:
    """Set the minimum time between callbacks.
    
    Args:
        debounce_time: Minimum time in seconds between callbacks (minimum: 0.01)
    """
    cursor_tracker.set_debounce_time(debounce_time)

def get_cursor_debounce_settings() -> dict:
    """Get current debouncing settings.
    
    Returns:
        Dictionary with debouncing configuration
    """
    return cursor_tracker.get_debounce_settings()

def get_active_window_info() -> Optional[WindowInfo]:
    """Get information about the currently active window.
    
    Returns:
        WindowInfo object or None if unavailable.
    """
    return cursor_tracker.get_active_window_info()

def enable_window_focus_tracking() -> bool:
    """Enable tracking of window focus changes.
    
    Returns:
        True if tracking was enabled, False otherwise.
    """
    return cursor_tracker.enable_window_focus_tracking()

def disable_window_focus_tracking() -> None:
    """Disable tracking of window focus changes."""
    cursor_tracker.disable_window_focus_tracking()

def add_window_callback(callback: Callable[[WindowInfo], None]) -> None:
    """Add a callback to be called when active window changes.
    
    Args:
        callback: Function to call with new window information
    """
    cursor_tracker.add_window_callback(callback)

def remove_window_callback(callback: Callable[[WindowInfo], None]) -> None:
    """Remove a window change callback.
    
    Args:
        callback: Function to remove from callbacks
    """
    cursor_tracker.remove_window_callback(callback)

def get_last_window_info() -> Optional[WindowInfo]:
    """Get the last known active window information.
    
    Returns:
        Last window info or None if not available.
    """
    return cursor_tracker.get_last_window_info()

def get_cursor_tracker() -> X11CursorTracker:
    """Get the global cursor tracker instance.
    
    Returns:
        The global X11CursorTracker instance
    """
    return cursor_tracker

def cleanup() -> None:
    """Clean up X11 resources."""
    cursor_tracker.cleanup()
