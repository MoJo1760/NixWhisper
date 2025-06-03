"""System-level text input handling for NixWhisper."""

import contextlib
import logging
import platform
import re
import subprocess
import time
from typing import Optional, Union, Any, Dict, Tuple, List, TYPE_CHECKING, Iterator

from pynput import keyboard


class TextInputError(Exception):
    """Raised when there's an error with text input."""
    pass


class TextInput:
    """Handles system-level text input simulation using pynput."""
    
    def __init__(self):
        """Initialize the text input handler."""
        self.controller = keyboard.Controller()
    
    def type_text(self, text: str) -> bool:
        """Type text at the current cursor position.
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            TextInputError: If typing fails
        """
        if not text:
            return True
            
        try:
            self.controller.type(text)
            return True
        except Exception as e:
            raise TextInputError(f"Failed to type text: {str(e)}")
    
    @contextlib.contextmanager
    def press_key_combo(self, *keys: Union[keyboard.Key, str]) -> Iterator[None]:
        """Context manager for pressing key combinations.
        
        Args:
            *keys: Keys to press simultaneously
            
        Yields:
            None
        """
        # Press all keys in order
        for key in keys:
            self.controller.press(key)
        
        try:
            yield
        finally:
            # Release all keys in reverse order
            for key in reversed(keys):
                self.controller.release(key)
    
    def _parse_hotkey(self, hotkey_str: str) -> List[Union[keyboard.Key, str]]:
        """Parse a hotkey string into a list of key objects.
        
        Args:
            hotkey_str: Hotkey string in format "<mod1>+<mod2>+key"
            
        Returns:
            List of key objects
            
        Raises:
            ValueError: If the hotkey string is invalid
        """
        if not hotkey_str:
            raise ValueError("Empty hotkey")
        
        # Check for invalid format (modifiers without angle brackets)
        if any(part in hotkey_str.lower() for part in ['ctrl+', 'alt+', 'shift+', 'cmd+', 'win+', 'super+']):
            if not all(('<' in part and '>' in part) for part in hotkey_str.split('+') if part.lower() in ['ctrl', 'alt', 'shift', 'cmd', 'win', 'super']):
                raise ValueError("Invalid hotkey format: modifiers must be in angle brackets (e.g., <ctrl>+a)")
        
        # Split the hotkey string into components, preserving case for regular characters
        parts = [p.strip() for p in hotkey_str.split('+')]
        
        keys = []
        for part in parts:
            if not part:
                continue
                
            # Handle special keys in angle brackets
            if part.startswith('<') and part.endswith('>'):
                key_name = part[1:-1].lower()  # Convert to lowercase for lookup
                
                # Check if it's a key code
                if key_name.isdigit():
                    keys.append(keyboard.KeyCode.from_vk(int(key_name)))
                    continue
                
                # Map common key names to Key enum
                key_map = {
                    'ctrl': keyboard.Key.ctrl,
                    'control': keyboard.Key.ctrl,
                    'shift': keyboard.Key.shift,
                    'alt': keyboard.Key.alt,
                    'alt_gr': keyboard.Key.alt_gr,
                    'alt_r': keyboard.Key.alt_r,
                    'cmd': keyboard.Key.cmd,
                    'command': keyboard.Key.cmd,
                    'super': keyboard.Key.cmd,
                    'win': keyboard.Key.cmd,
                    'menu': keyboard.Key.menu,
                    'space': keyboard.Key.space,
                    'enter': keyboard.Key.enter,
                    'return': keyboard.Key.enter,
                    'esc': keyboard.Key.esc,
                    'escape': keyboard.Key.esc,
                    'tab': keyboard.Key.tab,
                    'backspace': keyboard.Key.backspace,
                    'delete': keyboard.Key.delete,
                    'insert': keyboard.Key.insert,
                    'home': keyboard.Key.home,
                    'end': keyboard.Key.end,
                    'page_up': keyboard.Key.page_up,
                    'page_down': keyboard.Key.page_down,
                    'up': keyboard.Key.up,
                    'down': keyboard.Key.down,
                    'left': keyboard.Key.left,
                    'right': keyboard.Key.right,
                    'f1': keyboard.Key.f1,
                    'f2': keyboard.Key.f2,
                    'f3': keyboard.Key.f3,
                    'f4': keyboard.Key.f4,
                    'f5': keyboard.Key.f5,
                    'f6': keyboard.Key.f6,
                    'f7': keyboard.Key.f7,
                    'f8': keyboard.Key.f8,
                    'f9': keyboard.Key.f9,
                    'f10': keyboard.Key.f10,
                    'f11': keyboard.Key.f11,
                    'f12': keyboard.Key.f12,
                    'f13': keyboard.Key.f13,
                    'f14': keyboard.Key.f14,
                    'f15': keyboard.Key.f15,
                    'f16': keyboard.Key.f16,
                    'f17': keyboard.Key.f17,
                    'f18': keyboard.Key.f18,
                    'f19': keyboard.Key.f19,
                    'f20': keyboard.Key.f20,
                }
                
                if key_name in key_map:
                    keys.append(key_map[key_name])
                else:
                    # Try to get the key from the Key enum
                    try:
                        key_enum = getattr(keyboard.Key, key_name)
                        keys.append(key_enum)
                    except AttributeError:
                        raise ValueError(f"Unknown key: {key_name}")
            else:
                # Regular character - preserve case
                if len(part) == 1:
                    keys.append(part)
                else:
                    # For multi-character parts, only allow if it's a single character key name
                    # that was provided without angle brackets
                    if len(part) == 1:
                        keys.append(part)
                    else:
                        raise ValueError(f"Invalid key format: {part}. Single characters don't need angle brackets.")
        
        if not keys:
            raise ValueError("No valid keys in hotkey")
            
        return keys
    
    def _type_with_xdotool(self, text: str) -> bool:
        """Type text using xdotool.
        
        Args:
            text: Text to type
            
        Returns:
            bool: True if successful
        """
        from .utils.shell import type_text_xdotool
        return type_text_xdotool(text)
            
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
                    # Initialize GTK availability flag
                    GTK_AVAILABLE = False
                    Gdk = None

                    # Try to import GTK for Wayland support
                    try:
                        import gi
                        gi.require_version('Gtk', '3.0')
                        from gi.repository import Gdk
                        GTK_AVAILABLE = True
                    except (ImportError, ValueError):
                        GTK_AVAILABLE = False
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
