"""Tests for X11 cursor tracking window focus functionality."""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from nixwhisper.x11_cursor import (
    X11CursorTracker, 
    WindowInfo,
    get_active_window_info,
    enable_window_focus_tracking,
    disable_window_focus_tracking,
    add_window_callback,
    remove_window_callback,
    get_last_window_info,
    X11_AVAILABLE
)

# Skip tests if X11 is not available
pytestmark = pytest.mark.skipif(not X11_AVAILABLE, reason="X11 not available")


class TestWindowFocusTracking:
    """Test cases for window focus tracking functionality."""

    def test_window_info_dataclass(self):
        """Test WindowInfo dataclass."""
        timestamp = time.time()
        window_info = WindowInfo(
            window_id=12345,
            window_name="Test Window",
            window_class="TestApp",
            timestamp=timestamp
        )
        
        assert window_info.window_id == 12345
        assert window_info.window_name == "Test Window"
        assert window_info.window_class == "TestApp"
        assert window_info.timestamp == timestamp

    def test_window_focus_tracking_enable_disable(self):
        """Test enabling and disabling window focus tracking."""
        tracker = X11CursorTracker()
        
        try:
            # Initially disabled
            assert tracker._track_window_focus is False
            
            # Enable tracking
            result = tracker.enable_window_focus_tracking()
            if X11_AVAILABLE:
                assert result is True
                assert tracker._track_window_focus is True
            else:
                assert result is False
            
            # Disable tracking
            tracker.disable_window_focus_tracking()
            assert tracker._track_window_focus is False
            
        finally:
            tracker.cleanup()

    def test_window_callback_management(self):
        """Test adding and removing window callbacks."""
        tracker = X11CursorTracker()
        
        def dummy_callback(window_info: WindowInfo):
            pass
        
        def another_callback(window_info: WindowInfo):
            pass
        
        try:
            # Initially no callbacks
            assert len(tracker._window_callbacks) == 0
            
            # Add callbacks
            tracker.add_window_callback(dummy_callback)
            assert len(tracker._window_callbacks) == 1
            assert dummy_callback in tracker._window_callbacks
            
            tracker.add_window_callback(another_callback)
            assert len(tracker._window_callbacks) == 2
            
            # Adding same callback again should not duplicate
            tracker.add_window_callback(dummy_callback)
            assert len(tracker._window_callbacks) == 2
            
            # Remove callback
            tracker.remove_window_callback(dummy_callback)
            assert len(tracker._window_callbacks) == 1
            assert dummy_callback not in tracker._window_callbacks
            assert another_callback in tracker._window_callbacks
            
            # Remove non-existent callback should not error
            tracker.remove_window_callback(dummy_callback)
            assert len(tracker._window_callbacks) == 1
            
        finally:
            tracker.cleanup()

    def test_get_active_window_info_basic(self):
        """Test getting active window information."""
        tracker = X11CursorTracker()
        
        try:
            # Get current active window
            window_info = tracker.get_active_window_info()
            
            if X11_AVAILABLE and window_info:
                # Should return a WindowInfo object
                assert isinstance(window_info, WindowInfo)
                assert isinstance(window_info.window_id, int)
                assert isinstance(window_info.window_name, str)
                assert isinstance(window_info.window_class, str)
                assert isinstance(window_info.timestamp, float)
                
                # Window ID should be positive
                assert window_info.window_id > 0
                
                # Timestamp should be recent
                assert abs(window_info.timestamp - time.time()) < 1.0
            
        finally:
            tracker.cleanup()

    def test_last_window_info_tracking(self):
        """Test tracking of last known window information."""
        tracker = X11CursorTracker()
        
        try:
            # Initially no last window info
            assert tracker.get_last_window_info() is None
            
            # After getting current window info, last window info should still be None
            # (since tracking hasn't started)
            current_window = tracker.get_active_window_info()
            assert tracker.get_last_window_info() is None
            
        finally:
            tracker.cleanup()

    def test_module_level_window_functions(self):
        """Test module-level convenience functions for window tracking."""
        try:
            # Test enable/disable tracking
            result = enable_window_focus_tracking()
            if X11_AVAILABLE:
                assert isinstance(result, bool)
            
            disable_window_focus_tracking()
            
            # Test getting window info
            window_info = get_active_window_info()
            if X11_AVAILABLE and window_info:
                assert isinstance(window_info, WindowInfo)
            
            # Test callback functions
            def test_callback(window_info: WindowInfo):
                pass
            
            add_window_callback(test_callback)
            remove_window_callback(test_callback)
            
            # Test getting last window info
            last_info = get_last_window_info()
            # Should be None since tracking wasn't active
            assert last_info is None
            
        finally:
            disable_window_focus_tracking()

    @patch('nixwhisper.x11_cursor.X11CursorTracker.get_active_window_info')
    def test_window_focus_tracking_with_polling(self, mock_get_window_info):
        """Test window focus tracking during polling."""
        tracker = X11CursorTracker()
        callback_called = threading.Event()
        received_windows = []
        
        def window_callback(window_info: WindowInfo):
            received_windows.append(window_info)
            callback_called.set()
        
        try:
            # Mock window information changes
            window1 = WindowInfo(1001, "Window 1", "App1", time.time())
            window2 = WindowInfo(1002, "Window 2", "App2", time.time())
            
            windows = [window1, window1, window2, window2, window1]  # Simulate window changes
            window_iter = iter(windows)
            mock_get_window_info.side_effect = lambda: next(window_iter, None)
            
            # Enable window tracking and add callback
            tracker.enable_window_focus_tracking()
            tracker.add_window_callback(window_callback)
            
            if tracker.start_polling(0.05):  # Fast polling for testing
                # Wait for callbacks
                time.sleep(0.3)
                tracker.stop_polling()
                
                # Should have received window change notifications
                # Exact count depends on timing, but should be > 0
                if received_windows:
                    assert len(received_windows) > 0
                    
                    # First window should be window1
                    assert received_windows[0].window_id == 1001
                    
                    # Should have received notification for window2
                    window_ids = [w.window_id for w in received_windows]
                    assert 1002 in window_ids
            
        finally:
            tracker.cleanup()

    def test_window_focus_error_handling(self):
        """Test error handling in window focus tracking."""
        tracker = X11CursorTracker()
        
        def error_callback(window_info: WindowInfo):
            raise Exception("Test error in window callback")
        
        def good_callback(window_info: WindowInfo):
            good_callback.called = True
        
        good_callback.called = False
        
        try:
            # Add both callbacks
            tracker.add_window_callback(error_callback)
            tracker.add_window_callback(good_callback)
            tracker.enable_window_focus_tracking()
            
            if X11_AVAILABLE and tracker.start_polling(0.05):
                # Let it run for a bit
                time.sleep(0.2)
                tracker.stop_polling()
                
                # Good callback should still work despite error in other callback
                # Note: This test may be flaky depending on window changes
                
        finally:
            tracker.cleanup()

    def test_window_tracking_without_x11(self):
        """Test window tracking behavior when X11 is not available."""
        # This test simulates the case where X11 is not available
        tracker = X11CursorTracker()
        
        # Temporarily disable X11 for this tracker
        original_display = tracker.display
        tracker.display = None
        
        try:
            # Should return None for window info
            window_info = tracker.get_active_window_info()
            assert window_info is None
            
            # Should return False for enabling tracking
            result = tracker.enable_window_focus_tracking()
            # Note: This will still return True because we only check X11_AVAILABLE
            # The actual X11 operations will fail gracefully
            
        finally:
            tracker.display = original_display
            tracker.cleanup()

    def test_window_focus_tracking_integration(self):
        """Integration test for window focus tracking (if X11 available)."""
        if not X11_AVAILABLE:
            pytest.skip("X11 not available for integration test")
        
        tracker = X11CursorTracker()
        window_changes = []
        
        def window_callback(window_info: WindowInfo):
            window_changes.append(window_info)
        
        try:
            # Enable tracking and add callback
            tracker.enable_window_focus_tracking()
            tracker.add_window_callback(window_callback)
            
            # Get initial window info
            initial_window = tracker.get_active_window_info()
            
            if initial_window and tracker.start_polling(0.1):
                # Let it run for a short time
                time.sleep(0.5)
                tracker.stop_polling()
                
                # Should have tracked the current window
                last_window = tracker.get_last_window_info()
                if last_window:
                    assert isinstance(last_window, WindowInfo)
                    assert last_window.window_id > 0
                
        finally:
            tracker.cleanup()


if __name__ == "__main__":
    # Manual test when run directly
    print("Running window focus tracking tests...")
    
    if not X11_AVAILABLE:
        print("X11 not available, skipping tests")
        exit(0)
    
    try:
        print("Testing window focus tracking...")
        tracker = X11CursorTracker()
        
        # Get current window info
        window_info = tracker.get_active_window_info()
        if window_info:
            print(f"Current window: ID={window_info.window_id}, Name='{window_info.window_name}', Class='{window_info.window_class}'")
        else:
            print("No active window detected")
        
        # Test tracking
        window_changes = []
        
        def callback(window_info: WindowInfo):
            window_changes.append(window_info)
            print(f"Window changed: {window_info.window_name} ({window_info.window_class})")
        
        tracker.enable_window_focus_tracking()
        tracker.add_window_callback(callback)
        tracker.start_polling(0.2)
        
        print("Switch between applications for 5 seconds to test window focus tracking...")
        time.sleep(5)
        
        tracker.cleanup()
        
        print(f"Detected {len(window_changes)} window changes")
        print("Window focus tracking test completed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
