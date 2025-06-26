"""Tests for X11 cursor tracking functionality."""

import pytest
import sys
from unittest.mock import MagicMock, patch, PropertyMock
from nixwhisper.x11_cursor import X11CursorTracker, X11_AVAILABLE

# Skip tests if X11 is not available
pytestmark = pytest.mark.skipif(not X11_AVAILABLE, reason="X11 not available")

# Mock X11 modules
class MockX11Modules:
    """Container for mocked X11 modules."""
    
    def __init__(self):
        # Mock X constants
        self.X = MagicMock()
        self.X.ButtonPress = 4
        self.X.ButtonRelease = 5
        
        # Mock display module
        self.display = MagicMock()
        
        # Mock screen and root window
        self.screen = MagicMock()
        self.root = MagicMock()
        self.screen.root = self.root
        
        # Set up query_pointer to return mock values
        self.pointer = MagicMock()
        self.pointer.root_x = 100
        self.pointer.root_y = 200
        self.root.query_pointer.return_value = self.pointer
        
        # Set up display to return our mock display
        self.display.Display.return_value = self.display
        self.display.Screen.return_value = self.screen
        
        # Mock XTest
        self.ext = MagicMock()
        self.ext.xtest = MagicMock()

# Global mock for X11 modules
mock_x11 = MockX11Modules()

@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
    """Set up mocks for X11 modules."""
    # Mock the X11 imports
    monkeypatch.setitem(sys.modules, 'Xlib', MagicMock())
    monkeypatch.setattr('Xlib.X', mock_x11.X)
    monkeypatch.setattr('Xlib.display', mock_x11.display)
    monkeypatch.setattr('Xlib.ext', mock_x11.ext)
    
    # Reset mocks before each test
    mock_x11.display.reset_mock()
    mock_x11.root.reset_mock()
    mock_x11.ext.xtest.reset_mock()
    
    # Reset the pointer position
    mock_x11.pointer.root_x = 100
    mock_x11.pointer.root_y = 200
    
    # Reload the module to use the mocks
    import importlib
    import nixwhisper.x11_cursor
    importlib.reload(nixwhisper.x11_cursor)
    
    # Return the mock modules for tests to use
    return mock_x11

def test_x11_cursor_tracker_init():
    """Test X11CursorTracker initialization."""
    # Create a new tracker
    tracker = X11CursorTracker()
    
    # Verify the display was initialized
    mock_x11.display.Display.assert_called_once()
    
    # Verify the screen and root window are accessible
    assert tracker.display == mock_x11.display
    assert tracker.screen == mock_x11.screen
    assert tracker.root == mock_x11.root

def test_get_cursor_position():
    """Test getting cursor position."""
    # Set up test data
    test_x, test_y = 123, 456
    mock_x11.pointer.root_x = test_x
    mock_x11.pointer.root_y = test_y
    
    # Get the cursor position
    tracker = X11CursorTracker()
    pos = tracker.get_cursor_position()
    
    # Verify the result
    assert pos == (test_x, test_y)
    # Verify query_pointer was called on the root window
    mock_x11.root.query_pointer.assert_called_once()

def test_move_cursor():
    """Test moving the cursor."""
    # Set up test data
    target_x, target_y = 300, 400
    
    # Move the cursor
    tracker = X11CursorTracker()
    result = tracker.move_cursor(target_x, target_y)
    
    # Verify the result
    assert result is True
    # Verify warp_pointer was called with the correct coordinates
    mock_x11.root.warp_pointer.assert_called_once_with(target_x, target_y)
    # Verify sync was called
    mock_x11.display.sync.assert_called_once()

def test_simulate_click():
    """Test simulating a mouse click."""
    # Reset mocks
    mock_x11.ext.xtest.fake_input.reset_mock()
    mock_x11.display.sync.reset_mock()
    
    # Simulate a left click (button 1)
    tracker = X11CursorTracker()
    result = tracker.simulate_click(button=1)
    
    # Verify the result
    assert result is True
    
    # Verify fake_input was called for both press and release
    assert mock_x11.ext.xtest.fake_input.call_count == 2
    
    # Get the calls to fake_input
    calls = mock_x11.ext.xtest.fake_input.call_args_list
    
    # Verify the press event
    press_call = calls[0][0]
    assert press_call[1] == mock_x11.X.ButtonPress  # Event type
    assert press_call[2] == 1  # Button 1
    
    # Verify the release event
    release_call = calls[1][0]
    assert release_call[1] == mock_x11.X.ButtonRelease  # Event type
    assert release_call[2] == 1  # Button 1
    
    # Verify sync was called
    assert mock_x11.display.sync.call_count >= 1
    
    # Cleanup
    tracker.cleanup()

def test_cleanup():
    """Test cleanup of X11 resources."""
    # Reset mock
    mock_x11.display.close.reset_mock()
    
    # Create and then cleanup a tracker
    tracker = X11CursorTracker()
    tracker.cleanup()
    
    # Verify the display was closed
    mock_x11.display.close.assert_called_once()
    assert tracker.display is None
    assert tracker.screen is None
    assert tracker.root is None

@patch('nixwhisper.x11_cursor.X11_AVAILABLE', False)
def test_x11_not_available():
    """Test behavior when X11 is not available."""
    # Reload the module with X11_AVAILABLE=False
    import importlib
    import nixwhisper.x11_cursor
    importlib.reload(nixwhisper.x11_cursor)
    
    # Create a new tracker - should not try to initialize X11
    tracker = nixwhisper.x11_cursor.X11CursorTracker()
    
    # Verify methods return None or False when X11 is not available
    assert tracker.get_cursor_position() is None
    assert tracker.move_cursor(100, 200) is False
    assert tracker.simulate_click() is False
    
    # Cleanup should still work
    tracker.cleanup()
    
    # Reload the module to restore original state
    importlib.reload(nixwhisper.x11_cursor)
