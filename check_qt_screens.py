#!/usr/bin/env python3
"""
Simple script to check Qt screen detection and configuration.
"""
import sys
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt

def main():
    app = QApplication(sys.argv)
    
    # Create main window
    window = QWidget()
    window.setWindowTitle("Qt Screen Check")
    window.setGeometry(100, 100, 600, 400)
    
    layout = QVBoxLayout()
    
    # Get screen information
    screens = app.screens()
    screens_label = QLabel(f"Number of screens detected: {len(screens)}")
    layout.addWidget(screens_label)
    
    # Display info for each screen
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        screen_info = QLabel(
            f"Screen {i} ({screen.name()}):\n"
            f"  Size: {geom.width()}x{geom.height()}\n"
            f"  Position: {geom.x()}, {geom.y()}\n"
            f"  Available: {screen.availableGeometry().width()}x{screen.availableGeometry().height()}"
        )
        screen_info.setStyleSheet("border: 1px solid #ccc; padding: 5px;")
        layout.addWidget(screen_info)
    
    # Add a button to refresh the info
    refresh_btn = QPushButton("Refresh")
    refresh_btn.clicked.connect(window.close)
    layout.addWidget(refresh_btn)
    
    window.setLayout(layout)
    window.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
