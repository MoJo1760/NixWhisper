#!/usr/bin/env python3
"""
Enhanced cursor positioning test with detailed logging and visualization.
"""
import sys
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel,
                           QPushButton, QCheckBox, QHBoxLayout, QGroupBox)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QScreen, QPainter, QColor, QPen, QFont

from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position, CursorPosition

class CursorTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cursor Positioning Test")
        self.setGeometry(100, 100, 600, 500)
        
        # Create overlay window
        self.overlay = OverlayWindow()
        self.overlay.resize(300, 100)
        self.overlay.setStyleSheet("""
            background-color: rgba(50, 100, 150, 200);
            border-radius: 10px;
            padding: 10px;
            color: white;
            font-weight: bold;
        """)
        
        # Setup UI
        self.setup_ui()
        
        # Start with cursor tracking enabled
        self.overlay.enable_cursor_relative_positioning(True)
        self.overlay.show()
        
        # Update display every 100ms
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_display)
        self.timer.start(100)
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Info group
        info_group = QGroupBox("Cursor & Screen Information")
        info_layout = QVBoxLayout()
        
        self.cursor_pos_label = QLabel("Cursor Position: ")
        self.screen_info_label = QLabel("Screen: ")
        self.window_pos_label = QLabel("Window Position: ")
        self.overlay_pos_label = QLabel("Overlay Position: ")
        
        # Use monospace font for better alignment
        font = QFont("Monospace")
        for label in [self.cursor_pos_label, self.screen_info_label, 
                     self.window_pos_label, self.overlay_pos_label]:
            label.setFont(font)
        
        info_layout.addWidget(self.cursor_pos_label)
        info_layout.addWidget(self.screen_info_label)
        info_layout.addWidget(self.window_pos_label)
        info_layout.addWidget(self.overlay_pos_label)
        info_group.setLayout(info_layout)
        
        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        
        # Cursor tracking toggle
        self.tracking_check = QCheckBox("Enable cursor tracking")
        self.tracking_check.setChecked(True)
        self.tracking_check.toggled.connect(
            lambda checked: self.overlay.enable_cursor_relative_positioning(checked)
        )
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Display Info")
        refresh_btn.clicked.connect(self.update_display)
        
        controls_layout.addWidget(self.tracking_check)
        controls_layout.addWidget(refresh_btn)
        controls_group.setLayout(controls_layout)
        
        # Add all groups to main layout
        layout.addWidget(info_group)
        layout.addWidget(controls_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
    
    def update_display(self):
        # Update cursor position info
        cursor_pos = get_cursor_position(include_screen_info=True)
        
        if cursor_pos:
            self.cursor_pos_label.setText(
                f"Cursor: ({cursor_pos.x:4d}, {cursor_pos.y:4d})  "
                f"Screen: {cursor_pos.screen_number}  "
                f"Global: ({cursor_pos.screen_x + cursor_pos.x:4d}, {cursor_pos.screen_y + cursor_pos.y:4d})"
            )
            
            self.screen_info_label.setText(
                f"Screen {cursor_pos.screen_number}: {cursor_pos.screen_width}x{cursor_pos.screen_height}  "
                f"at ({cursor_pos.screen_x}, {cursor_pos.screen_y})"
            )
        else:
            self.cursor_pos_label.setText("Cursor: Not available")
            self.screen_info_label.setText("Screen: Not available")
        
        # Update window positions
        self.window_pos_label.setText(
            f"This window: ({self.x()}, {self.y()})  "
            f"Size: {self.width()}x{self.height()}"
        )
        
        if hasattr(self.overlay, 'pos'):
            self.overlay_pos_label.setText(
                f"Overlay:   ({self.overlay.x()}, {self.overlay.y()})  "
                f"Size: {self.overlay.width()}x{self.overlay.height()}"
            )
        else:
            self.overlay_pos_label.setText("Overlay: Not available")

def main():
    app = QApplication(sys.argv)
    
    # Print screen info to console
    screens = app.screens()
    print(f"Detected {len(screens)} screen(s):")
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        print(
            f"  Screen {i} ({screen.name()}): {geom.width()}x{geom.height()} "
            f"at ({geom.x()}, {geom.y()})"
        )
    
    window = CursorTestWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
