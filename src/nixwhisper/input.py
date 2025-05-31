"""System-level text input handling for NixWhisper."""

import logging
import platform
import subprocess
import time
from typing import Optional, Union, Any, Dict, Tuple, TYPE_CHECKING

# Make GTK imports optional
GTK_AVAILABLE = False
Gdk: Any = None
Gtk: Any = None

try:
    import gi
    gi.require_version('Gdk', '3.0')
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gdk, Gtk  # type: ignore
    GTK_AVAILABLE = True
except (ImportError, ValueError) as e:
    logging.warning(
        "GTK bindings not available. Some features may be limited. "
        f"Error: {str(e)}"
    )
    # Create dummy classes for type checking
    if TYPE_CHECKING:
        from gi.repository import Gdk, Gtk  # type: ignore
    else:
        class DummyGtk:
            """Dummy Gtk class when GTK is not available."""
            Selection = type('Selection', (), {'CLIPBOARD': 'clipboard'})
            
        class DummyGdk:
            """Dummy Gdk class when GTK is not available."""
            SELECTION_CLIPBOARD = 69
            
        Gtk = DummyGtk()
        Gdk = DummyGdk()


class TextInputError(Exception):
    """Raised when there's an error with text input."""
    pass


class TextInput:
    """Handles system-level text input simulation."""
    
    def __init__(self):
        """Initialize the text input handler."""
        self.clipboard_backup = None
        self._init_clipboard()
    
    def _init_clipboard(self):
        """Initialize clipboard handling."""
        if GTK_AVAILABLE:
            self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        else:
            self.clipboard = None
    
    def type_text(self, text: str) -> bool:
        """Type text at the current cursor position.
        
        This method attempts to use the most reliable method available on the current
        system to simulate keyboard input.
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Try xdotool first (Linux)
        if self._is_xdotool_available():
            return self._type_with_xdotool(text)
            
        # Try GTK next
        if GTK_AVAILABLE:
            return self._type_with_gtk(text)
            
        # Fall back to clipboard method
        return self._type_with_clipboard(text)
    
    def _is_xdotool_available(self) -> bool:
        """Check if xdotool is available.
        
        Returns:
            bool: True if xdotool is available
        """
        try:
            subprocess.run(
                ["which", "xdotool"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _type_with_xdotool(self, text: str) -> bool:
        """Type text using xdotool.
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful
        """
        try:
            # Escape special characters for shell
            import shlex
            escaped_text = shlex.quote(text)
            
            # Type the text
            subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--", escaped_text],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return True
            
        except subprocess.SubprocessError as e:
            logging.warning(f"xdotool failed: {e}")
            return False
    
    def _type_with_gtk(self, text: str) -> bool:
        """Type text using GTK.
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful
        """
        if not GTK_AVAILABLE:
            return False
            
        try:
            # Get the current window and display
            display = Gdk.Display.get_default()
            if not display:
                return False
                
            seat = display.get_default_seat()
            device = seat.get_pointer()
            if not device:
                return False
                
            # Get the focused window
            window = display.get_focus_window()
            if not window:
                return False
                
            # Focus the window (raises the window)
            window.focus(Gdk.CURRENT_TIME)
            
            # Type each character with a small delay
            for char in text:
                # Simulate key press and release for each character
                # This is a simplified version and may not work for all characters
                keyval = Gdk.unicode_to_keyval(ord(char))
                keymap = Gdk.Keymap.get_for_display(display)
                entries = keymap.get_entries_for_keyval(keyval)
                
                if entries and entries[0].keycode:
                    keycode = entries[0].keycode
                    
                    # Press
                    event = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
                    event.window = window
                    event.time = Gdk.CURRENT_TIME
                    event.hardware_keycode = keycode
                    event.keyval = keyval
                    event.state = 0
                    event.send_event = True
                    
                    window.emit("key-press-event", event)
                    
                    # Release
                    event = Gdk.Event.new(Gdk.EventType.KEY_RELEASE)
                    event.window = window
                    event.time = Gdk.CURRENT_TIME
                    event.hardware_keycode = keycode
                    event.keyval = keyval
                    event.state = 0
                    event.send_event = True
                    
                    window.emit("key-release-event", event)
                    
                    # Small delay between keypresses
                    time.sleep(0.01)
            
            return True
            
        except Exception as e:
            logging.warning(f"GTK typing failed: {e}")
            return False
    
    def _type_with_clipboard(self, text: str) -> bool:
        """Type text using clipboard (fallback method).
        
        This method uses Ctrl+V to paste text from clipboard.
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful
        """
        try:
            # Save current clipboard content
            self._save_clipboard()
            
            # Set clipboard to our text
            self._set_clipboard(text)
            
            # Simulate Ctrl+V
            if self._is_xdotool_available():
                subprocess.run(
                    ["xdotool", "key", "--clearmodifiers", "Control_L+v"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Fall back to pyautogui if available
                try:
                    import pyautogui
                    pyautogui.hotkey('ctrl', 'v')
                except ImportError:
                    logging.warning("No text input method available")
                    return False
            
            # Small delay to ensure paste completes
            time.sleep(0.1)
            
            # Restore clipboard
            self._restore_clipboard()
            
            return True
            
        except Exception as e:
            logging.warning(f"Clipboard typing failed: {e}")
            # Try to restore clipboard even if paste failed
            self._restore_clipboard()
            return False
    
    def _save_clipboard(self):
        """Save the current clipboard content."""
        if self.clipboard:
            self.clipboard_backup = self.clipboard.wait_for_text()
    
    def _set_clipboard(self, text: str):
        """Set clipboard content.
        
        Args:
            text: Text to set in clipboard
        """
        if self.clipboard:
            self.clipboard.set_text(text, -1)
            self.clipboard.store()
    
    def _restore_clipboard(self):
        """Restore the clipboard to its previous content."""
        if self.clipboard and self.clipboard_backup is not None:
            self.clipboard.set_text(self.clipboard_backup, -1)
            self.clipboard.store()
            self.clipboard_backup = None
