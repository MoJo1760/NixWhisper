#!/usr/bin/env python3
"""Test overlay with improved multi-monitor support."""

import sys
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QLabel, QPushButton, QCheckBox, QHBoxLayout, QSpinBox)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect
from PyQt6.QtGui import QCursor, QGuiApplication, QScreen

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OverlayWindow(QMainWindow):
    """Overlay window that demonstrates multi-monitor cursor tracking."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Monitor Overlay Test")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Cursor tracking settings
        self.cursor_offset_x = 20
        self.cursor_offset_y = 20
        self.follow_cursor = True
        
        # Setup UI
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 200);
                border: 2px solid #4CAF50;
                border-radius: 8px;
                padding: 10px;
                color: white;
            }
            QLabel {
                color: white;
                font-family: monospace;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QSpinBox {
                background-color: white;
                color: black;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 2px;
            }
        """)
        
        layout = QVBoxLayout(self.central_widget)
        
        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Follow cursor checkbox
        self.follow_cb = QCheckBox("Follow Cursor")
        self.follow_cb.setChecked(self.follow_cursor)
        self.follow_cb.toggled.connect(self.toggle_follow_cursor)
        controls_layout.addWidget(self.follow_cb)
        
        # X offset
        controls_layout.addWidget(QLabel("X Offset:"))
        self.x_offset = QSpinBox()
        self.x_offset.setRange(-1000, 1000)
        self.x_offset.setValue(self.cursor_offset_x)
        self.x_offset.valueChanged.connect(self.update_offsets)
        controls_layout.addWidget(self.x_offset)
        
        # Y offset
        controls_layout.addWidget(QLabel("Y Offset:"))
        self.y_offset = QSpinBox()
        self.y_offset.setRange(-1000, 1000)
        self.y_offset.setValue(self.cursor_offset_y)
        self.y_offset.valueChanged.connect(self.update_offsets)
        controls_layout.addWidget(self.y_offset)
        
        layout.addLayout(controls_layout)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setCentralWidget(self.central_widget)
        
        # Set initial size
        self.resize(300, 150)
        
        # Setup timer for cursor tracking
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)  # ~60 FPS
        
        # Initial position update
        self.update_position()
    
    def toggle_follow_cursor(self, enabled):
        """Toggle whether the overlay follows the cursor."""
        self.follow_cursor = enabled
        if enabled:
            self.update_position()
    
    def update_offsets(self):
        """Update cursor offset values."""
        self.cursor_offset_x = self.x_offset.value()
        self.cursor_offset_y = self.y_offset.value()
        if self.follow_cursor:
            self.update_position()
    
    def update_position(self):
        """Update the overlay position based on cursor."""
        if not self.follow_cursor:
            return
            
        try:
            # Get cursor position and screen info
            cursor_pos = QCursor.pos()
            screen = QGuiApplication.screenAt(cursor_pos)
            
            if not screen:
                logger.warning("Could not determine screen for cursor position")
                return
                
            screen_geom = screen.geometry()
            
            # Calculate desired position with offset
            x = cursor_pos.x() + self.cursor_offset_x
            y = cursor_pos.y() + self.cursor_offset_y
            
            # Adjust to keep window on screen
            x = max(screen_geom.left(), min(x, screen_geom.right() - self.width()))
            y = max(screen_geom.top(), min(y, screen_geom.bottom() - self.height()))
            
            # Update window position
            self.move(int(x), int(y))
            
            # Update status
            self.status_label.setText(
                f"Screen: {screen.name()}\n"
                f"Cursor: ({cursor_pos.x()}, {cursor_pos.y()})\n"
                f"Window: ({x}, {y})\n"
                f"Screen Geometry: {screen_geom.x()}, {screen_geom.y()} "
                f"{screen_geom.width()}x{screen_geom.height()}"
            )
            
        except Exception as e:
            logger.error(f"Error updating position: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")

def main():
    """Run the test overlay."""
    app = QApplication(sys.argv)
    
    # Log screen information at startup
    screens = QGuiApplication.screens()
    logger.info(f"Detected {len(screens)} screen(s)")
    
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        logger.info(
            f"Screen {i} ({screen.name()}): {geom.width()}x{geom.height()} at ({geom.x()}, {geom.y()})"
        )
    
    # Create and show the overlay
    overlay = OverlayWindow()
    overlay.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
