"""Unit tests for the UniversalTyping class."""

import unittest
from unittest.mock import patch, MagicMock, ANY, PropertyMock, mock_open
import sys
import os
import importlib

# Import the UniversalTyping class and its constants
from nixwhisper.universal_typing import UniversalTyping, UniversalTypingError, PYNPROMPT_AVAILABLE, QT_AVAILABLE

class TestUniversalTyping(unittest.TestCase):
    """Test cases for the UniversalTyping class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Save the original modules
        self.original_modules = {}
        for module_name in ['pynput', 'PyQt5', 'PyQt5.QtWidgets', 'PyQt5.QtGui']:
            self.original_modules[module_name] = sys.modules.get(module_name)
        
        # Create patches for all external dependencies
        self.patches = [
            # Mock the pynput.keyboard module
            patch('pynput.keyboard', MagicMock()),
            # Mock Qt modules
            patch.dict('sys.modules', {
                'PyQt5': MagicMock(),
                'PyQt5.QtWidgets': MagicMock(),
                'PyQt5.QtGui': MagicMock()
            }),
            # Mock subprocess and shutil at the global level
            patch('subprocess.run', return_value=MagicMock(returncode=0)),
            patch('shutil.which', return_value="/usr/bin/xdotool"),
            # Mock the module-level flags
            patch('nixwhisper.universal_typing.PYNPROMPT_AVAILABLE', True),
            patch('nixwhisper.universal_typing.QT_AVAILABLE', True)
        ]
        
        # Start all patches
        for p in self.patches:
            p.start()
            
        # Create a UniversalTyping instance for testing
        self.typer = UniversalTyping()
        
    def tearDown(self):
        """Clean up after tests."""
        # Stop all patches
        for p in reversed(self.patches):
            p.stop()
            
        # Restore original modules
        for module_name, module in self.original_modules.items():
            if module is None:
                if module_name in sys.modules:
                    del sys.modules[module_name]
            else:
                sys.modules[module_name] = module
                
        # Remove any remaining references to the mocked modules
        modules_to_remove = [
            'nixwhisper.universal_typing',
            'pynput',
            'pynput.keyboard',
            'PyQt5',
            'PyQt5.QtWidgets',
            'PyQt5.QtGui'
        ]
        
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

    @patch('nixwhisper.universal_typing.PYNPROMPT_AVAILABLE', False)
    def test_type_text_pynput_unavailable(self):
        """Test typing when pynput is not available."""
        # Create a new instance - it should pick up the patched PYNPROMPT_AVAILABLE
        typer = UniversalTyping()
        with self.assertRaises(UniversalTypingError) as context:
            typer._type_with_pynput("test")
        self.assertEqual(str(context.exception), "pynput not available")

    @patch('subprocess.run')
    def test_type_text_xdotool_not_found(self, mock_run):
        """Test typing when xdotool is not installed."""
        # Mock subprocess.run to simulate xdotool not found
        mock_run.return_value.returncode = 1  # Simulate xdotool not found
        
        # Create a new instance
        typer = UniversalTyping()
        
        # Patch _is_xdotool_available to return False
        with patch.object(typer, '_is_xdotool_available', return_value=False):
            with self.assertRaises(UniversalTypingError) as context:
                typer._type_with_xdotool("test")
            self.assertEqual(str(context.exception), "xdotool not available")

    @patch('nixwhisper.universal_typing.QT_AVAILABLE', False)
    def test_type_text_clipboard_failure(self):
        """Test clipboard fallback failure when Qt is not available."""
        # Create a new instance - it should pick up the patched QT_AVAILABLE
        typer = UniversalTyping()
        
        # Test that clipboard method raises the expected error
        with self.assertRaises(UniversalTypingError) as context:
            typer._type_with_clipboard("test")
        self.assertEqual(str(context.exception), "Clipboard not available")

    @patch('nixwhisper.universal_typing.QT_AVAILABLE', True)
    @patch('PyQt5.QtWidgets.QApplication')
    def test_type_text_success(self, mock_qapp):
        """Test the main type_text method with successful typing."""
        # Create a mock clipboard
        mock_clipboard = MagicMock()
        mock_qapp.instance.return_value.clipboard.return_value = mock_clipboard
        
        # Create a new instance with the mocked QApplication
        typer = UniversalTyping()
        
        # Patch the _type_with_pynput method to succeed
        with patch.object(typer, '_type_with_pynput', return_value=True) as mock_type:
            result = typer.type_text("test")
            self.assertTrue(result)
            mock_type.assert_called_once_with("test")
        
        # Test with specific method
        with patch.object(typer, '_type_with_xdotool', return_value=True) as mock_xdotool:
            result = typer.type_text("test", method="xdotool")
            self.assertTrue(result)
            mock_xdotool.assert_called_once_with("test")
            
        # Test with clipboard method
        with patch.object(typer, '_type_with_clipboard', return_value=True) as mock_clip:
            text = "test clipboard"
            result = typer.type_text(text, method="clipboard")
            self.assertTrue(result)
            # Verify clipboard was called
            mock_clip.assert_called_once_with(text)

    def test_type_text_fallback(self):
        """Test fallback through all methods when each one fails."""
        # Setup side effects for each method
        with patch.object(self.typer, '_type_with_pynput', 
                        side_effect=UniversalTypingError("pynput failed")), \
             patch.object(self.typer, '_type_with_xdotool', 
                        side_effect=UniversalTypingError("xdotool failed")), \
             patch.object(self.typer, '_type_with_clipboard', 
                        return_value=True) as mock_clipboard:
            
            # Test
            text = "Fallback test"
            result = self.typer.type_text(text)
            
            # Verify the call worked (clipboard should have succeeded)
            self.assertTrue(result)
            
            # Verify clipboard was called as fallback
            mock_clipboard.assert_called_once_with(text)
        
    @patch('nixwhisper.universal_typing.QT_AVAILABLE', True)
    @patch('PyQt5.QtWidgets.QApplication')
    def test_type_text_no_methods_available(self, mock_qapp):
        """Test typing when no typing methods are available."""
        # Create a mock clipboard
        mock_clipboard = MagicMock()
        mock_qapp.instance.return_value.clipboard.return_value = mock_clipboard
        
        # Create a new instance with the mocked QApplication
        typer = UniversalTyping()
        
        # Save the original preferred_methods
        original_preferred_methods = typer.preferred_methods
        
        try:
            # Set the preferred methods to try all methods
            typer.preferred_methods = ['pynput', 'xdotool', 'clipboard']
            
            # Patch all methods to raise exceptions
            with patch.object(typer, '_type_with_pynput', 
                            side_effect=UniversalTypingError("pynput failed")), \
                 patch.object(typer, '_type_with_xdotool', 
                            side_effect=UniversalTypingError("xdotool failed")), \
                 patch.object(typer, '_type_with_clipboard', 
                            side_effect=UniversalTypingError("clipboard failed")):
                
                # Test that the error is raised with the correct message
                with self.assertRaises(UniversalTypingError) as context:
                    typer.type_text("test")
                self.assertEqual(str(context.exception), "All typing methods failed")
        finally:
            # Restore original preferred_methods
            typer.preferred_methods = original_preferred_methods
    


if __name__ == '__main__':
    unittest.main()
