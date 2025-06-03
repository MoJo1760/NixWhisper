"""Universal typing implementation for cross-platform text input simulation."""

import logging
import platform
import subprocess
import time
from typing import List

# Try to import pynput
try:
    from pynput import keyboard, mouse
    PYNPROMPT_AVAILABLE = True
except ImportError:
    PYNPROMPT_AVAILABLE = False

# Try to import Qt clipboard
try:
    from PyQt5.QtWidgets import QApplication
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

# Try to import shell utility
try:
    from .utils.shell import type_text_xdotool
    SHELL_UTIL_AVAILABLE = True
except ImportError:
    SHELL_UTIL_AVAILABLE = False

# Platform detection
IS_LINUX = platform.system() == 'Linux'
IS_WINDOWS = platform.system() == 'Windows'
IS_MAC = platform.system() == 'Darwin'

class UniversalTypingError(Exception):
    """Raised when there's an error with universal typing.

    Attributes:
        message: Explanation of the error.
    """

class UniversalTyping:
    """A class to handle universal typing across different platforms and applications."""

    def __init__(self, logger=None):
        """Initialize the UniversalTyping class.

        Args:
            logger: Optional logger instance. If not provided, a default logger will be used.
        """
        self.logger = logger or logging.getLogger(__name__)
        # Input methods
        self.pynput_controller = None
        self.mouse_controller = None
        # Clipboard handling
        self.qt_clipboard = None
        self.clipboard_backup = None
        # Configuration
        self.preferred_methods = []
        self._init_pynput()
        self._init_qt_clipboard()
        self.preferred_methods = self._get_default_methods()

    def _get_default_methods(self) -> List[str]:
        """Get default typing methods based on platform."""
        if IS_LINUX:
            return ['pynput', 'xdotool', 'clipboard']
        if IS_WINDOWS or IS_MAC:
            return ['pynput', 'clipboard']
        return ['pynput', 'xdotool', 'clipboard']

    def _init_pynput(self) -> None:
        """Initialize pynput controller if available."""
        if PYNPROMPT_AVAILABLE and not self.pynput_controller:
            try:
                self.pynput_controller = keyboard.Controller()
                self.mouse_controller = mouse.Controller()
            except (RuntimeError, ImportError) as exc:
                self.logger.warning("Failed to initialize pynput: %s", str(exc))

    def _init_qt_clipboard(self) -> None:
        """Initialize Qt clipboard if available."""
        if QT_AVAILABLE and not self.qt_clipboard:
            try:
                app = QApplication.instance() or QApplication([])
                self.qt_clipboard = app.clipboard()
            except (RuntimeError, ImportError) as exc:
                self.logger.warning("Failed to initialize Qt clipboard: %s", str(exc))

    def _ensure_focus(self) -> bool:
        """Ensure the target window has focus before typing.

        Returns:
            bool: True if focus was successfully set, False otherwise
        """
        # Try with pynput first
        if PYNPROMPT_AVAILABLE and self.mouse_controller:
            try:
                # Get current mouse position
                current_pos = self.mouse_controller.position
                # Move mouse slightly to ensure we're in the right window
                self.mouse_controller.position = (current_pos[0] + 1, current_pos[1] + 1)
                # Click to ensure focus
                self.mouse_controller.click(mouse.Button.left, 1)
                # Restore mouse position
                self.mouse_controller.position = current_pos
                self.logger.debug("Successfully set focus using pynput")
                return True
            except (RuntimeError, AttributeError) as exc:
                self.logger.warning("Failed to ensure focus with pynput: %s", str(exc))

        # Try with xdotool as fallback on Linux
        if IS_LINUX and self._is_xdotool_available():
            try:
                subprocess.run(
                    ['xdotool', 'click', '1'],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=False
                )
                self.logger.debug("Successfully set focus using xdotool")
                return True
            except (subprocess.SubprocessError, OSError) as exc:
                self.logger.warning("Failed to ensure focus with xdotool: %s", str(exc))

        self.logger.warning("Could not ensure window focus with any method")
        return False

    def type_text(self, text: str, method: str = 'auto') -> bool:
        """Type the given text using the specified method.

        Args:
            text: Text to type
            method: Typing method ('auto', 'pynput', 'xdotool', 'clipboard')

        Returns:
            bool: True if typing was successful

        Raises:
            UniversalTypingError: If typing fails
        """
        if not text:
            return True

        # Log available methods for debugging
        available = self.get_available_methods()
        self.logger.debug("Available typing methods: %s", available)
        self.logger.debug("Preferred methods: %s", self.preferred_methods)

        method = method.lower()
        if method == 'auto':
            # Try each method in order of preference
            for m in self.preferred_methods:
                try:
                    self.logger.debug("Attempting to type with method: %s", m)
                    result = self._type_with_method(text, m)
                    self.logger.debug("Successfully typed text with method: %s", m)
                    return result
                except UniversalTypingError as exc:
                    self.logger.debug("Method %s failed: %s", m, str(exc))
                    continue

            # If all preferred methods failed, try any available method as last resort
            for m in available:
                if m not in self.preferred_methods:
                    try:
                        self.logger.debug("Trying fallback method: %s", m)
                        result = self._type_with_method(text, m)
                        self.logger.debug("Successfully typed text with fallback method: %s", m)
                        return result
                    except UniversalTypingError as exc:
                        self.logger.debug("Fallback method %s failed: %s", m, str(exc))
                        continue

            raise UniversalTypingError("All typing methods failed")
        return self._type_with_method(text, method)

    def get_available_methods(self) -> List[str]:
        """Get a list of available typing methods on this system.

        Returns:
            List[str]: List of available method names
        """
        available = []
        if PYNPROMPT_AVAILABLE and self.pynput_controller:
            available.append('pynput')
        if IS_LINUX and self._is_xdotool_available():
            available.append('xdotool')
        if QT_AVAILABLE and self.qt_clipboard:
            available.append('clipboard')
        return available

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

        # Always try to ensure focus first
        self._ensure_focus()

        # Add a small delay to ensure the window has focus
        time.sleep(0.2)

        if method == 'pynput':
            return self._type_with_pynput(text)
        if method == 'xdotool':
            return self._type_with_xdotool(text)
        if method == 'clipboard':
            return self._type_with_clipboard(text)

        raise UniversalTypingError(f"Unknown typing method: {method}")

    def _type_with_pynput(self, text: str) -> bool:
        """Type text using pynput.

        Args:
            text: Text to type

        Returns:
            bool: True if typing was successful

        Raises:
            UniversalTypingError: If typing fails
        """
        if not PYNPROMPT_AVAILABLE or not self.pynput_controller:
            raise UniversalTypingError("pynput not available")

        try:
            # Split text into chunks to avoid buffer issues
            chunk_size = 100
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size]
                self.pynput_controller.type(chunk)
                # Small delay between chunks to avoid overwhelming the system
                if i + chunk_size < len(text):
                    time.sleep(0.01)
            return True
        except (RuntimeError, AttributeError) as exc:
            raise UniversalTypingError(f"pynput typing failed: {str(exc)}") from exc

    def _is_xdotool_available(self) -> bool:
        """Check if xdotool is available on the system.

        Returns:
            bool: True if xdotool is available, False otherwise
        """
        try:
            return subprocess.run(
                ['which', 'xdotool'],
                check=False,
                capture_output=True,
                text=True,
                shell=False,
                timeout=5
            ).returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False

    def _type_with_xdotool(self, text: str) -> bool:
        """Type text using xdotool.

        Args:
            text: Text to type

        Returns:
            bool: True if typing was successful

        Raises:
            UniversalTypingError: If typing fails
        """
        # First try to use the shell utility if available
        if SHELL_UTIL_AVAILABLE and type_text_xdotool:
            try:
                return type_text_xdotool(text)
            except (ImportError, RuntimeError) as exc:
                self.logger.debug("Shell utility failed: %s", str(exc))

        # Fallback to direct xdotool command
        if not self._is_xdotool_available():
            raise UniversalTypingError("xdotool not found in PATH")

        try:
            # Get active window ID
            result = subprocess.run(
                ['xdotool', 'getactivewindow'],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
                shell=False
            )
            window_id = result.stdout.strip()

            if not window_id:
                raise UniversalTypingError("Could not get active window ID")

            # Type the text into the active window
            subprocess.run(
                ['xdotool', 'type', '--window', window_id, '--delay', '10', text],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                shell=False,
                stdin=subprocess.DEVNULL
            )
            return True

        except subprocess.TimeoutExpired as exc:
            raise UniversalTypingError("xdotool command timed out") from exc
        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr if exc.stderr else str(exc)
            raise UniversalTypingError(
                f"xdotool command failed: {error_msg}"
            ) from exc
        except (OSError, RuntimeError) as exc:
            raise UniversalTypingError(
                f"xdotool failed: {str(exc)}"
            ) from exc

    def _type_with_clipboard(self, text: str) -> bool:
        """Type text using clipboard fallback.

        This is the most reliable but also the most intrusive method as it
        temporarily overrides the system clipboard.

        Args:
            text: Text to type

        Returns:
            bool: True if typing was successful

        Raises:
            UniversalTypingError: If typing fails
        """
        try:
            # Backup current clipboard
            self._save_clipboard()

            # Set new clipboard content
            if not self.qt_clipboard:
                raise UniversalTypingError("Qt clipboard not available")

            self.logger.debug("Setting clipboard text")
            self.qt_clipboard.setText(text)

            # Small delay to ensure clipboard content is set
            time.sleep(0.1)

            # Simulate paste
            if PYNPROMPT_AVAILABLE and self.pynput_controller:
                self.logger.debug("Pasting with pynput")
                # Use Ctrl+V to paste
                with self.pynput_controller.pressed(keyboard.Key.ctrl):
                    self.pynput_controller.press('v')
                    self.pynput_controller.release('v')
                # Small delay to ensure paste completes
                time.sleep(0.1)
                return True

            # Fallback to xdotool on Linux if available
            if IS_LINUX and self._is_xdotool_available():
                try:
                    self.logger.debug("Pasting with xdotool")
                    subprocess.run(
                        ['xdotool', 'key', 'ctrl+v'],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        shell=False
                    )
                    # Small delay to ensure paste completes
                    time.sleep(0.1)
                    return True
                except subprocess.TimeoutExpired as exc:
                    raise UniversalTypingError("xdotool paste timed out") from exc
                except subprocess.CalledProcessError as exc:
                    error_msg = exc.stderr if exc.stderr else str(exc)
                    raise UniversalTypingError(
                        f"xdotool paste failed: {error_msg}"
                    ) from exc

            raise UniversalTypingError("No paste method available")

        except (RuntimeError, AttributeError) as exc:
            raise UniversalTypingError(
                f"Clipboard operation failed: {str(exc)}"
            ) from exc
        finally:
            # Restore clipboard
            self._restore_clipboard()

    def _save_clipboard(self) -> None:
        """Save the current clipboard content."""
        if not hasattr(self, 'clipboard_backup') and self.qt_clipboard:
            try:
                self.clipboard_backup = self.qt_clipboard.text()
            except (RuntimeError, AttributeError) as exc:
                self.logger.warning("Failed to save clipboard: %s", str(exc))

    def _restore_clipboard(self) -> None:
        """Restore the clipboard to its previous state."""
        if self.clipboard_backup is None:
            return

        try:
            if self.qt_clipboard:
                self.qt_clipboard.setText(self.clipboard_backup)
            self.clipboard_backup = None
        except (RuntimeError, AttributeError) as exc:
            self.logger.warning("Failed to restore clipboard: %s", str(exc))

    def _clear_clipboard_backup(self) -> None:
        """Clear the clipboard backup."""
        if hasattr(self, 'clipboard_backup'):
            try:
                del self.clipboard_backup
            except (AttributeError, RuntimeError) as exc:
                self.logger.warning("Failed to clear clipboard backup: %s", str(exc))
