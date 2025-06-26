#!/usr/bin/env python3
"""
Focused test for overlay positioning across multiple monitors.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position
import time

def main():
    app = QApplication(sys.argv)
    
    screens = app.screens()
    print(f"=== Overlay Multimonitor Test ===")
    print(f"Detected {len(screens)} screens")
    
    # Display screen layout
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        is_primary = screen == app.primaryScreen()
        print(f"Screen {i}: {screen.name()} {geom.width()}x{geom.height()}+{geom.x()}+{geom.y()} {'(PRIMARY)' if is_primary else ''}")
    
    print("\n=== Creating Test Overlay ===")
    
    # Create overlay
    overlay = OverlayWindow()
    overlay.resize(300, 100)
    overlay.setStyleSheet("""
        background-color: rgba(255, 100, 50, 220);
        border: 3px solid white;
        border-radius: 15px;
        color: white;
        font-weight: bold;
        font-size: 16px;
        padding: 15px;
    """)
    
    # Add content to overlay
    layout = QVBoxLayout(overlay)
    title_label = QLabel("🎯 NixWhisper Test Overlay")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_label)
    
    position_label = QLabel("Position tracking...")
    position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(position_label)
    
    overlay.show()
    print("✓ Overlay created and shown")
    
    # Enable cursor positioning
    overlay.enable_cursor_relative_positioning(True)
    print("✓ Cursor-relative positioning enabled")
    
    # Set cursor offset
    overlay.set_cursor_offset(30, 30)
    print("✓ Cursor offset set to (30, 30)")
    
    print("\n=== Testing Each Screen ===")
    
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        screen_name = screen.name()
        
        print(f"\n--- Screen {i}: {screen_name} ---")
        print(f"Geometry: {geom.width()}x{geom.height()}+{geom.x()}+{geom.y()}")
        
        # Test multiple positions on this screen
        test_positions = [
            ("center", geom.x() + geom.width() // 2, geom.y() + geom.height() // 2),
            ("top-left", geom.x() + 100, geom.y() + 100),
            ("top-right", geom.x() + geom.width() - 100, geom.y() + 100),
            ("bottom-left", geom.x() + 100, geom.y() + geom.height() - 100),
            ("bottom-right", geom.x() + geom.width() - 100, geom.y() + geom.height() - 100),
        ]
        
        for pos_name, target_x, target_y in test_positions:
            print(f"\n  Testing {pos_name}: moving cursor to ({target_x}, {target_y})")
            
            # Move cursor
            QCursor.setPos(target_x, target_y)
            time.sleep(0.4)  # Give time for tracking
            app.processEvents()
            
            # Check actual cursor position
            actual_cursor = QCursor.pos()
            print(f"    Cursor moved to: ({actual_cursor.x()}, {actual_cursor.y()})")
            
            # Check our tracking
            tracked_pos = get_cursor_position(include_screen_info=True)
            if tracked_pos:
                abs_x = tracked_pos.screen_x + tracked_pos.x
                abs_y = tracked_pos.screen_y + tracked_pos.y
                print(f"    Tracked: rel=({tracked_pos.x}, {tracked_pos.y}) "
                      f"abs=({abs_x}, {abs_y}) screen={tracked_pos.screen_number}")
                
                # Check overlay position
                overlay_pos = overlay.pos()
                overlay_size = overlay.size()
                expected_x = actual_cursor.x() + 30
                expected_y = actual_cursor.y() + 30
                
                print(f"    Overlay: pos=({overlay_pos.x()}, {overlay_pos.y()}) "
                      f"size=({overlay_size.width()}x{overlay_size.height()})")
                print(f"    Expected: ≈({expected_x}, {expected_y})")
                
                # Check which screen the overlay is on
                overlay_screen = -1
                for j, check_screen in enumerate(screens):
                    if check_screen.geometry().contains(overlay_pos.x(), overlay_pos.y()):
                        overlay_screen = j
                        break
                
                # Determine if positioning is correct
                distance = ((overlay_pos.x() - expected_x) ** 2 + (overlay_pos.y() - expected_y) ** 2) ** 0.5
                
                if overlay_screen == i:
                    if distance < 100:  # Within reasonable tolerance
                        print(f"    ✓ PASS: Overlay correctly positioned on screen {i} (distance: {distance:.1f}px)")
                    else:
                        print(f"    ⚠ WARN: Overlay on correct screen {i} but position off by {distance:.1f}px")
                else:
                    print(f"    ❌ FAIL: Overlay on wrong screen {overlay_screen}, expected screen {i}")
                
            else:
                print(f"    ❌ ERROR: Failed to get tracked cursor position")
            
            time.sleep(0.3)  # Brief pause between positions
        
        time.sleep(1.0)  # Longer pause between screens
    
    print(f"\n=== Edge Boundary Test ===")
    
    # Test positioning near screen edges to check bounds handling
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        
        print(f"\nTesting screen {i} edges:")
        
        # Test very close to edges (should reposition overlay to stay on screen)
        edge_tests = [
            ("right-edge", geom.right() - 20, geom.y() + geom.height() // 2),
            ("bottom-edge", geom.x() + geom.width() // 2, geom.bottom() - 20),
            ("right-bottom", geom.right() - 20, geom.bottom() - 20),
        ]
        
        for edge_name, x, y in edge_tests:
            print(f"  {edge_name}: cursor at ({x}, {y})")
            
            QCursor.setPos(x, y)
            time.sleep(0.4)
            app.processEvents()
            
            overlay_pos = overlay.pos()
            overlay_size = overlay.size()
            
            # Check if overlay stayed within screen bounds
            screen_right = geom.x() + geom.width()
            screen_bottom = geom.y() + geom.height()
            overlay_right = overlay_pos.x() + overlay_size.width()
            overlay_bottom = overlay_pos.y() + overlay_size.height()
            
            within_bounds = (overlay_pos.x() >= geom.x() and overlay_pos.y() >= geom.y() and 
                           overlay_right <= screen_right and overlay_bottom <= screen_bottom)
            
            if within_bounds:
                print(f"    ✓ Overlay stayed within screen bounds: ({overlay_pos.x()}, {overlay_pos.y()})")
            else:
                print(f"    ❌ Overlay outside bounds: pos=({overlay_pos.x()}, {overlay_pos.y()}) "
                      f"size=({overlay_size.width()}x{overlay_size.height()}) "
                      f"right={overlay_right} bottom={overlay_bottom}")
    
    print(f"\n=== Test Complete ===")
    print("Press Ctrl+C to exit...")
    
    try:
        # Keep running so user can manually test
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        overlay.close()

if __name__ == "__main__":
    main()