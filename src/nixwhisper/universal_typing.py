"""Universal typing integration for NixWhisper.

This module provides cross-platform text input simulation with multiple fallback methods.
"""

import logging
import subprocess
import time
from typing import Optional, List, Dict, Any, Union

# Try to import optional dependencies
try:
    from pynput import keyboard
    PYNPROMPT_AVAILABLE = True
except ImportError:
    PYNPROMPT_AVAILABLE = False

# Try to import Qt clipboard
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QClipboard
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

class UniversalTypingError(Exception):
    """Raised when there's an error with universal typing."""
    pass

class UniversalTyping:
    """Handles universal text input simulation with multiple fallback methods."""
    
    def __init__(self, preferred_methods: Optional[List[str]] = None):
        """Initialize the universal typing handler.
        
        Args:
            preferred_methods: List of preferred typing methods in order of preference.
                             Can include: 'pynput', 'xdotool', 'clipboard'
                             If None, uses a sensible default order.
        """
        self.logger = logging.getLogger(__name__)
        self.preferred_methods = preferred_methods or [
            'pynput',    # Direct input using pynput (works in most cases)
            'xdotool',   # Use xdotool if available (good for X11)
            'clipboard'  # Fallback to clipboard if all else fails
        ]
        
        # Initialize controllers
        self.pynput_controller = keyboard.Controller() if PYNPROMPT_AVAILABLE else None
        self.qt_clipboard = None
        
        if QT_AVAILABLE:
            try:
                # Get or create QApplication instance
                app = QApplication.instance()
                if app is None:
                    app = QApplication([])
                self.qt_clipboard = app.clipboard()
            except Exception as e:
                self.logger.warning(f"Failed to initialize Qt clipboard: {e}")
    
    def type_text(self, text: str, method: Optional[str] = None) -> bool:
        """Type text at the current cursor position.
        
        Args:
            text: Text to type
            method: Specific method to use. If None, tries all available methods.
            
        Returns:
            bool: True if typing was successful
            
        Raises:
            UniversalTypingError: If typing fails and no fallback is available
        """
        if not text:
            return True
            
        if method:
            return self._type_with_method(text, method)
            
        # Try each method in preferred order until one succeeds
        for method_name in self.preferred_methods:
            try:
                if self._type_with_method(text, method_name):
                    self.logger.debug(f"Successfully typed text using {method_name}")
                    return True
            except Exception as e:
                self.logger.debug(f"Typing with {method_name} failed: {e}")
                continue
                
        raise UniversalTypingError("All typing methods failed")
    
    def _type_with_method(self, text: str, method: str) -> bool:
        """Type text using a specific method.
        
        Args:
            text: Text to type
            method: Typing method to use
            
        Returns:
            bool: True if successful
            
        Raises:
            UniversalTypingError: If the method is unknown or fails
        """
        method = method.lower()
        
        if method == 'pynput':
            return self._type_with_pynput(text)
        elif method == 'xdotool':
            return self._type_with_xdotool(text)
        elif method == 'gtk':
            return self._type_with_gtk(text)
        elif method == 'clipboard':
            return self._type_with_clipboard(text)
        else:
            raise UniversalTypingError(f"Unknown typing method: {method}")
    
    def _type_with_pynput(self, text: str) -> bool:
        """Type text using pynput."""
        if not PYNPROMPT_AVAILABLE:
            raise UniversalTypingError("pynput not available")
            
        try:
            self.pynput_controller.type(text)
            return True
        except Exception as e:
            raise UniversalTypingError(f"pynput typing failed: {e}")
    
    def _is_xdotool_available(self) -> bool:
        """Check if xdotool is available on the system."""
        try:
            return subprocess.run(
                ["which", "xdotool"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ).returncode == 0
        except Exception:
            return False
    
    def _type_with_xdotool(self, text: str) -> bool:
        """Type text using xdotool."""
        from .utils.shell import type_text_xdotool
        return type_text_xdotool(text)
    
    def _type_with_clipboard(self, text: str) -> bool:
        """Type text using clipboard fallback."""
        if not QT_AVAILABLE or self.qt_clipboard is None:
            raise UniversalTypingError("Clipboard not available")
            
        try:
            # Backup current clipboard
            clipboard = self.qt_clipboard
            old_text = clipboard.text()
            
            # Set new text to clipboard
            clipboard.setText(text, QClipboard.Clipboard)
            
            # Give the clipboard a moment to update
            QApplication.processEvents()
            
            # Simulate paste (Ctrl+V) using pynput if available
            if PYNPROMPT_AVAILABLE:
                with self.pynput_controller.pressed(keyboard.Key.ctrl):
                    self.pynput_controller.press('v')
                    self.pynput_controller.release('v')
                
                # Wait for paste to complete
                time.sleep(0.1)
            else:
                # If pynput is not available, just log a warning
                self.logger.warning("Cannot simulate paste - pynput not available")
                # Wait a bit longer since we can't simulate the paste
                time.sleep(0.5)
            
            # Restore original clipboard content
            if old_text is not None:
                clipboard.setText(old_text, QClipboard.Clipboard)
                QApplication.processEvents()
                
            return True
            
        except Exception as e:
            # Try to restore clipboard even if paste failed
            if 'old_text' in locals() and old_text is not None:
                try:
                    clipboard.setText(old_text, QClipboard.Clipboard)
                    QApplication.processEvents()
                except Exception as restore_error:
                    self.logger.error(f"Failed to restore clipboard: {restore_error}")
                    
            raise UniversalTypingError(f"Clipboard typing failed: {e}")
    def _save_clipboard(self):
        """Save the current clipboard content."""
        if self.gtk_clipboard:
            self.clipboard_backup = self.gtk_clipboard.wait_for_text()
    
    def _set_clipboard(self, text: str):
        """Set clipboard content."""
        if self.gtk_clipboard:
            self.gtk_clipboard.set_text(text, -1)
            self.gtk_clipboard.store()
    
    def _restore_clipboard(self):
        """Restore the clipboard to its previous content."""
        if self.gtk_clipboard and self.clipboard_backup is not None:
            self.gtk_clipboard.set_text(self.clipboard_backup, -1)
            self.gtk_clipboard.store()
            self.clipboard_backup = None
