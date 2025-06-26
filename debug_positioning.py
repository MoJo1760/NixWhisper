#!/usr/bin/env python3
"""
Debug cursor positioning with detailed logging.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout
from PyQt6.QtGui import QCursor, QColor
from PyQt6.QtCore import Qt, QTimer
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position
import time

class PositioningDebugger:
    """Debug cursor positioning issues."""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.overlay = None
        self.debug_timer = QTimer()
        self.debug_timer.timeout.connect(self.debug_positioning)
        
    def create_simple_overlay(self):
        """Create a simple overlay for debugging."""
        if self.overlay:
            self.overlay.close()
        
        self.overlay = OverlayWindow()
        self.overlay.resize(200, 80)
        
        # Very visible styling
        self.overlay.setStyleSheet("""
            background-color: rgba(255, 0, 0, 200);
            border: 2px solid white;
            border-radius: 10px;
            color: white;
            font-weight: bold;
            padding: 10px;
        """)
        
        layout = QVBoxLayout(self.overlay)
        self.debug_label = QLabel("Debug Overlay")
        self.debug_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.debug_label)
        
        # Show and configure
        self.overlay.show()
        
        print("✓ Simple overlay created")
        return self.overlay
    
    def debug_positioning(self):
        """Debug positioning in real-time."""
        if not self.overlay:
            return
            
        # Get cursor position
        cursor_qt = QCursor.pos()
        cursor_tracked = get_cursor_position(include_screen_info=True)
        overlay_pos = self.overlay.pos()
        
        print(f"\n--- Debug Info ---")
        print(f"Qt Cursor: ({cursor_qt.x()}, {cursor_qt.y()})")
        
        if cursor_tracked:
            abs_x = cursor_tracked.screen_x + cursor_tracked.x
            abs_y = cursor_tracked.screen_y + cursor_tracked.y
            print(f"Tracked: rel=({cursor_tracked.x}, {cursor_tracked.y}) abs=({abs_x}, {abs_y}) screen={cursor_tracked.screen_number}")
        else:
            print("Tracked: FAILED")
        
        print(f"Overlay: ({overlay_pos.x()}, {overlay_pos.y()})")
        
        # Calculate expected position
        if cursor_tracked:
            expected_x = abs_x + 50  # Default offset
            expected_y = abs_y + 50
            distance = ((overlay_pos.x() - expected_x) ** 2 + (overlay_pos.y() - expected_y) ** 2) ** 0.5
            print(f"Expected: ({expected_x}, {expected_y}) Distance: {distance:.1f}px")
        
        # Update label
        if cursor_tracked:
            self.debug_label.setText(f"Cursor: {abs_x}, {abs_y}\nOverlay: {overlay_pos.x()}, {overlay_pos.y()}")
        else:
            self.debug_label.setText("Tracking Failed")
    
    def test_manual_positioning(self):
        """Test manual positioning."""
        self.create_simple_overlay()
        
        print("\n=== Manual Positioning Test ===")
        print("Testing with cursor positioning DISABLED first...")
        
        # Test without cursor positioning
        self.overlay.enable_cursor_relative_positioning(False)
        print("✓ Cursor positioning disabled")
        
        input("Press Enter to enable cursor positioning...")
        
        # Enable cursor positioning
        print("\nEnabling cursor positioning...")
        self.overlay.enable_cursor_relative_positioning(True)
        self.overlay.set_cursor_offset(50, 50)
        print("✓ Cursor positioning enabled with 50x50 offset")
        
        # Start debug timer
        print("Starting debug timer...")
        self.debug_timer.start(1000)  # Every second
        
        input("Press Enter to add visual connection...")
        
        # Add visual connection
        print("Adding visual connection indicators...")
        self.overlay.set_cursor_connection_enabled(True)
        self.overlay.set_cursor_connection_style('arrow')
        self.overlay.set_cursor_connection_color(QColor(255, 255, 0, 255))  # Bright yellow
        self.overlay.set_cursor_connection_animated(True)
        print("✓ Visual connections enabled")
        
        input("Press Enter to stop...")
        
        self.debug_timer.stop()
        self.overlay.close()
        print("✓ Debug completed")

def main():
    """Main debugging function."""
    debugger = PositioningDebugger()
    debugger.test_manual_positioning()

if __name__ == "__main__":
    main()