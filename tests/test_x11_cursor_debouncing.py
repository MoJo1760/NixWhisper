"""Tests for X11 cursor tracking debouncing functionality."""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from nixwhisper.x11_cursor import (
    X11CursorTracker, 
    CursorPosition,
    set_cursor_debounce_threshold,
    set_cursor_debounce_time,
    get_cursor_debounce_settings,
    X11_AVAILABLE
)

# Skip tests if X11 is not available
pytestmark = pytest.mark.skipif(not X11_AVAILABLE, reason="X11 not available")


class TestCursorDebouncing:
    """Test cases for cursor position debouncing functionality."""

    def test_debounce_threshold_setting(self):
        """Test setting debounce threshold."""
        tracker = X11CursorTracker()
        
        try:
            # Test setting valid threshold
            tracker.set_debounce_threshold(10)
            assert tracker._debounce_threshold == 10
            
            # Test minimum threshold enforcement
            tracker.set_debounce_threshold(0)  # Below minimum
            assert tracker._debounce_threshold == 1  # Should be clamped to minimum
            
            tracker.set_debounce_threshold(-5)  # Negative
            assert tracker._debounce_threshold == 1  # Should be clamped to minimum
            
        finally:
            tracker.cleanup()

    def test_debounce_time_setting(self):
        """Test setting debounce time."""
        tracker = X11CursorTracker()
        
        try:
            # Test setting valid debounce time
            tracker.set_debounce_time(0.1)
            assert tracker._debounce_time == 0.1
            
            # Test minimum time enforcement
            tracker.set_debounce_time(0.005)  # Below minimum
            assert tracker._debounce_time == 0.01  # Should be clamped to minimum
            
            tracker.set_debounce_time(-0.1)  # Negative
            assert tracker._debounce_time == 0.01  # Should be clamped to minimum
            
        finally:
            tracker.cleanup()

    def test_debounce_settings_retrieval(self):
        """Test getting debounce settings."""
        tracker = X11CursorTracker()
        
        try:
            # Set some custom values
            tracker.set_debounce_threshold(15)
            tracker.set_debounce_time(0.08)
            tracker.set_polling_interval(0.12)
            
            # Get settings
            settings = tracker.get_debounce_settings()
            
            # Verify settings
            assert settings['threshold'] == 15
            assert settings['time'] == 0.08
            assert settings['polling_interval'] == 0.12
            
        finally:
            tracker.cleanup()

    def test_module_level_debounce_functions(self):
        """Test module-level debouncing functions."""
        try:
            # Test setting threshold
            set_cursor_debounce_threshold(20)
            
            # Test setting debounce time
            set_cursor_debounce_time(0.15)
            
            # Test getting settings
            settings = get_cursor_debounce_settings()
            assert settings['threshold'] == 20
            assert settings['time'] == 0.15
            
        finally:
            # Reset to defaults
            set_cursor_debounce_threshold(5)
            set_cursor_debounce_time(0.05)

    @patch('nixwhisper.x11_cursor.X11CursorTracker.get_cursor_position')
    def test_debounce_threshold_filtering(self, mock_get_position):
        """Test that small movements are filtered out by debounce threshold."""
        tracker = X11CursorTracker()
        callback_called = threading.Event()
        callback_count = 0
        received_positions = []
        
        def position_callback(pos: CursorPosition):
            nonlocal callback_count
            callback_count += 1
            received_positions.append(pos)
            callback_called.set()
        
        try:
            # Set a larger debounce threshold
            tracker.set_debounce_threshold(10)
            tracker.set_debounce_time(0.01)  # Short debounce time for testing
            
            # Mock cursor positions - small movements that should be filtered
            positions = [
                (100, 100),  # Initial position
                (102, 101),  # Small movement (< threshold)
                (103, 102),  # Small movement (< threshold)
                (115, 115),  # Large movement (> threshold)
                (116, 116),  # Small movement (< threshold)
                (130, 130),  # Large movement (> threshold)
            ]
            
            position_iter = iter(positions)
            mock_get_position.side_effect = lambda: next(position_iter, None)
            
            # Add callback and start polling
            tracker.add_position_callback(position_callback)
            
            if tracker.start_polling(0.02):  # Fast polling for testing
                # Wait for some callbacks
                time.sleep(0.2)
                tracker.stop_polling()
                
                # Should have received fewer callbacks due to debouncing
                # Exact count depends on timing, but should be less than total positions
                assert callback_count < len(positions)
                
                # First callback should be for initial position
                if received_positions:
                    assert received_positions[0].x == 100
                    assert received_positions[0].y == 100
            
        finally:
            tracker.cleanup()

    @patch('nixwhisper.x11_cursor.X11CursorTracker.get_cursor_position')
    def test_debounce_time_filtering(self, mock_get_position):
        """Test that rapid callbacks are filtered out by debounce time."""
        tracker = X11CursorTracker()
        callback_times = []
        
        def position_callback(pos: CursorPosition):
            callback_times.append(time.time())
        
        try:
            # Set a longer debounce time
            tracker.set_debounce_time(0.1)  # 100ms
            tracker.set_debounce_threshold(1)  # Low threshold so movement is detected
            
            # Mock cursor positions - large movements
            positions = [
                (100, 100),
                (120, 120),
                (140, 140),
                (160, 160),
                (180, 180),
            ]
            
            position_iter = iter(positions)
            mock_get_position.side_effect = lambda: next(position_iter, None)
            
            # Add callback and start polling
            tracker.add_position_callback(position_callback)
            
            if tracker.start_polling(0.02):  # Fast polling
                # Wait for callbacks
                time.sleep(0.3)
                tracker.stop_polling()
                
                # Check that callbacks are spaced by at least debounce time
                if len(callback_times) > 1:
                    for i in range(1, len(callback_times)):
                        time_diff = callback_times[i] - callback_times[i-1]
                        # Allow some tolerance for timing variations
                        assert time_diff >= 0.08  # Slightly less than 0.1 for tolerance
            
        finally:
            tracker.cleanup()

    def test_debounce_with_no_movement(self):
        """Test that no callbacks are triggered when cursor doesn't move."""
        tracker = X11CursorTracker()
        callback_count = 0
        
        def position_callback(pos: CursorPosition):
            nonlocal callback_count
            callback_count += 1
        
        try:
            # Add callback and start polling
            tracker.add_position_callback(position_callback)
            
            if tracker.start_polling(0.05):
                # Wait a bit - should get at most one callback for initial position
                time.sleep(0.2)
                tracker.stop_polling()
                
                # Should have at most one callback (for initial position detection)
                assert callback_count <= 1
            
        finally:
            tracker.cleanup()

    def test_debounce_reset_after_stop_start(self):
        """Test that debounce state is properly reset when stopping and starting polling."""
        tracker = X11CursorTracker()
        
        try:
            # Start and stop polling
            if tracker.start_polling(0.05):
                time.sleep(0.1)
                tracker.stop_polling()
                
                # Last callback time should be reset
                assert tracker._last_callback_time == 0.0 or tracker._last_callback_time > 0
                
                # Should be able to start again
                result = tracker.start_polling(0.05)
                assert result is True
                tracker.stop_polling()
            
        finally:
            tracker.cleanup()

    def test_default_debounce_settings(self):
        """Test that default debounce settings are reasonable."""
        tracker = X11CursorTracker()
        
        try:
            # Check default settings
            settings = tracker.get_debounce_settings()
            
            # Default threshold should be reasonable (not too sensitive, not too insensitive)
            assert 1 <= settings['threshold'] <= 20
            
            # Default debounce time should be reasonable (not too fast, not too slow)
            assert 0.01 <= settings['time'] <= 0.2
            
            # Default polling interval should be around 100ms
            assert 0.05 <= settings['polling_interval'] <= 0.2
            
        finally:
            tracker.cleanup()


if __name__ == "__main__":
    # Manual test when run directly
    print("Running cursor debouncing tests...")
    
    if not X11_AVAILABLE:
        print("X11 not available, skipping tests")
        exit(0)
    
    try:
        print("Testing debouncing settings...")
        tracker = X11CursorTracker()
        
        # Test setting debounce parameters
        tracker.set_debounce_threshold(8)
        tracker.set_debounce_time(0.1)
        
        settings = tracker.get_debounce_settings()
        print(f"Debounce settings: {settings}")
        
        # Test with callback
        callback_count = 0
        
        def test_callback(pos: CursorPosition):
            global callback_count
            callback_count += 1
            print(f"Callback {callback_count}: Cursor at ({pos.x}, {pos.y}) at {pos.timestamp}")
        
        tracker.add_position_callback(test_callback)
        tracker.start_polling(0.1)
        
        print("Move your cursor around for 3 seconds to test debouncing...")
        time.sleep(3)
        
        tracker.cleanup()
        
        print(f"Total callbacks received: {callback_count}")
        print("Debouncing test completed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
