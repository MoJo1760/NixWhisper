"""Unit tests for the UniversalTyping class."""

from unittest.mock import MagicMock, patch
from unittest import TestCase, main

from nixwhisper.universal_typing import UniversalTyping, UniversalTypingError


class TestUniversalTyping(TestCase):
    """Test cases for the UniversalTyping class."""
    def setUp(self):
        """Set up test fixtures."""
        # Save the original modules
        self.original_modules = {}
        module_names = [
            'pynput',
            'PyQt5',
            'PyQt5.QtWidgets',
            'PyQt5.QtGui'
        ]
        for module_name in module_names:
            self.original_modules[module_name] = globals().get(module_name)

        # Create patches for all external dependencies
        self.patches = [
            patch('pynput.keyboard.Controller'),
            patch('PyQt5.QtWidgets.QApplication'),
            patch('PyQt5.QtGui.QClipboard'),
            patch('nixwhisper.universal_typing.subprocess')
        ]

        # Start all patches
        for p in self.patches:
            p.start()

        # Create a UniversalTyping instance for testing
        self.typer = UniversalTyping()

    def tearDown(self):
        """Clean up test fixtures."""
        # Stop all patches
        for p in self.patches:
            p.stop()

        # Restore original modules
        for module_name, module in self.original_modules.items():
            if module is None:
                if module_name in globals():
                    del globals()[module_name]
            else:
                globals()[module_name] = module

        # Remove any remaining references to the mocked modules
        modules_to_remove = [
            'pynput',
            'pynput.keyboard',
            'PyQt5',
            'PyQt5.QtWidgets',
            'PyQt5.QtGui'
        ]

        for module in modules_to_remove:
            if module in globals():
                del globals()[module]

    @patch('nixwhisper.universal_typing.PYNPROMPT_AVAILABLE', False)
    def test_type_text_pynput_unavailable(self):
        """Test typing text when pynput is unavailable.

        This test verifies that the internal pynput typing method correctly
        handles the case when pynput is not available.

        Note: This test accesses protected member _type_with_pynput directly
        as it is testing the internal implementation details of the typing
        methods.
        """
        with self.assertRaises(UniversalTypingError):
            self.typer._type_with_pynput("test")

    @patch('nixwhisper.universal_typing.QT_AVAILABLE', False)
    def test_type_text_qt_unavailable(self):
        """Test typing text when Qt is unavailable.

        This test verifies that the internal clipboard typing method correctly
        handles the case when Qt is not available.

        Note: This test accesses protected member _type_with_clipboard directly
        as it is testing the internal implementation details of the typing
        methods.
        """
        with self.assertRaises(UniversalTypingError):
            self.typer._type_with_clipboard("test")

    def test_type_text_invalid_method(self):
        """Test typing text with an invalid method.

        This test verifies that attempting to type text with an invalid
        method raises an appropriate error.
        """
        with self.assertRaises(UniversalTypingError):
            self.typer.type_text("test", "invalid")

    def test_type_text_xdotool_error(self):
        """Test typing text when xdotool fails.

        This test verifies that the internal xdotool typing method correctly
        handles failures from the xdotool command.

        Note: This test accesses protected member _type_with_xdotool directly
        as it is testing the internal implementation details of the typing
        methods.
        """
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("xdotool error")
            with self.assertRaises(UniversalTypingError):
                self.typer._type_with_xdotool("test")

    @patch('nixwhisper.universal_typing.PYNPROMPT_AVAILABLE', False)
    def test_type_text_pynput_unavailable_fallback(self):
        """Test typing text when pynput is unavailable and fallback is used."""
        self.typer = UniversalTyping()
        with patch.object(self.typer, '_type_with_xdotool', return_value=True):
            result = self.typer.type_text("test")
            self.assertTrue(result)

    @patch('nixwhisper.universal_typing.QT_AVAILABLE', False)
    def test_type_text_qt_unavailable_fallback(self):
        """Test typing text when Qt is unavailable and fallback is used."""
        self.typer = UniversalTyping()
        with patch.object(self.typer, '_type_with_xdotool', return_value=True):
            result = self.typer.type_text("test")
            self.assertTrue(result)

    def test_type_text_success(self):
        """Test typing text with successful typing."""
        self.typer = UniversalTyping()
        with patch.object(self.typer, '_type_with_pynput', return_value=True):
            result = self.typer.type_text("test")
            self.assertTrue(result)

    def test_type_text_all_methods_fail(self):
        """Test typing text when all methods fail.

        This test verifies that attempting to type text when all available
        typing methods fail results in an appropriate error.
        """
        pynput_error = UniversalTypingError("pynput failed")
        xdotool_error = UniversalTypingError("xdotool failed")
        clipboard_error = UniversalTypingError("clipboard failed")
        with patch.object(
            self.typer, '_type_with_pynput', side_effect=pynput_error
        ), patch.object(
            self.typer, '_type_with_xdotool', side_effect=xdotool_error
        ), patch.object(
            self.typer, '_type_with_clipboard', side_effect=clipboard_error
        ):
            with self.assertRaises(UniversalTypingError) as context:
                self.typer.type_text("test")
            self.assertEqual(
                str(context.exception),
                "All typing methods failed"
            )

    @patch('nixwhisper.universal_typing.QT_AVAILABLE', False)
    def test_type_text_clipboard_failure(self):
        """Test clipboard fallback failure when Qt is not available.

        Note: This test accesses protected member _type_with_clipboard directly
        as it is testing the internal implementation details of the typing
        methods.
        """
        # Create a new instance - it should pick up the patched QT_AVAILABLE
        typer = UniversalTyping()
        # Test that clipboard method raises the expected error
        with self.assertRaises(UniversalTypingError) as context:
            typer._type_with_clipboard("test")
        self.assertEqual(str(context.exception), "Clipboard not available")

    @patch('nixwhisper.universal_typing.QT_AVAILABLE', True)
    @patch('nixwhisper.universal_typing.PYNPROMPT_AVAILABLE', False)
    @patch('nixwhisper.universal_typing.QApplication')
    @patch('nixwhisper.universal_typing.QClipboard')
    def test_type_text_with_clipboard(self, mock_clipboard_class, mock_qapp, *_):
        """Test typing text using clipboard method."""
        # Create a mock clipboard
        mock_clipboard = MagicMock()
        mock_clipboard.text.return_value = ""
        # Set up QApplication
        mock_qapp.processEvents = MagicMock()
        # Set up the clipboard mode
        mock_clipboard_class.Clipboard = 0
        # Create a new instance with the mocked QApplication
        typer = UniversalTyping()
        typer.qt_clipboard = mock_clipboard
        # Test with clipboard method
        text = "test clipboard"
        result = typer.type_text(text, "clipboard")
        self.assertTrue(result)
        mock_clipboard.setText.assert_any_call(text, 0)
        # Test fallback
        with patch.object(typer, '_type_with_pynput',
                        side_effect=UniversalTypingError("pynput failed")), \
            patch.object(typer, '_type_with_xdotool',
                        side_effect=UniversalTypingError("xdotool failed")):
            # Test
            text = "Fallback test"
            result = typer.type_text(text)
            self.assertTrue(result)
            # Verify clipboard was called as fallback
            mock_clipboard.setText.assert_any_call(text, 0)

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
    main()
