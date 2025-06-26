#!/usr/bin/env python3
"""
Quick multimonitor test summary.
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
    print(f"=== NixWhisper Multimonitor Test Summary ===")
    print(f"Detected {len(screens)} screens:")
    
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        is_primary = screen == app.primaryScreen()
        print(f"  Screen {i}: {screen.name()} {geom.width()}x{geom.height()}+{geom.x()}+{geom.y()} {'(PRIMARY)' if is_primary else ''}")
    
    print(f"\nCreating test overlay...")
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
    label = QLabel("🎯 Test Overlay")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    
    overlay.show()
    overlay.enable_cursor_relative_positioning(True)
    overlay.set_cursor_offset(25, 25)
    
    print("✓ Overlay created with cursor positioning enabled")
    
    print(f"\nTesting each screen...")
    
    test_results = []
    
    # Test each screen individually
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        center_x = geom.x() + geom.width() // 2
        center_y = geom.y() + geom.height() // 2
        
        print(f"\nScreen {i} ({screen.name()}):")
        print(f"  Moving cursor to center: ({center_x}, {center_y})")
        
        QCursor.setPos(center_x, center_y)
        time.sleep(0.7)  # Wait for positioning
        app.processEvents()
        time.sleep(0.3)  # Additional wait for overlay positioning
        app.processEvents()
        
        # Get results immediately after positioning
        actual_cursor = QCursor.pos()
        overlay_pos = overlay.pos()
        tracked_pos = get_cursor_position(include_screen_info=True)
        
        print(f"  Debug: cursor expected=({center_x}, {center_y}) actual=({actual_cursor.x()}, {actual_cursor.y()})")
        print(f"  Debug: overlay at ({overlay_pos.x()}, {overlay_pos.y()})")
        if tracked_pos:
            abs_x = tracked_pos.screen_x + tracked_pos.x
            abs_y = tracked_pos.screen_y + tracked_pos.y
            print(f"  Debug: tracked rel=({tracked_pos.x}, {tracked_pos.y}) abs=({abs_x}, {abs_y}) screen={tracked_pos.screen_number}")
        
        # Determine which screen the overlay is on
        overlay_screen = -1
        for j, check_screen in enumerate(screens):
            if check_screen.geometry().contains(overlay_pos.x(), overlay_pos.y()):
                overlay_screen = j
                break
        
        # Check if positioning is within reasonable tolerance
        expected_overlay_x = center_x + 25  # cursor offset
        expected_overlay_y = center_y + 25
        position_tolerance = 100  # pixels
        
        cursor_matches = abs(actual_cursor.x() - center_x) < 5 and abs(actual_cursor.y() - center_y) < 5
        overlay_on_correct_screen = overlay_screen == i
        tracking_works = tracked_pos is not None and tracked_pos.screen_number == i
        position_reasonable = (abs(overlay_pos.x() - expected_overlay_x) < position_tolerance and 
                              abs(overlay_pos.y() - expected_overlay_y) < position_tolerance)
        
        result = {
            'screen': i,
            'cursor_moved': cursor_matches,
            'overlay_correct_screen': overlay_on_correct_screen,
            'tracking_works': tracking_works,
            'position_reasonable': position_reasonable,
            'cursor_pos': (actual_cursor.x(), actual_cursor.y()),
            'overlay_pos': (overlay_pos.x(), overlay_pos.y()),
            'overlay_screen': overlay_screen,
            'expected_overlay': (expected_overlay_x, expected_overlay_y)
        }
        
        test_results.append(result)
        
        print(f"  ✓ Cursor moved: {cursor_matches}")
        print(f"  ✓ Tracking works: {tracking_works}")
        print(f"  ✓ Overlay on correct screen: {overlay_on_correct_screen}")
        print(f"  ✓ Position reasonable: {position_reasonable}")
        print(f"  Cursor: ({actual_cursor.x()}, {actual_cursor.y()})")
        print(f"  Overlay: ({overlay_pos.x()}, {overlay_pos.y()}) expected≈({expected_overlay_x}, {expected_overlay_y}) on screen {overlay_screen}")
        
        # Add a pause before next test to let logs settle
        time.sleep(1.0)
    
    # Final summary
    print(f"\n=== Test Results Summary ===")
    
    all_passed = True
    for result in test_results:
        screen_passed = (result['cursor_moved'] and result['overlay_correct_screen'] and 
                        result['tracking_works'] and result['position_reasonable'])
        status = "✓ PASS" if screen_passed else "❌ FAIL"
        print(f"Screen {result['screen']}: {status}")
        if not screen_passed:
            all_passed = False
            # Show what failed
            failures = []
            if not result['cursor_moved']: failures.append("cursor_moved")
            if not result['overlay_correct_screen']: failures.append("overlay_screen")
            if not result['tracking_works']: failures.append("tracking")
            if not result['position_reasonable']: failures.append("position")
            print(f"  Failed: {', '.join(failures)}")
    
    if all_passed:
        print(f"\n🎉 ALL TESTS PASSED! Multimonitor cursor positioning is working correctly.")
    else:
        print(f"\n⚠️  Some tests failed. Check individual screen results above.")
    
    print(f"\nClosing overlay...")
    overlay.close()

if __name__ == "__main__":
    main()