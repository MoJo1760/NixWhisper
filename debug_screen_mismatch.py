#!/usr/bin/env python3
"""
Debug script to compare Qt and X11 screen detection.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QCursor
from nixwhisper.x11_cursor import get_cursor_position
import time

def main():
    app = QApplication(sys.argv)
    
    print("=== Screen Detection Comparison ===\n")
    
    # Get Qt screen information
    qt_screens = app.screens()
    print(f"Qt detected {len(qt_screens)} screens:")
    for i, screen in enumerate(qt_screens):
        geom = screen.geometry()
        print(f"  Qt Screen {i}: {geom.width()}x{geom.height()}+{geom.x()}+{geom.y()}")
    
    print()
    
    # Test current cursor position
    qt_cursor = QCursor.pos()
    print(f"Qt cursor position: ({qt_cursor.x()}, {qt_cursor.y()})")
    
    # Check which Qt screen contains cursor
    qt_cursor_screen = -1
    for i, screen in enumerate(qt_screens):
        if screen.geometry().contains(qt_cursor.x(), qt_cursor.y()):
            qt_cursor_screen = i
            break
    
    print(f"Qt cursor screen: {qt_cursor_screen}")
    
    # Get our tracking info
    tracked = get_cursor_position(include_screen_info=True)
    if tracked:
        abs_x = tracked.screen_x + tracked.x
        abs_y = tracked.screen_y + tracked.y
        print(f"Our tracking: rel=({tracked.x}, {tracked.y}) abs=({abs_x}, {abs_y}) screen={tracked.screen_number}")
        print(f"Our screen info: {tracked.screen_width}x{tracked.screen_height}+{tracked.screen_x}+{tracked.screen_y}")
        
        # Compare
        if abs_x == qt_cursor.x() and abs_y == qt_cursor.y():
            print("✓ Cursor positions match")
        else:
            print(f"❌ Cursor position mismatch: Qt=({qt_cursor.x()}, {qt_cursor.y()}) vs Our=({abs_x}, {abs_y})")
        
        if qt_cursor_screen == tracked.screen_number:
            print("✓ Screen detection matches")
        else:
            print(f"❌ Screen detection mismatch: Qt={qt_cursor_screen} vs Our={tracked.screen_number}")
    else:
        print("❌ Our tracking failed")
    
    print("\n=== Manual Position Test ===")
    print("Move your cursor to different screens and watch the output...")
    print("Press Ctrl+C to exit\n")
    
    try:
        while True:
            # Get current positions
            qt_pos = QCursor.pos()
            tracked_pos = get_cursor_position(include_screen_info=True)
            
            # Find Qt screen
            qt_screen = -1
            for i, screen in enumerate(qt_screens):
                if screen.geometry().contains(qt_pos.x(), qt_pos.y()):
                    qt_screen = i
                    break
            
            if tracked_pos:
                our_abs_x = tracked_pos.screen_x + tracked_pos.x
                our_abs_y = tracked_pos.screen_y + tracked_pos.y
                
                print(f"\rQt: ({qt_pos.x():4d},{qt_pos.y():4d}) screen={qt_screen} | "
                      f"Our: ({our_abs_x:4d},{our_abs_y:4d}) screen={tracked_pos.screen_number} | "
                      f"Match: {'✓' if qt_screen == tracked_pos.screen_number else '❌'}", end='', flush=True)
            else:
                print(f"\rQt: ({qt_pos.x():4d},{qt_pos.y():4d}) screen={qt_screen} | Our: FAILED", end='', flush=True)
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\nExiting...")

if __name__ == "__main__":
    main()