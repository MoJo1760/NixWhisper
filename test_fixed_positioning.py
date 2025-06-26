#!/usr/bin/env python3
"""
Test the fixed positioning logic.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout
from PyQt6.QtGui import QCursor, QColor
from PyQt6.QtCore import Qt, QTimer
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position
import time

def test_fixed_positioning():
    """Test the positioning after the fix."""
    app = QApplication(sys.argv)
    
    print("=== Testing Fixed Positioning ===")
    
    # Create overlay
    overlay = OverlayWindow()
    overlay.resize(150, 50)
    overlay.setStyleSheet("""
        background-color: rgba(255, 165, 0, 220);
        border: 2px solid red;
        border-radius: 8px;
        color: white;
        font-weight: bold;
        padding: 5px;
    """)
    
    layout = QVBoxLayout(overlay)
    label = QLabel("Fixed Test")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    
    overlay.show()
    
    # Enable cursor positioning with a clear offset
    overlay.enable_cursor_relative_positioning(True)
    overlay.set_cursor_offset(80, 80)  # Large offset for visibility
    
    # Add visual connection
    overlay.set_cursor_connection_enabled(True)
    overlay.set_cursor_connection_style('arrow')
    overlay.set_cursor_connection_color(QColor(255, 255, 0, 255))  # Yellow arrow
    
    print("✓ Overlay configured with:")
    print("  - 80x80 pixel offset from cursor")
    print("  - Orange background with red border") 
    print("  - Yellow arrow pointing to cursor")
    print("  - Fixed boundary checking")
    
    # Test positioning accuracy
    print("\n--- Testing Positioning Accuracy ---")
    
    for i in range(3):
        time.sleep(1)
        app.processEvents()
        
        cursor_qt = QCursor.pos()
        overlay_pos = overlay.pos()
        cursor_tracked = get_cursor_position(include_screen_info=True)
        
        if cursor_tracked:
            abs_x = cursor_tracked.screen_x + cursor_tracked.x
            abs_y = cursor_tracked.screen_y + cursor_tracked.y
            expected_x = abs_x + 80
            expected_y = abs_y + 80
            distance = ((overlay_pos.x() - expected_x) ** 2 + (overlay_pos.y() - expected_y) ** 2) ** 0.5
            
            print(f"Test {i+1}:")
            print(f"  Cursor: ({abs_x}, {abs_y})")
            print(f"  Expected: ({expected_x}, {expected_y})")
            print(f"  Actual: ({overlay_pos.x()}, {overlay_pos.y()})")
            print(f"  Distance: {distance:.1f}px")
            
            if distance < 30:  # Allow some tolerance
                print(f"  ✅ GOOD positioning")
            else:
                print(f"  ⚠ Position may still need adjustment")
        else:
            print(f"Test {i+1}: ❌ Tracking failed")
        print()
    
    print("Manual test time - move your cursor around for 8 seconds...")
    print("You should see:")
    print("• Orange overlay following cursor with 80px offset")
    print("• Overlay should NOT jump around aggressively")
    print("• Yellow arrow should point toward cursor")
    
    # Manual test period
    start_time = time.time()
    while time.time() - start_time < 8:
        app.processEvents()
        time.sleep(0.1)
    
    overlay.close()
    print("✓ Fixed positioning test completed!")

if __name__ == "__main__":
    test_fixed_positioning()