"""Tests for X11 cursor tracking functionality."""

import pytest
import time
import sys
from unittest.mock import patch, MagicMock, PropertyMock
from nixwhisper.x11_cursor import X11CursorTracker, get_cursor_position, move_cursor, simulate_click, cleanup, X11_AVAILABLE

# Skip tests if X11 is not available
pytestmark = pytest.mark.skipif(not X11_AVAILABLE, reason="X11 not available")

class MockX11Display:
    """Mock X11 display for testing."""
    
    def __init__(self, display_name=None):
        self.display_name = display_name
        self.screen = MagicMock()
        self.screen.root = MockX11Root(0, 0)
        self.closed = False
        self.connected = True
    
    def close(self):
        self.closed = True
        self.connected = False
    
    def sync(self):
        pass
    
    @property
    def screen(self):
        return self._screen
    
    @screen.setter
    def screen(self, value):
        self._screen = value

class MockX11Root:
    """Mock X11 root window for testing."""
    
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        self.warp_called = False
        self.warp_x = 0
        self.warp_y = 0
    
    def query_pointer(self):
        result = MagicMock()
        result.root_x = self.x
        result.root_y = self.y
        return result
    
    def warp_pointer(self, x, y):
        self.warp_called = True
        self.warp_x = x
        self.warp_y = y
        return 1  # Success

@pytest.fixture
def mock_x11(monkeypatch):
    """Fixture to mock X11 display and root window."""
    # Create mock display and root
    mock_display = MockX11Display()
    mock_root = MockX11Root(100, 200)  # Initial cursor position
    mock_display.screen.root = mock_root
    
    # Mock the X11 imports
    mock_xlib = MagicMock()
    mock_xlib.display.Display.return_value = mock_display
    
    # Create mock X object with constants
    mock_x = MagicMock()
    mock_x.ButtonPress = 4  # Example X11 constant
    mock_x.ButtonRelease = 5  # Example X11 constant
    
    # Create mock xtest module
    mock_xtest = MagicMock()
    
    # Patch the modules
    sys.modules['Xlib'] = mock_xlib
    sys.modules['Xlib.X'] = mock_x
    sys.modules['Xlib.ext'] = MagicMock()
    sys.modules['Xlib.ext.xtest'] = mock_xtest
    
    # Reload the module to use the mocks
    import importlib
    import nixwhisper.x11_cursor
    importlib.reload(nixwhisper.x11_cursor)
    
    # Update the global tracker
    nixwhisper.x11_cursor.cursor_tracker = nixwhisper.x11_cursor.X11CursorTracker()
    
    # Make sure the tracker is using our mock display
    nixwhisper.x11_cursor.cursor_tracker.display = mock_display
    nixwhisper.x11_cursor.cursor_tracker.screen = mock_display.screen
    nixwhisper.x11_cursor.cursor_tracker.root = mock_root
    
    yield mock_display, mock_root
    
    # Cleanup
    nixwhisper.x11_cursor.cursor_tracker.cleanup()
    
    # Restore original modules
    del sys.modules['Xlib']
    del sys.modules['Xlib.X']
    del sys.modules['Xlib.ext']
    del sys.modules['Xlib.ext.xtest']
    importlib.reload(nixwhisper.x11_cursor)

def test_x11_cursor_tracker_init(mock_x11):
    """Test X11CursorTracker initialization."""
    mock_display, mock_root = mock_x11
    
    tracker = X11CursorTracker()
    assert tracker.display is not None
    assert tracker.root is not None
    assert tracker.display == mock_display
    assert tracker.root == mock_root

def test_get_cursor_position(mock_x11):
    """Test getting cursor position."""
    mock_display, mock_root = mock_x11
    mock_root.x = 100
    mock_root.y = 200
    
    tracker = X11CursorTracker()
    pos = tracker.get_cursor_position()
    
    assert pos == (100, 200)

def test_move_cursor(mock_x11):
    """Test moving the cursor."""
    mock_display, mock_root = mock_x11
    
    tracker = X11CursorTracker()
    result = tracker.move_cursor(300, 400)
    
    assert result is True
    assert mock_root.warp_called is True
    assert mock_root.warp_x == 300
    assert mock_root.warp_y == 400

def test_simulate_click(mock_x11):
    """Test simulating a mouse click."""
    mock_display, mock_root = mock_x11
    
    tracker = X11CursorTracker()
    result = tracker.simulate_click(button=1)  # Left click
    
    assert result is True
    # Verify fake_input was called with the right parameters
    from Xlib.ext import xtest
    assert xtest.fake_input.call_count == 2  # Press and release

def test_cleanup(mock_x11):
    """Test cleaning up resources."""
    mock_display, mock_root = mock_x11
    
    tracker = X11CursorTracker()
    tracker.cleanup()
    
    assert tracker.display is None
    assert tracker.root is None
    assert tracker.screen is None

def test_module_level_functions(mock_x11):
    """Test the module-level convenience functions."""
    mock_display, mock_root = mock_x11
    mock_root.x = 150
    mock_root.y = 250
    
    # Test get_cursor_position
    pos = get_cursor_position()
    assert pos == (150, 250)
    
    # Test move_cursor
    result = move_cursor(350, 450)
    assert result is True
    assert mock_root.warp_x == 350
    assert mock_root.warp_y == 450
    
    # Test simulate_click
    result = simulate_click(button=1)
    assert result is True
    
    # Test cleanup
    cleanup()
    # This is a bit tricky to test directly since we're using a global
    # But we can check that the cleanup function exists and is callable
    assert callable(cleanup)

def test_error_handling(monkeypatch):
    """Test error handling when X11 is not available."""
    # Save original value
    original_x11_available = X11_AVAILABLE
    
    try:
        # Simulate X11 not being available
        monkeypatch.setattr('nixwhisper.x11_cursor.X11_AVAILABLE', False)
        
        # Reload the module to pick up the change
        import importlib
        import nixwhisper.x11_cursor
        importlib.reload(nixwhisper.x11_cursor)
        
        # Create a new tracker with X11 not available
        tracker = nixwhisper.x11_cursor.X11CursorTracker()
        
        # Test that methods return None or False when X11 is not available
        assert tracker.get_cursor_position() is None
        assert tracker.move_cursor(100, 200) is False
        assert tracker.simulate_click() is False
        
        # Cleanup should still work
        tracker.cleanup()
    finally:
        # Restore original value
        monkeypatch.setattr('nixwhisper.x11_cursor.X11_AVAILABLE', original_x11_available)
        import importlib
        import nixwhisper.x11_cursor
        importlib.reload(nixwhisper.x11_cursor)

if __name__ == "__main__":
    # Simple test to print current cursor position
    pos = get_cursor_position()
    if pos:
        print(f"Current cursor position: {pos}")
    else:
        print("Could not get cursor position")
