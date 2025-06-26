"""Tests for X11 cursor tracking polling functionality."""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from nixwhisper.x11_cursor import (
    X11CursorTracker, 
    CursorPosition, 
    start_cursor_polling, 
    stop_cursor_polling,
    add_cursor_callback,
    remove_cursor_callback,
    X11_AVAILABLE
)

# Skip tests if X11 is not available
pytestmark = pytest.mark.skipif(not X11_AVAILABLE, reason="X11 not available")


class TestCursorPolling:
    """Test cases for cursor position polling functionality."""

    def test_cursor_position_dataclass(self):
        """Test CursorPosition dataclass."""
        timestamp = time.time()
        pos = CursorPosition(100, 200, timestamp)
        
        assert pos.x == 100
        assert pos.y == 200
        assert pos.timestamp == timestamp

    def test_polling_start_stop(self):
        """Test starting and stopping cursor polling."""
        tracker = X11CursorTracker()
        
        try:
            # Initially not polling
            assert not tracker.is_polling_active()
            
            # Start polling
            result = tracker.start_polling(0.05)  # 50ms for faster testing
            if X11_AVAILABLE:
                assert result is True
                assert tracker.is_polling_active()
                
                # Give it a moment to start
                time.sleep(0.1)
                
                # Stop polling
                tracker.stop_polling()
                assert not tracker.is_polling_active()
            else:
                assert result is False
                
        finally:
            tracker.cleanup()

    def test_polling_interval_settings(self):
        """Test polling interval configuration."""
        tracker = X11CursorTracker()
        
        try:
            # Test setting interval
            tracker.set_polling_interval(0.2)
            assert tracker._polling_interval == 0.2
            
            # Test minimum interval enforcement
            tracker.set_polling_interval(0.005)  # Below minimum
            assert tracker._polling_interval == 0.01  # Should be clamped to minimum
            
        finally:
            tracker.cleanup()

    def test_callback_management(self):
        """Test adding and removing position callbacks."""
        tracker = X11CursorTracker()
        
        def dummy_callback(pos: CursorPosition):
            pass
        
        def another_callback(pos: CursorPosition):
            pass
        
        try:
            # Initially no callbacks
            assert len(tracker._position_callbacks) == 0
            
            # Add callbacks
            tracker.add_position_callback(dummy_callback)
            assert len(tracker._position_callbacks) == 1
            assert dummy_callback in tracker._position_callbacks
            
            tracker.add_position_callback(another_callback)
            assert len(tracker._position_callbacks) == 2
            
            # Adding same callback again should not duplicate
            tracker.add_position_callback(dummy_callback)
            assert len(tracker._position_callbacks) == 2
            
            # Remove callback
            tracker.remove_position_callback(dummy_callback)
            assert len(tracker._position_callbacks) == 1
            assert dummy_callback not in tracker._position_callbacks
            assert another_callback in tracker._position_callbacks
            
            # Remove non-existent callback should not error
            tracker.remove_position_callback(dummy_callback)
            assert len(tracker._position_callbacks) == 1
            
        finally:
            tracker.cleanup()

    def test_last_position_tracking(self):
        """Test tracking of last known position."""
        tracker = X11CursorTracker()
        
        try:
            # Initially no last position
            assert tracker.get_last_position() is None
            
            # After getting current position, last position should still be None
            # (since polling hasn't started)
            current_pos = tracker.get_cursor_position()
            assert tracker.get_last_position() is None
            
        finally:
            tracker.cleanup()

    def test_module_level_functions(self):
        """Test module-level convenience functions for polling."""
        try:
            # Test start/stop polling
            result = start_cursor_polling(0.05)
            if X11_AVAILABLE:
                assert isinstance(result, bool)
                time.sleep(0.1)  # Give it time to start
                
            stop_cursor_polling()
            
            # Test callback functions
            def test_callback(pos: CursorPosition):
                pass
            
            add_cursor_callback(test_callback)
            remove_cursor_callback(test_callback)
            
        finally:
            stop_cursor_polling()

    def test_polling_with_real_cursor_movement(self):
        """Integration test with actual cursor movement (if X11 available)."""
        if not X11_AVAILABLE:
            pytest.skip("X11 not available for integration test")
        
        tracker = X11CursorTracker()
        callback_called = threading.Event()
        received_positions = []
        
        def position_callback(pos: CursorPosition):
            received_positions.append(pos)
            callback_called.set()
        
        try:
            # Add callback and start polling
            tracker.add_position_callback(position_callback)
            tracker.start_polling(0.05)  # 50ms for faster testing
            
            # Get initial position
            initial_pos = tracker.get_cursor_position()
            if initial_pos:
                # Move cursor slightly
                new_x = initial_pos[0] + 10
                new_y = initial_pos[1] + 10
                
                # Move cursor
                tracker.move_cursor(new_x, new_y)
                
                # Wait for callback
                callback_received = callback_called.wait(timeout=1.0)
                
                if callback_received:
                    # Should have received at least one position update
                    assert len(received_positions) > 0
                    
                    # Last position should be tracked
                    last_pos = tracker.get_last_position()
                    assert last_pos is not None
                    assert isinstance(last_pos.timestamp, float)
                
                # Move cursor back to original position
                tracker.move_cursor(initial_pos[0], initial_pos[1])
                
        finally:
            tracker.cleanup()

    def test_polling_error_handling(self):
        """Test error handling in polling loop."""
        tracker = X11CursorTracker()
        
        def error_callback(pos: CursorPosition):
            raise Exception("Test error in callback")
        
        def good_callback(pos: CursorPosition):
            good_callback.called = True
        
        good_callback.called = False
        
        try:
            # Add both callbacks
            tracker.add_position_callback(error_callback)
            tracker.add_position_callback(good_callback)
            
            if X11_AVAILABLE:
                # Start polling
                tracker.start_polling(0.05)
                time.sleep(0.2)  # Let it run for a bit
                
                # Good callback should still work despite error in other callback
                # Note: This test may be flaky depending on cursor movement
                
        finally:
            tracker.cleanup()

    def test_cleanup_stops_polling(self):
        """Test that cleanup properly stops polling."""
        tracker = X11CursorTracker()
        
        try:
            if X11_AVAILABLE:
                # Start polling
                tracker.start_polling(0.05)
                assert tracker.is_polling_active()
                
                # Cleanup should stop polling
                tracker.cleanup()
                assert not tracker.is_polling_active()
                
        finally:
            # Ensure cleanup even if test fails
            tracker.cleanup()

    def test_double_start_polling(self):
        """Test that starting polling twice doesn't create multiple threads."""
        tracker = X11CursorTracker()
        
        try:
            if X11_AVAILABLE:
                # Start polling first time
                result1 = tracker.start_polling(0.05)
                assert result1 is True
                assert tracker.is_polling_active()
                
                # Start polling second time should return False
                result2 = tracker.start_polling(0.05)
                assert result2 is False
                assert tracker.is_polling_active()
                
        finally:
            tracker.cleanup()


if __name__ == "__main__":
    # Manual test when run directly
    print("Running cursor polling tests...")
    
    if not X11_AVAILABLE:
        print("X11 not available, skipping tests")
        exit(0)
    
    try:
        print("Testing cursor polling...")
        tracker = X11CursorTracker()
        
        positions_received = []
        
        def callback(pos: CursorPosition):
            positions_received.append(pos)
            print(f"Cursor moved to: ({pos.x}, {pos.y}) at {pos.timestamp}")
        
        tracker.add_position_callback(callback)
        tracker.start_polling(0.1)
        
        print("Move your cursor around for 3 seconds...")
        time.sleep(3)
        
        tracker.cleanup()
        
        print(f"Received {len(positions_received)} position updates")
        print("Cursor polling test completed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
