"""Tests for OverlayWindow cursor-relative positioning functionality."""

import pytest
import sys
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QGuiApplication

# Import the OverlayWindow class
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import X11_AVAILABLE

# Skip tests if X11 is not available
pytestmark = pytest.mark.skipif(not X11_AVAILABLE, reason="X11 not available")

# Ensure QApplication exists for Qt tests
@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication instance for testing."""
    if not QApplication.instance():
        app = QApplication(sys.argv)
        yield app
        app.quit()
    else:
        yield QApplication.instance()


class TestOverlayCursorPositioning:
    """Test cases for OverlayWindow cursor-relative positioning functionality."""

    def test_overlay_window_initialization(self, qapp):
        """Test that OverlayWindow initializes with cursor positioning properties."""
        overlay = OverlayWindow()
        
        try:
            # Check default cursor positioning properties
            assert hasattr(overlay, 'cursor_relative_positioning')
            assert hasattr(overlay, 'cursor_offset_x')
            assert hasattr(overlay, 'cursor_offset_y')
            assert hasattr(overlay, 'last_cursor_position')
            
            # Check default values
            assert overlay.cursor_relative_positioning is False
            assert overlay.cursor_offset_x == 20
            assert overlay.cursor_offset_y == 20
            assert overlay.last_cursor_position is None
            
        finally:
            overlay.close()

    def test_enable_cursor_relative_positioning(self, qapp):
        """Test enabling and disabling cursor-relative positioning."""
        overlay = OverlayWindow()
        
        try:
            # Initially disabled
            assert overlay.cursor_relative_positioning is False
            
            # Enable cursor-relative positioning
            overlay.enable_cursor_relative_positioning(True)
            assert overlay.cursor_relative_positioning is True
            
            # Disable cursor-relative positioning
            overlay.enable_cursor_relative_positioning(False)
            assert overlay.cursor_relative_positioning is False
            
        finally:
            overlay.close()

    def test_set_cursor_offset(self, qapp):
        """Test setting cursor offset values."""
        overlay = OverlayWindow()
        
        try:
            # Set custom offset values
            overlay.set_cursor_offset(30, 40)
            assert overlay.cursor_offset_x == 30
            assert overlay.cursor_offset_y == 40
            
            # Set different values
            overlay.set_cursor_offset(10, 15)
            assert overlay.cursor_offset_x == 10
            assert overlay.cursor_offset_y == 15
            
        finally:
            overlay.close()

    def test_get_cursor_relative_settings(self, qapp):
        """Test getting cursor-relative positioning settings."""
        overlay = OverlayWindow()
        
        try:
            # Get default settings
            settings = overlay.get_cursor_relative_settings()
            
            assert isinstance(settings, dict)
            assert 'enabled' in settings
            assert 'offset_x' in settings
            assert 'offset_y' in settings
            assert 'last_cursor_position' in settings
            
            assert settings['enabled'] is False
            assert settings['offset_x'] == 20
            assert settings['offset_y'] == 20
            assert settings['last_cursor_position'] is None
            
            # Change settings and verify
            overlay.enable_cursor_relative_positioning(True)
            overlay.set_cursor_offset(25, 35)
            
            updated_settings = overlay.get_cursor_relative_settings()
            assert updated_settings['enabled'] is True
            assert updated_settings['offset_x'] == 25
            assert updated_settings['offset_y'] == 35
            
        finally:
            overlay.close()

    @patch('nixwhisper.qt_gui.get_cursor_position')
    @patch('nixwhisper.qt_gui.QGuiApplication.primaryScreen')
    def test_cursor_relative_positioning_logic(self, mock_screen, mock_get_cursor_position, qapp):
        """Test cursor-relative positioning logic."""
        overlay = OverlayWindow()
        
        try:
            # Mock screen geometry
            mock_screen_geometry = QRect(0, 0, 1920, 1080)
            mock_screen_obj = MagicMock()
            mock_screen_obj.availableGeometry.return_value = mock_screen_geometry
            mock_screen.return_value = mock_screen_obj
            
            # Mock cursor position
            mock_get_cursor_position.return_value = (500, 300)
            
            # Enable cursor-relative positioning
            overlay.enable_cursor_relative_positioning(True)
            overlay.set_cursor_offset(20, 30)
            
            # Set overlay size for testing
            overlay.resize(200, 100)
            
            # Update position
            overlay.update_position()
            
            # Verify position was set correctly
            expected_x = 500 + 20  # cursor_x + offset_x
            expected_y = 300 + 30  # cursor_y + offset_y
            
            assert overlay.x() == expected_x
            assert overlay.y() == expected_y
            assert overlay.last_cursor_position == (500, 300)
            
        finally:
            overlay.close()

    @patch('nixwhisper.qt_gui.get_cursor_position')
    @patch('nixwhisper.qt_gui.QGuiApplication.primaryScreen')
    def test_bounds_checking(self, mock_screen, mock_get_cursor_position, qapp):
        """Test that overlay stays within screen bounds."""
        overlay = OverlayWindow()
        
        try:
            # Mock screen geometry (smaller screen for testing bounds)
            mock_screen_geometry = QRect(0, 0, 800, 600)
            mock_screen_obj = MagicMock()
            mock_screen_obj.availableGeometry.return_value = mock_screen_geometry
            mock_screen.return_value = mock_screen_obj
            
            # Set overlay size
            overlay.resize(200, 100)
            
            # Enable cursor-relative positioning
            overlay.enable_cursor_relative_positioning(True)
            overlay.set_cursor_offset(20, 20)
            
            # Test cursor near right edge
            mock_get_cursor_position.return_value = (750, 300)
            overlay.update_position()
            
            # Should be clamped to keep window on screen
            assert overlay.x() <= 800 - 200  # screen_width - window_width
            
            # Test cursor near bottom edge
            mock_get_cursor_position.return_value = (400, 550)
            overlay.update_position()
            
            # Should be clamped to keep window on screen
            assert overlay.y() <= 600 - 100  # screen_height - window_height
            
            # Test cursor near left edge
            mock_get_cursor_position.return_value = (-10, 300)
            overlay.update_position()
            
            # Should be clamped to left edge
            assert overlay.x() >= 0
            
            # Test cursor near top edge
            mock_get_cursor_position.return_value = (400, -10)
            overlay.update_position()
            
            # Should be clamped to top edge
            assert overlay.y() >= 0
            
        finally:
            overlay.close()

    @patch('nixwhisper.qt_gui.get_cursor_position')
    @patch('nixwhisper.qt_gui.QGuiApplication.primaryScreen')
    def test_fallback_to_center_positioning(self, mock_screen, mock_get_cursor_position, qapp):
        """Test fallback to center positioning when cursor position is unavailable."""
        overlay = OverlayWindow()
        
        try:
            # Mock screen geometry
            mock_screen_geometry = QRect(0, 0, 1920, 1080)
            mock_screen_obj = MagicMock()
            mock_screen_obj.availableGeometry.return_value = mock_screen_geometry
            mock_screen.return_value = mock_screen_obj
            
            # Mock cursor position as None (unavailable)
            mock_get_cursor_position.return_value = None
            
            # Enable cursor-relative positioning
            overlay.enable_cursor_relative_positioning(True)
            
            # Set overlay size
            overlay.resize(400, 80)
            
            # Update position - should fall back to center
            overlay.update_position()
            
            # Should be positioned at center-bottom
            expected_x = (1920 - 400) // 2
            expected_y = 1080 - 80 - 50
            
            assert overlay.x() == expected_x
            assert overlay.y() == expected_y
            
        finally:
            overlay.close()

    @patch('nixwhisper.qt_gui.QGuiApplication.primaryScreen')
    def test_center_positioning_when_disabled(self, mock_screen, qapp):
        """Test center positioning when cursor-relative positioning is disabled."""
        overlay = OverlayWindow()
        
        try:
            # Mock screen geometry
            mock_screen_geometry = QRect(0, 0, 1920, 1080)
            mock_screen_obj = MagicMock()
            mock_screen_obj.availableGeometry.return_value = mock_screen_geometry
            mock_screen.return_value = mock_screen_obj
            
            # Ensure cursor-relative positioning is disabled
            overlay.enable_cursor_relative_positioning(False)
            
            # Set overlay size
            overlay.resize(400, 80)
            
            # Update position
            overlay.update_position()
            
            # Should be positioned at center-bottom
            expected_x = (1920 - 400) // 2
            expected_y = 1080 - 80 - 50
            
            assert overlay.x() == expected_x
            assert overlay.y() == expected_y
            
        finally:
            overlay.close()

    def test_handle_screen_change(self, qapp):
        """Test handling screen configuration changes."""
        overlay = OverlayWindow()
        
        try:
            # This should not raise an exception
            overlay.handle_screen_change()
            
            # Enable cursor positioning and test again
            overlay.enable_cursor_relative_positioning(True)
            overlay.handle_screen_change()
            
        finally:
            overlay.close()


if __name__ == "__main__":
    # Manual test when run directly
    print("Running overlay cursor positioning tests...")
    
    if not X11_AVAILABLE:
        print("X11 not available, skipping tests")
        exit(0)
    
    try:
        # Create QApplication for testing
        app = QApplication(sys.argv)
        
        print("Testing overlay window with cursor positioning...")
        overlay = OverlayWindow()
        
        # Test basic functionality
        print("Testing cursor positioning enable/disable...")
        overlay.enable_cursor_relative_positioning(True)
        settings = overlay.get_cursor_relative_settings()
        print(f"Cursor positioning settings: {settings}")
        
        overlay.set_cursor_offset(30, 40)
        print(f"Updated offset to (30, 40)")
        
        settings = overlay.get_cursor_relative_settings()
        print(f"Updated settings: {settings}")
        
        overlay.close()
        
        print("Overlay cursor positioning test completed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
