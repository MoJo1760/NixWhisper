"""Simple tests for X11 cursor tracking functionality."""

import pytest
from unittest.mock import patch, MagicMock
from nixwhisper.x11_cursor import X11CursorTracker, get_cursor_position, move_cursor, simulate_click, X11_AVAILABLE

# Skip tests if X11 is not available
pytestmark = pytest.mark.skipif(not X11_AVAILABLE, reason="X11 not available")


class TestX11CursorTracker:
    """Test cases for X11CursorTracker class."""

    @patch('nixwhisper.x11_cursor.Xlib')
    def test_init_success(self, mock_xlib):
        """Test successful initialization of X11CursorTracker."""
        # Set up mocks
        mock_display = MagicMock()
        mock_screen = MagicMock()
        mock_root = MagicMock()
        
        mock_xlib.display.Display.return_value = mock_display
        mock_display.screen.return_value = mock_screen
        mock_screen.root = mock_root
        
        # Create tracker
        tracker = X11CursorTracker()
        
        # Verify initialization
        assert tracker.display == mock_display
        assert tracker.screen == mock_screen
        assert tracker.root == mock_root
        
        # Cleanup
        tracker.cleanup()

    @patch('nixwhisper.x11_cursor.Xlib')
    def test_get_cursor_position(self, mock_xlib):
        """Test getting cursor position."""
        # Set up mocks
        mock_display = MagicMock()
        mock_screen = MagicMock()
        mock_root = MagicMock()
        mock_pointer = MagicMock()
        
        mock_xlib.display.Display.return_value = mock_display
        mock_display.screen.return_value = mock_screen
        mock_screen.root = mock_root
        mock_root.query_pointer.return_value = mock_pointer
        
        # Set cursor position
        test_x, test_y = 123, 456
        mock_pointer.root_x = test_x
        mock_pointer.root_y = test_y
        
        # Create tracker and get position
        tracker = X11CursorTracker()
        position = tracker.get_cursor_position()
        
        # Verify result
        assert position == (test_x, test_y)
        mock_root.query_pointer.assert_called_once()
        
        # Cleanup
        tracker.cleanup()

    @patch('nixwhisper.x11_cursor.Xlib')
    def test_move_cursor(self, mock_xlib):
        """Test moving cursor."""
        # Set up mocks
        mock_display = MagicMock()
        mock_screen = MagicMock()
        mock_root = MagicMock()
        
        mock_xlib.display.Display.return_value = mock_display
        mock_display.screen.return_value = mock_screen
        mock_screen.root = mock_root
        mock_root.warp_pointer.return_value = 1  # Success
        
        # Create tracker and move cursor
        tracker = X11CursorTracker()
        target_x, target_y = 300, 400
        result = tracker.move_cursor(target_x, target_y)
        
        # Verify result
        assert result is True
        mock_root.warp_pointer.assert_called_once_with(target_x, target_y)
        mock_display.sync.assert_called_once()
        
        # Cleanup
        tracker.cleanup()

    @patch('nixwhisper.x11_cursor.Xlib')
    def test_simulate_click(self, mock_xlib):
        """Test simulating mouse click."""
        # Set up mocks
        mock_display = MagicMock()
        mock_screen = MagicMock()
        mock_root = MagicMock()
        mock_x = MagicMock()
        mock_xtest = MagicMock()
        
        mock_xlib.display.Display.return_value = mock_display
        mock_display.screen.return_value = mock_screen
        mock_screen.root = mock_root
        mock_xlib.X = mock_x
        mock_xlib.ext.xtest = mock_xtest
        
        # Set up X constants
        mock_x.ButtonPress = 4
        mock_x.ButtonRelease = 5
        
        # Create tracker and simulate click
        tracker = X11CursorTracker()
        result = tracker.simulate_click(button=1)
        
        # Verify result
        assert result is True
        assert mock_xtest.fake_input.call_count == 2
        mock_display.sync.assert_called()
        
        # Cleanup
        tracker.cleanup()

    @patch('nixwhisper.x11_cursor.Xlib')
    def test_cleanup(self, mock_xlib):
        """Test cleanup of resources."""
        # Set up mocks
        mock_display = MagicMock()
        mock_screen = MagicMock()
        mock_root = MagicMock()
        
        mock_xlib.display.Display.return_value = mock_display
        mock_display.screen.return_value = mock_screen
        mock_screen.root = mock_root
        
        # Create tracker and cleanup
        tracker = X11CursorTracker()
        tracker.cleanup()
        
        # Verify cleanup
        mock_display.close.assert_called_once()
        assert tracker.display is None
        assert tracker.screen is None
        assert tracker.root is None

    @patch('nixwhisper.x11_cursor.X11_AVAILABLE', False)
    def test_x11_not_available(self):
        """Test behavior when X11 is not available."""
        # Create tracker when X11 is not available
        tracker = X11CursorTracker()
        
        # Verify methods return None/False
        assert tracker.get_cursor_position() is None
        assert tracker.move_cursor(100, 200) is False
        assert tracker.simulate_click() is False
        
        # Cleanup should work
        tracker.cleanup()


class TestModuleFunctions:
    """Test module-level convenience functions."""

    @patch('nixwhisper.x11_cursor.cursor_tracker')
    def test_get_cursor_position_function(self, mock_tracker):
        """Test get_cursor_position module function."""
        # Set up mock
        mock_tracker.get_cursor_position.return_value = (100, 200)
        
        # Call function
        result = get_cursor_position()
        
        # Verify result
        assert result == (100, 200)
        mock_tracker.get_cursor_position.assert_called_once()

    @patch('nixwhisper.x11_cursor.cursor_tracker')
    def test_move_cursor_function(self, mock_tracker):
        """Test move_cursor module function."""
        # Set up mock
        mock_tracker.move_cursor.return_value = True
        
        # Call function
        result = move_cursor(300, 400)
        
        # Verify result
        assert result is True
        mock_tracker.move_cursor.assert_called_once_with(300, 400)

    @patch('nixwhisper.x11_cursor.cursor_tracker')
    def test_simulate_click_function(self, mock_tracker):
        """Test simulate_click module function."""
        # Set up mock
        mock_tracker.simulate_click.return_value = True
        
        # Call function
        result = simulate_click(button=1)
        
        # Verify result
        assert result is True
        mock_tracker.simulate_click.assert_called_once_with(button=1)


if __name__ == "__main__":
    # Simple manual test
    print("Testing X11 cursor tracking...")
    if X11_AVAILABLE:
        try:
            tracker = X11CursorTracker()
            pos = tracker.get_cursor_position()
            print(f"Current cursor position: {pos}")
            tracker.cleanup()
            print("Test completed successfully!")
        except Exception as e:
            print(f"Test failed: {e}")
    else:
        print("X11 not available, skipping manual test")
