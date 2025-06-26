#!/usr/bin/env python3
"""Live test script for cursor-relative positioning in NixWhisper OverlayWindow."""

import sys
import time
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QTimer, Qt

# Add the source directory to the path
sys.path.insert(0, 'src')

from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import X11_AVAILABLE, get_cursor_position

class CursorPositioningTestApp(QWidget):
    """Test application for cursor-relative positioning."""
    
    def __init__(self):
        super().__init__()
        self.overlay = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the test UI."""
        self.setWindowTitle("NixWhisper Cursor Positioning Test")
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Ready to test cursor positioning")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # X11 availability status
        x11_status = "X11 Available " if X11_AVAILABLE else "X11 Not Available "
        x11_label = QLabel(f"Status: {x11_status}")
        x11_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(x11_label)
        
        # Current cursor position
        self.cursor_label = QLabel("Cursor: (0, 0)")
        self.cursor_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.cursor_label)
        
        # Test buttons
        self.show_overlay_btn = QPushButton("Show Overlay (Center)")
        self.show_overlay_btn.clicked.connect(self.show_overlay_center)
        layout.addWidget(self.show_overlay_btn)
        
        self.show_cursor_btn = QPushButton("Show Overlay (Cursor-Relative)")
        self.show_cursor_btn.clicked.connect(self.show_overlay_cursor)
        layout.addWidget(self.show_cursor_btn)
        
        self.hide_overlay_btn = QPushButton("Hide Overlay")
        self.hide_overlay_btn.clicked.connect(self.hide_overlay)
        layout.addWidget(self.hide_overlay_btn)
        
        self.test_recording_btn = QPushButton("Test Recording Animation")
        self.test_recording_btn.clicked.connect(self.test_recording)
        layout.addWidget(self.test_recording_btn)
        
        self.setLayout(layout)
        
        # Timer to update cursor position
        self.cursor_timer = QTimer()
        self.cursor_timer.timeout.connect(self.update_cursor_display)
        self.cursor_timer.start(100)  # Update every 100ms
        
    def update_cursor_display(self):
        """Update the cursor position display."""
        if X11_AVAILABLE:
            cursor_pos = get_cursor_position()
            if cursor_pos:
                x, y = cursor_pos
                self.cursor_label.setText(f"Cursor: ({x}, {y})")
            else:
                self.cursor_label.setText("Cursor: (unavailable)")
        else:
            self.cursor_label.setText("Cursor: (X11 not available)")
    
    def show_overlay_center(self):
        """Show overlay in center positioning mode."""
        if self.overlay:
            self.overlay.close()
        
        self.overlay = OverlayWindow()
        self.overlay.enable_cursor_relative_positioning(False)  # Center mode
        self.overlay.set_recording(False)
        
        # Check if status_label exists before trying to set it
        if hasattr(self.overlay, 'status_label'):
            self.overlay.status_label.setText("Center Positioning")
        
        self.overlay.show()
        self.overlay.update_position()
        
        self.status_label.setText("Overlay shown in center mode")
        
    def show_overlay_cursor(self):
        """Show overlay in cursor-relative positioning mode."""
        if not X11_AVAILABLE:
            self.status_label.setText("X11 not available - cannot use cursor positioning")
            return
            
        if self.overlay:
            self.overlay.close()
        
        self.overlay = OverlayWindow()
        self.overlay.enable_cursor_relative_positioning(True)  # Cursor-relative mode
        self.overlay.set_cursor_offset(30, 30)  # 30px offset from cursor
        self.overlay.set_recording(False)
        
        # Check if status_label exists before trying to set it
        if hasattr(self.overlay, 'status_label'):
            self.overlay.status_label.setText("Cursor-Relative Positioning")
        
        self.overlay.show()
        self.overlay.update_position()
        
        settings = self.overlay.get_cursor_relative_settings()
        self.status_label.setText(f"Overlay shown at cursor + ({settings['offset_x']}, {settings['offset_y']})")
        
    def hide_overlay(self):
        """Hide the overlay window."""
        if self.overlay:
            self.overlay.close()
            self.overlay = None
        self.status_label.setText("Overlay hidden")
        
    def test_recording(self):
        """Test recording animation with cursor positioning."""
        if not self.overlay:
            self.show_overlay_cursor()
            
        if self.overlay:
            self.overlay.set_recording(True)
            
            # Check if status_label exists before trying to set it
            if hasattr(self.overlay, 'status_label'):
                self.overlay.status_label.setText("Recording...")
            
            self.status_label.setText("Recording animation started")
            
            # Stop recording after 3 seconds
            QTimer.singleShot(3000, self.stop_recording)
    
    def stop_recording(self):
        """Stop recording animation."""
        if self.overlay:
            self.overlay.set_recording(False)
            
            # Check if status_label exists before trying to set it
            if hasattr(self.overlay, 'status_label'):
                self.overlay.status_label.setText("Ready")
            
            self.status_label.setText("Recording animation stopped")
    
    def closeEvent(self, event):
        """Clean up when closing."""
        if self.overlay:
            self.overlay.close()
        event.accept()


def main():
    """Main function to run the test application."""
    print("NixWhisper Cursor Positioning Live Test")
    print("=" * 40)
    
    if not X11_AVAILABLE:
        print("WARNING: X11 not available. Cursor positioning will not work.")
        print("You can still test center positioning mode.")
    else:
        print("X11 available. Full cursor positioning functionality enabled.")
    
    print("\nInstructions:")
    print("1. Click 'Show Overlay (Center)' to test traditional center positioning")
    print("2. Click 'Show Overlay (Cursor-Relative)' to test cursor positioning")
    print("3. Move your mouse around and click the cursor button again to see repositioning")
    print("4. Click 'Test Recording Animation' to see the recording indicator")
    print("5. Click 'Hide Overlay' to hide the overlay window")
    print("\nNote: The overlay will appear near your cursor when using cursor-relative mode.")
    
    app = QApplication(sys.argv)
    
    test_app = CursorPositioningTestApp()
    test_app.show()
    
    return app.exec()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
