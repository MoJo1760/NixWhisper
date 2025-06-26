#!/usr/bin/env python3
"""
Simple Qt test application to verify display connection.
"""
import sys
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

def main():
    print("Starting Qt application...")
    app = QApplication(sys.argv)
    
    print(f"QApplication instance created. Display: {app.primaryScreen().name()}")
    
    # Create a simple window
    window = QWidget()
    window.setWindowTitle("Qt Test")
    window.setGeometry(100, 100, 400, 200)
    
    layout = QVBoxLayout()
    label = QLabel("Qt is working!")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    
    screen_info = QLabel(
        f"Screen: {app.primaryScreen().name()}\n"
        f"Size: {app.primaryScreen().size().width()}x{app.primaryScreen().size().height()}"
    )
    screen_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(screen_info)
    
    window.setLayout(layout)
    window.show()
    
    print("Window shown. Starting event loop...")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
