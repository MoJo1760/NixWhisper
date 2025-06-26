#!/usr/bin/env python3
"""Diagnostic tool for screen layout and cursor tracking."""

import sys
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QLabel, QPushButton, QComboBox, QHBoxLayout, QGroupBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QScreen, QGuiApplication

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScreenDiagnosticTool(QMainWindow):
    """Tool to diagnose screen layout and cursor tracking."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Layout Diagnostic Tool")
        self.setMinimumSize(600, 400)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Screen information section
        screen_group = QGroupBox("Screen Information")
        screen_layout = QVBoxLayout()
        
        self.screen_info = QLabel("Detecting screens...")
        self.screen_info.setStyleSheet("font-family: monospace;")
        self.screen_info.setWordWrap(True)
        screen_layout.addWidget(self.screen_info)
        
        # Cursor position section
        cursor_group = QGroupBox("Cursor Position")
        cursor_layout = QVBoxLayout()
        
        self.cursor_info = QLabel("Move cursor to see position...")
        self.cursor_info.setStyleSheet("font-family: monospace;")
        cursor_layout.addWidget(self.cursor_info)
        
        # Add sections to main layout
        screen_group.setLayout(screen_layout)
        cursor_group.setLayout(cursor_layout)
        
        layout.addWidget(screen_group)
        layout.addWidget(cursor_group)
        
        # Add a refresh button
        btn_refresh = QPushButton("Refresh Screen Info")
        btn_refresh.clicked.connect(self.update_screen_info)
        layout.addWidget(btn_refresh)
        
        # Set up timer for cursor position updates
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.update_cursor_position)
        self.cursor_timer.start(100)  # Update every 100ms
        
        # Initial update
        self.update_screen_info()
    
    def update_screen_info(self):
        """Update the display with current screen information."""
        screens = QGuiApplication.screens()
        primary_screen = QGuiApplication.primaryScreen()
        
        screen_text = []
        screen_text.append(f"Detected {len(screens)} screen(s):\n")
        
        for i, screen in enumerate(screens):
            geom = screen.geometry()
            is_primary = " (Primary)" if screen == primary_screen else ""
            
            screen_text.append(
                f"Screen {i}{is_primary}:"
                f"\n  Geometry: {geom.x()}, {geom.y()} {geom.width()}x{geom.height()}"
                f"\n  DPI: {screen.logicalDotsPerInch():.1f} (logical), {screen.physicalDotsPerInch():.1f} (physical)"
                f"\n  Pixel ratio: {screen.devicePixelRatio():.1f}"
                f"\n  Available geometry: {screen.availableGeometry().getCoords()}"
                f"\n  Virtual geometry: {screen.virtualGeometry().getCoords()}"
                f"\n  Name: {screen.name()}"
                f"\n  Model: {screen.model() if hasattr(screen, 'model') else 'N/A'}"
                f"\n  Manufacturer: {screen.manufacturer() if hasattr(screen, 'manufacturer') else 'N/A'}"
                f"\n  Serial number: {screen.serialNumber() if hasattr(screen, 'serialNumber') else 'N/A'}"
            )
        
        self.screen_info.setText("\n\n".join(screen_text))
    
    def update_cursor_position(self):
        """Update the cursor position display."""
        from PyQt6.QtGui import QCursor
        
        # Get global cursor position
        cursor_pos = QCursor.pos()
        # Find which screen contains the cursor
        screen = QGuiApplication.screenAt(cursor_pos)
        
        if screen:
            screen_geom = screen.geometry()
            rel_x = cursor_pos.x() - screen_geom.x()
            rel_y = cursor_pos.y() - screen_geom.y()
            
            # Check if cursor is within screen bounds
            on_screen = (0 <= rel_x < screen_geom.width() and 
                        0 <= rel_y < screen_geom.height())
            
            self.cursor_info.setText(
                f"Global position: ({cursor_pos.x()}, {cursor_pos.y()})\n"
                f"Screen: {screen.name()}\n"
                f"Screen position: ({rel_x}, {rel_y}) relative to screen\n"
                f"Screen geometry: {screen_geom.x()}, {screen_geom.y()} {screen_geom.width()}x{screen_geom.height()}\n"
                f"On screen: {on_screen}"
            )
            
            # Log any issues with cursor position
            if not on_screen:
                logger.warning(
                    f"Cursor at ({cursor_pos.x()}, {cursor_pos.y()}) "
                    f"not within screen {screen.name()} bounds: {screen_geom}"
                )
        else:
            self.cursor_info.setText(
                f"Global position: ({cursor_pos.x()}, {cursor_pos.y()})\n"
                "Not on any known screen!"
            )
            logger.error(
                f"Cursor at ({cursor_pos.x()}, {cursor_pos.y()}) "
                "not on any detected screen!"
            )

def main():
    """Run the diagnostic tool."""
    app = QApplication(sys.argv)
    
    # Log screen information at startup
    logger.info("Starting screen layout diagnostic tool")
    screens = QGuiApplication.screens()
    logger.info(f"Detected {len(screens)} screen(s)")
    
    for i, screen in enumerate(screens):
        geom = screen.geometry()
        logger.info(
            f"Screen {i} ({screen.name()}): {geom.width()}x{geom.height()} at ({geom.x()}, {geom.y()})"
        )
    
    # Create and show the main window
    window = ScreenDiagnosticTool()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
