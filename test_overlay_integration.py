#!/usr/bin/env python3
"""Integration test for OverlayWindow with cursor tracking."""

import sys
import time
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QPushButton, QLabel, QWidget, QCheckBox, QSpinBox, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from nixwhisper.qt_gui import OverlayWindow

class TestOverlayWindow(OverlayWindow):
    """Test overlay window with controls for testing cursor tracking."""
    
    def __init__(self, parent=None):
        # Initialize parent first
        super().__init__(parent)
        
        # Initialize cursor tracking attributes
        self.cursor_relative_positioning = True
        self.cursor_offset_x = 20
        self.cursor_offset_y = 20
        self.last_cursor_position = None
        
        # Now set up our window properties
        self.setWindowTitle("Test Overlay")
        self.setMinimumSize(300, 200)
        
        # Create a widget to hold controls
        self.control_widget = QWidget(self)
        self.control_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 220);
                border-radius: 10px;
                padding: 10px;
            }
            QLabel {
                color: white;
            }
        """)
        
        layout = QVBoxLayout(self.control_widget)
        
        # Cursor relative positioning toggle
        self.cursor_relative_cb = QCheckBox("Cursor Relative Positioning")
        # Initialize based on current cursor tracking state
        self.cursor_relative_cb.setChecked(True)  # Default to enabled
        # Connect to our method that will handle the toggle
        self.cursor_relative_cb.toggled.connect(self.toggle_cursor_relative)
        layout.addWidget(self.cursor_relative_cb)
        
        # X offset control
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X Offset:"))
        self.x_offset = QSpinBox()
        self.x_offset.setRange(-1000, 1000)
        self.x_offset.setValue(self.cursor_offset_x)
        self.x_offset.valueChanged.connect(self.update_offsets)
        x_layout.addWidget(self.x_offset)
        layout.addLayout(x_layout)
        
        # Y offset control
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y Offset:"))
        self.y_offset = QSpinBox()
        self.y_offset.setRange(-1000, 1000)
        self.y_offset.setValue(self.cursor_offset_y)
        self.y_offset.valueChanged.connect(self.update_offsets)
        y_layout.addWidget(self.y_offset)
        layout.addLayout(y_layout)
        
        # Position info label
        self.position_label = QLabel("Position: Waiting for update...")
        layout.addWidget(self.position_label)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        # Position the control widget
        self.control_widget.setLayout(layout)
        self.control_widget.adjustSize()
        
        # Update position periodically
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position_info)
        self.timer.start(100)  # Update every 100ms
        
        # Initial position update
        self.update_position()
    
    def update_offsets(self):
        """Update cursor offset values from spinboxes."""
        self.cursor_offset_x = self.x_offset.value()
        self.cursor_offset_y = self.y_offset.value()
        self.update_position()
    
    def update_position_info(self):
        """Update the position information label."""
        try:
            cursor_pos = get_cursor_position(include_screen_info=True)
            if cursor_pos:
                x, y = self.x(), self.y()
                self.position_label.setText(
                    f"Window: ({x}, {y}), "
                    f"Cursor: ({cursor_pos.x}, {cursor_pos.y}), "
                    f"Screen: {getattr(cursor_pos, 'screen_number', 'N/A')}"
                )
                self.last_cursor_position = cursor_pos
            self.update_position()
        except Exception as e:
            print(f"Error updating position info: {e}")
    
    def toggle_cursor_relative(self, enabled):
        """Toggle cursor-relative positioning."""
        self.cursor_relative_positioning = enabled
        self.update_position()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create and show the test overlay
    overlay = TestOverlayWindow()
    overlay.show()
    
    # Position the overlay initially
    overlay.update_position()
    
    # Start the application
    sys.exit(app.exec())
