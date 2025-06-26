#!/usr/bin/env python3
"""Simple test for cursor tracking and overlay positioning."""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position

class CursorTracker(OverlayWindow):
    """Simple overlay that shows cursor position and follows it."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cursor Tracker")
        self.setMinimumSize(300, 100)
        
        # Setup UI
        self.label = QLabel("Waiting for cursor position...")
        self.label.setStyleSheet("color: white;")
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        
        # Add a close button
        btn = QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn)
        
        self.setLayout(layout)
        
        # Setup timer to update position
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_position_info)
        self.timer.start(100)  # Update every 100ms
        
        # Initial position update
        self.update_position_info()
    
    def update_position_info(self):
        """Update the display with current cursor and window positions."""
        try:
            # Get cursor position
            cursor_pos = get_cursor_position(include_screen_info=True)
            if not cursor_pos:
                self.label.setText("Error: Could not get cursor position")
                return
            
            # Update window position to follow cursor with offset
            x = cursor_pos.x + 20
            y = cursor_pos.y + 20
            self.move(x, y)
            
            # Update display
            self.label.setText(
                f"Cursor: ({cursor_pos.x}, {cursor_pos.y})\n"
                f"Window: ({x}, {y})\n"
                f"Screen: {getattr(cursor_pos, 'screen_number', 'N/A')}"
            )
            
        except Exception as e:
            self.label.setText(f"Error: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create and show the tracker window
    tracker = CursorTracker()
    tracker.show()
    
    # Position the window initially
    tracker.update_position_info()
    
    sys.exit(app.exec())
