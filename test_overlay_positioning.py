#!/usr/bin/env python3
"""
Test script to verify overlay window positioning with cursor tracking.
"""
import sys
import time
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor
from nixwhisper.x11_cursor import X11CursorTracker

class CursorOverlayTest(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cursor Overlay Test")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Set up the UI
        self.label = QLabel("Cursor Overlay Test")
        self.label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 14px;
        """)
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        # Set up cursor tracker
        self.cursor_tracker = X11CursorTracker()
        
        # Set up timer to update position
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_position)
        self.timer.start(50)  # 20 FPS update rate
        
        # Initial position
        self.update_position()
    
    def update_position(self):
        # Get cursor position with screen info
        cursor_pos = self.cursor_tracker.get_cursor_position()
        if cursor_pos:
            # Update position
            self.move(
                int(cursor_pos.screen_x + cursor_pos.x + 20),  # 20px offset from cursor
                int(cursor_pos.screen_y + cursor_pos.y + 20)
            )
            
            # Update label with position info
            self.label.setText(
                f"Cursor: ({cursor_pos.x:.0f}, {cursor_pos.y:.0f})\n"
                f"Screen: {cursor_pos.screen_number}\n"
                f"Screen Pos: ({cursor_pos.screen_x}, {cursor_pos.screen_y})\n"
                f"Screen Size: {cursor_pos.screen_width}x{cursor_pos.screen_height}"
            )
            
            # Make sure the window is shown and raised
            self.show()
            self.raise_()
    
    def closeEvent(self, event):
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Print screen info for debugging
    screens = app.screens()
    print(f"Detected {len(screens)} screen(s):")
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        print(f"  Screen {i} ({screen.name()}): {geom.width()}x{geom.height()} at ({geom.x()}, {geom.y()})")
    
    # Create and show the overlay
    overlay = CursorOverlayTest()
    overlay.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
