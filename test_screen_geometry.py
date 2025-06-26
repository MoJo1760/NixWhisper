#!/usr/bin/env python3
"""
Simple test to verify screen geometry detection and cursor positioning across screens.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QCursor
from nixwhisper.x11_cursor import get_cursor_position
import time

def main():
    app = QApplication(sys.argv)
    
    screens = app.screens()
    print(f"=== Screen Geometry Test ===")
    print(f"Detected {len(screens)} screens:\n")
    
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        avail = screen.availableGeometry()
        is_primary = screen == app.primaryScreen()
        
        print(f"Screen {i}: {screen.name()}")
        print(f"  Geometry: {geom.width()}x{geom.height()}+{geom.x()}+{geom.y()}")
        print(f"  Available: {avail.width()}x{avail.height()}+{avail.x()}+{avail.y()}")
        print(f"  DPI: {screen.physicalDotsPerInch():.1f}")
        print(f"  Primary: {is_primary}")
        print()
    
    print("=== Cursor Movement Test ===")
    print("Testing cursor movement to each screen center...\n")
    
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        center_x = geom.x() + geom.width() // 2
        center_y = geom.y() + geom.height() // 2
        
        print(f"Screen {i} ({screen.name()}):")
        print(f"  Target center: ({center_x}, {center_y})")
        
        # Move cursor to screen center
        QCursor.setPos(center_x, center_y)
        time.sleep(0.2)
        
        # Verify actual position
        actual_pos = QCursor.pos()
        print(f"  Actual cursor: ({actual_pos.x()}, {actual_pos.y()})")
        
        # Get position through our tracking system
        tracked_pos = get_cursor_position(include_screen_info=True)
        if tracked_pos:
            abs_x = tracked_pos.screen_x + tracked_pos.x
            abs_y = tracked_pos.screen_y + tracked_pos.y
            print(f"  Tracked pos: rel=({tracked_pos.x}, {tracked_pos.y}) "
                  f"abs=({abs_x}, {abs_y}) screen={tracked_pos.screen_number}")
            print(f"  Screen info: {tracked_pos.screen_width}x{tracked_pos.screen_height}"
                  f"+{tracked_pos.screen_x}+{tracked_pos.screen_y}")
            
            # Verify the screen detection is correct
            if tracked_pos.screen_number == i:
                print(f"  ✓ Screen detection correct")
            else:
                print(f"  ❌ Screen detection incorrect: expected {i}, got {tracked_pos.screen_number}")
        else:
            print(f"  ❌ Failed to get tracked position")
        
        print()
        time.sleep(1)
    
    print("=== Edge Case Test ===")
    print("Testing edge positions and screen boundaries...\n")
    
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        
        # Test near edges (10 pixels from edge)
        edge_positions = [
            ("top-left", geom.x() + 10, geom.y() + 10),
            ("top-right", geom.x() + geom.width() - 10, geom.y() + 10),
            ("bottom-left", geom.x() + 10, geom.y() + geom.height() - 10),
            ("bottom-right", geom.x() + geom.width() - 10, geom.y() + geom.height() - 10),
        ]
        
        print(f"Screen {i} edge tests:")
        
        for edge_name, x, y in edge_positions:
            QCursor.setPos(x, y)
            time.sleep(0.1)
            
            tracked_pos = get_cursor_position(include_screen_info=True)
            if tracked_pos:
                print(f"  {edge_name}: screen={tracked_pos.screen_number} "
                      f"rel=({tracked_pos.x}, {tracked_pos.y})")
            else:
                print(f"  {edge_name}: ❌ tracking failed")
        
        print()
        time.sleep(0.5)
    
    print("Test completed!")

if __name__ == "__main__":
    main()