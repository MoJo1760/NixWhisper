#!/usr/bin/env python3
"""
Simple positioning test that waits for the overlay to reach the correct position.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position
import time

def wait_for_overlay_position(overlay, target_screen, timeout=3.0):
    """Wait for overlay to be positioned on the target screen."""
    start_time = time.time()
    app = QApplication.instance()
    screens = app.screens()
    
    while time.time() - start_time < timeout:
        overlay_pos = overlay.pos()
        
        # Check which screen contains the overlay
        for i, screen in enumerate(screens):
            if screen.geometry().contains(overlay_pos.x(), overlay_pos.y()):
                if i == target_screen:
                    return True, overlay_pos
                break
        
        time.sleep(0.1)
        app.processEvents()
    
    return False, overlay.pos()

def main():
    app = QApplication(sys.argv)
    
    screens = app.screens()
    print(f"=== Simple Positioning Test ===")
    print(f"Detected {len(screens)} screens:")
    
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        is_primary = screen == app.primaryScreen()
        print(f"  Screen {i}: {screen.name()} {geom.width()}x{geom.height()}+{geom.x()}+{geom.y()} {'(PRIMARY)' if is_primary else ''}")
    
    print(f"\nCreating overlay...")
    overlay = OverlayWindow()
    overlay.resize(200, 60)
    overlay.setStyleSheet("""
        background-color: rgba(255, 100, 50, 220);
        border: 2px solid white;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        padding: 10px;
    """)
    
    layout = QVBoxLayout(overlay)
    label = QLabel("🎯 Simple Test")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    
    overlay.show()
    overlay.enable_cursor_relative_positioning(True)
    overlay.set_cursor_offset(30, 30)
    
    print("✓ Overlay created with cursor positioning enabled")
    
    # Test each screen individually
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        center_x = geom.x() + geom.width() // 2
        center_y = geom.y() + geom.height() // 2
        
        print(f"\n--- Testing Screen {i} ({screen.name()}) ---")
        print(f"Moving cursor to center: ({center_x}, {center_y})")
        
        # Move cursor
        QCursor.setPos(center_x, center_y)
        
        # Wait for overlay to position correctly
        positioned_correctly, final_pos = wait_for_overlay_position(overlay, i, timeout=2.0)
        
        # Get final cursor position
        actual_cursor = QCursor.pos()
        tracked_pos = get_cursor_position(include_screen_info=True)
        
        print(f"Cursor: target=({center_x}, {center_y}) actual=({actual_cursor.x()}, {actual_cursor.y()})")
        print(f"Overlay: final position=({final_pos.x()}, {final_pos.y()})")
        
        if tracked_pos:
            abs_x = tracked_pos.screen_x + tracked_pos.x
            abs_y = tracked_pos.screen_y + tracked_pos.y
            print(f"Tracking: rel=({tracked_pos.x}, {tracked_pos.y}) abs=({abs_x}, {abs_y}) screen={tracked_pos.screen_number}")
        
        if positioned_correctly:
            print(f"✅ SUCCESS: Overlay correctly positioned on screen {i}")
        else:
            print(f"❌ FAILED: Overlay not positioned on screen {i} within timeout")
        
        print()
        time.sleep(0.5)  # Brief pause between tests
    
    print("Closing overlay...")
    overlay.close()
    print("Test completed!")

if __name__ == "__main__":
    main()