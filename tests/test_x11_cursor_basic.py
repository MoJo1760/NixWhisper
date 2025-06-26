"""Basic integration tests for X11 cursor tracking functionality."""

import pytest
from nixwhisper.x11_cursor import X11CursorTracker, get_cursor_position, move_cursor, simulate_click, X11_AVAILABLE

# Skip tests if X11 is not available
pytestmark = pytest.mark.skipif(not X11_AVAILABLE, reason="X11 not available")


def test_x11_available():
    """Test that X11 is available for testing."""
    assert X11_AVAILABLE is True, "X11 should be available for these tests"


def test_tracker_initialization():
    """Test that X11CursorTracker can be initialized."""
    tracker = X11CursorTracker()
    
    # Basic checks
    assert tracker is not None
    if X11_AVAILABLE:
        assert tracker.display is not None
        assert tracker.screen is not None
        assert tracker.root is not None
    
    # Cleanup
    tracker.cleanup()
    
    # After cleanup, these should be None
    assert tracker.display is None
    assert tracker.screen is None
    assert tracker.root is None


def test_get_cursor_position_returns_tuple():
    """Test that get_cursor_position returns a tuple of integers."""
    tracker = X11CursorTracker()
    
    try:
        position = tracker.get_cursor_position()
        
        if X11_AVAILABLE:
            # Should return a tuple of two integers
            assert isinstance(position, tuple)
            assert len(position) == 2
            assert isinstance(position[0], int)
            assert isinstance(position[1], int)
            # Coordinates should be reasonable (not negative, not extremely large)
            assert position[0] >= 0
            assert position[1] >= 0
            assert position[0] < 10000  # Reasonable upper bound
            assert position[1] < 10000  # Reasonable upper bound
        else:
            assert position is None
    finally:
        tracker.cleanup()


def test_module_functions():
    """Test module-level convenience functions."""
    # Test get_cursor_position function
    position = get_cursor_position()
    if X11_AVAILABLE:
        assert isinstance(position, tuple)
        assert len(position) == 2
    else:
        assert position is None
    
    # Test move_cursor function (move to current position, should be safe)
    if X11_AVAILABLE and position:
        current_x, current_y = position
        result = move_cursor(current_x, current_y)
        assert isinstance(result, bool)
    
    # Test simulate_click function (just check it doesn't crash)
    if X11_AVAILABLE:
        result = simulate_click(button=1)
        assert isinstance(result, bool)


def test_x11_not_available_behavior():
    """Test behavior when X11 is not available."""
    # This test will only run if X11 is available, but we can simulate
    # the not-available case by creating a tracker and checking fallback behavior
    
    # Create a tracker
    tracker = X11CursorTracker()
    
    # Even if X11 is available, the methods should handle errors gracefully
    try:
        position = tracker.get_cursor_position()
        # Should either return a valid position or None
        assert position is None or (isinstance(position, tuple) and len(position) == 2)
        
        # Move cursor should return a boolean
        result = tracker.move_cursor(100, 100)
        assert isinstance(result, bool)
        
        # Simulate click should return a boolean
        result = tracker.simulate_click()
        assert isinstance(result, bool)
        
    finally:
        tracker.cleanup()


if __name__ == "__main__":
    # Manual test when run directly
    print("Running basic X11 cursor tracking tests...")
    
    if not X11_AVAILABLE:
        print("X11 not available, skipping tests")
        exit(0)
    
    try:
        # Test initialization
        print("Testing initialization...")
        tracker = X11CursorTracker()
        print("✓ Tracker initialized successfully")
        
        # Test getting cursor position
        print("Testing cursor position...")
        pos = tracker.get_cursor_position()
        print(f"✓ Current cursor position: {pos}")
        
        # Test cleanup
        print("Testing cleanup...")
        tracker.cleanup()
        print("✓ Cleanup completed successfully")
        
        # Test module functions
        print("Testing module functions...")
        pos = get_cursor_position()
        print(f"✓ Module function get_cursor_position: {pos}")
        
        print("All basic tests passed!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
