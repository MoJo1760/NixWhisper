#!/usr/bin/env python3
"""
Test to identify and fix the cursor positioning issue.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout
from PyQt6.QtGui import QCursor, QColor
from PyQt6.QtCore import Qt, QTimer
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position
import time

def test_positioning_logic():
    """Test the positioning logic step by step."""
    app = QApplication(sys.argv)
    
    print("=== Cursor Positioning Logic Test ===")
    
    # Create overlay
    overlay = OverlayWindow()
    overlay.resize(200, 60)
    overlay.setStyleSheet("""
        background-color: rgba(0, 255, 0, 200);
        border: 2px solid white;
        border-radius: 10px;
        color: black;
        font-weight: bold;
        padding: 5px;
    """)
    
    layout = QVBoxLayout(overlay)
    label = QLabel("Test Overlay")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    
    overlay.show()
    
    print("✓ Overlay created and shown")
    
    # Test 1: Default positioning (should be center)
    print("\n--- Test 1: Default Positioning ---")
    time.sleep(1)
    app.processEvents()
    
    pos = overlay.pos()
    print(f"Default position: ({pos.x()}, {pos.y()})")
    
    # Test 2: Enable cursor positioning
    print("\n--- Test 2: Enable Cursor Positioning ---")
    overlay.enable_cursor_relative_positioning(True)
    overlay.set_cursor_offset(60, 60)  # Large offset for visibility
    print("✓ Cursor positioning enabled with 60x60 offset")
    
    # Wait and check position updates
    for i in range(5):
        time.sleep(0.5)
        app.processEvents()
        
        cursor_qt = QCursor.pos()
        overlay_pos = overlay.pos()
        cursor_tracked = get_cursor_position(include_screen_info=True)
        
        print(f"Update {i+1}:")
        print(f"  Qt Cursor: ({cursor_qt.x()}, {cursor_qt.y()})")
        print(f"  Overlay: ({overlay_pos.x()}, {overlay_pos.y()})")
        
        if cursor_tracked:
            abs_x = cursor_tracked.screen_x + cursor_tracked.x
            abs_y = cursor_tracked.screen_y + cursor_tracked.y
            expected_x = abs_x + 60
            expected_y = abs_y + 60
            distance = ((overlay_pos.x() - expected_x) ** 2 + (overlay_pos.y() - expected_y) ** 2) ** 0.5
            
            print(f"  Tracked: abs=({abs_x}, {abs_y}) screen={cursor_tracked.screen_number}")
            print(f"  Expected overlay: ({expected_x}, {expected_y})")
            print(f"  Distance from expected: {distance:.1f}px")
            
            if distance < 20:
                print(f"  ✅ GOOD: Positioning is accurate")
            else:
                print(f"  ❌ ISSUE: Large distance from expected position")
        else:
            print(f"  ❌ TRACKING FAILED")
        print()
    
    # Test 3: Visual connection
    print("\n--- Test 3: Visual Connection ---")
    overlay.set_cursor_connection_enabled(True)
    overlay.set_cursor_connection_style('arrow')
    overlay.set_cursor_connection_color(QColor(255, 0, 0, 255))  # Bright red
    print("✓ Visual connection enabled")
    
    # Final check
    time.sleep(2)
    app.processEvents()
    
    settings = overlay.get_cursor_connection_settings()
    print(f"Final connection settings: {settings}")
    
    print("\n--- Test Results ---")
    print("If you can see:")
    print("• Green overlay following your cursor with ~60px offset")
    print("• Red arrow pointing from overlay to cursor")
    print("• Overlay updating position as you move cursor")
    print("Then the positioning is working correctly!")
    
    # Keep running for manual verification
    print("\nKeeping overlay active for 10 seconds for manual verification...")
    start_time = time.time()
    while time.time() - start_time < 10:
        app.processEvents()
        time.sleep(0.1)
    
    overlay.close()
    print("✓ Test completed")

if __name__ == "__main__":
    test_positioning_logic()