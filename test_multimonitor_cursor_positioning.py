#!/usr/bin/env python3
"""
Comprehensive multimonitor test for cursor positioning and overlay dialog.

This script tests the cursor-positioned overlay dialog functionality across
multiple monitors, including edge cases and screen boundary handling.
"""

import sys
import time
import math
from typing import List, Dict, Optional, Tuple
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                           QLabel, QPushButton, QHBoxLayout, QGroupBox, 
                           QTextEdit, QScrollArea, QFrame, QCheckBox, QSpinBox)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect
from PyQt6.QtGui import QScreen, QPainter, QColor, QPen, QFont, QPixmap

# Add src to path so we can import nixwhisper modules
sys.path.insert(0, 'src')

from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_tracker, get_cursor_position, CursorPosition

class MultiMonitorTestWindow(QMainWindow):
    """Main test window for multimonitor cursor positioning tests."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NixWhisper Multimonitor Test Suite")
        self.setGeometry(100, 100, 800, 700)
        
        # Test state
        self.overlay = None
        self.cursor_tracker = get_cursor_tracker()
        self.test_log = []
        self.auto_test_timer = QTimer()
        self.auto_test_step = 0
        self.current_screen = 0
        
        # Screen information
        self.screens = QApplication.screens()
        self.screen_info = self._gather_screen_info()
        
        # Setup UI
        self.setup_ui()
        
        # Update display every 100ms
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)
        
        # Log initial screen configuration
        self.log_test_result("TEST_START", f"Detected {len(self.screens)} screens")
        for i, info in enumerate(self.screen_info):
            self.log_test_result("SCREEN_INFO", 
                               f"Screen {i}: {info['geometry']} DPI:{info['dpi']:.1f} "
                               f"Primary:{info['is_primary']} Name:{info['name']}")
    
    def setup_ui(self):
        """Setup the test interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Screen Information Group
        screen_group = QGroupBox("Screen Configuration")
        screen_layout = QVBoxLayout(screen_group)
        
        self.screen_info_label = QLabel()
        self.screen_info_label.setFont(QFont("monospace"))
        screen_layout.addWidget(self.screen_info_label)
        layout.addWidget(screen_group)
        
        # Current Status Group
        status_group = QGroupBox("Current Status")
        status_layout = QVBoxLayout(status_group)
        
        self.cursor_status_label = QLabel()
        self.cursor_status_label.setFont(QFont("monospace"))
        status_layout.addWidget(self.cursor_status_label)
        
        self.overlay_status_label = QLabel()
        self.overlay_status_label.setFont(QFont("monospace"))
        status_layout.addWidget(self.overlay_status_label)
        layout.addWidget(status_group)
        
        # Test Controls Group
        controls_group = QGroupBox("Test Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Manual test buttons
        button_layout = QHBoxLayout()
        
        self.create_overlay_btn = QPushButton("Create Test Overlay")
        self.create_overlay_btn.clicked.connect(self.create_test_overlay)
        button_layout.addWidget(self.create_overlay_btn)
        
        self.enable_cursor_btn = QPushButton("Enable Cursor Positioning")
        self.enable_cursor_btn.clicked.connect(self.enable_cursor_positioning)
        button_layout.addWidget(self.enable_cursor_btn)
        
        self.disable_cursor_btn = QPushButton("Disable Cursor Positioning")
        self.disable_cursor_btn.clicked.connect(self.disable_cursor_positioning)
        button_layout.addWidget(self.disable_cursor_btn)
        
        controls_layout.addLayout(button_layout)
        
        # Auto test controls
        auto_layout = QHBoxLayout()
        
        self.auto_test_btn = QPushButton("Run Automated Tests")
        self.auto_test_btn.clicked.connect(self.run_automated_tests)
        auto_layout.addWidget(self.auto_test_btn)
        
        self.test_all_screens_btn = QPushButton("Test All Screens")
        self.test_all_screens_btn.clicked.connect(self.test_all_screens)
        auto_layout.addWidget(self.test_all_screens_btn)
        
        self.test_edges_btn = QPushButton("Test Screen Edges")
        self.test_edges_btn.clicked.connect(self.test_screen_edges)
        auto_layout.addWidget(self.test_edges_btn)
        
        controls_layout.addLayout(auto_layout)
        
        # Configuration controls
        config_layout = QHBoxLayout()
        
        config_layout.addWidget(QLabel("Cursor Offset X:"))
        self.offset_x_spin = QSpinBox()
        self.offset_x_spin.setRange(-200, 200)
        self.offset_x_spin.setValue(20)
        self.offset_x_spin.valueChanged.connect(self.update_cursor_offset)
        config_layout.addWidget(self.offset_x_spin)
        
        config_layout.addWidget(QLabel("Y:"))
        self.offset_y_spin = QSpinBox()
        self.offset_y_spin.setRange(-200, 200)
        self.offset_y_spin.setValue(20)
        self.offset_y_spin.valueChanged.connect(self.update_cursor_offset)
        config_layout.addWidget(self.offset_y_spin)
        
        controls_layout.addLayout(config_layout)
        layout.addWidget(controls_group)
        
        # Test Log Group
        log_group = QGroupBox("Test Log")
        log_layout = QVBoxLayout(log_group)
        
        self.test_log_text = QTextEdit()
        self.test_log_text.setFont(QFont("monospace"))
        self.test_log_text.setMaximumHeight(200)
        log_layout.addWidget(self.test_log_text)
        
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.clear_test_log)
        log_layout.addWidget(clear_log_btn)
        
        layout.addWidget(log_group)
        
        # Update initial display
        self.update_screen_info_display()
    
    def _gather_screen_info(self) -> List[Dict]:
        """Gather detailed information about all screens."""
        info_list = []
        for i, screen in enumerate(self.screens):
            geometry = screen.geometry()
            info = {
                'index': i,
                'name': screen.name(),
                'geometry': f"{geometry.width()}x{geometry.height()}+{geometry.x()}+{geometry.y()}",
                'geometry_rect': geometry,
                'dpi': screen.physicalDotsPerInch(),
                'is_primary': screen == QApplication.primaryScreen(),
                'available_geometry': screen.availableGeometry(),
                'device_pixel_ratio': screen.devicePixelRatio()
            }
            info_list.append(info)
        return info_list
    
    def update_screen_info_display(self):
        """Update the screen information display."""
        info_text = f"Total Screens: {len(self.screens)}\n"
        for info in self.screen_info:
            primary_marker = " (PRIMARY)" if info['is_primary'] else ""
            info_text += (f"Screen {info['index']}: {info['geometry']} "
                         f"DPI:{info['dpi']:.1f} Ratio:{info['device_pixel_ratio']:.1f}"
                         f"{primary_marker}\n")
        self.screen_info_label.setText(info_text)
    
    def update_display(self):
        """Update the current status display."""
        # Get current cursor position
        cursor_pos = get_cursor_position(include_screen_info=True)
        if cursor_pos:
            cursor_text = (f"Cursor: x={cursor_pos.x}, y={cursor_pos.y} "
                          f"(abs: {cursor_pos.x + cursor_pos.screen_x}, "
                          f"{cursor_pos.y + cursor_pos.screen_y})\n"
                          f"Screen: {cursor_pos.screen_number} "
                          f"({cursor_pos.screen_width}x{cursor_pos.screen_height} "
                          f"+{cursor_pos.screen_x}+{cursor_pos.screen_y})")
        else:
            cursor_text = "Cursor: Unable to get position"
        
        self.cursor_status_label.setText(cursor_text)
        
        # Update overlay status
        if self.overlay:
            overlay_pos = self.overlay.pos()
            overlay_size = self.overlay.size()
            overlay_visible = self.overlay.isVisible()
            cursor_mode = getattr(self.overlay, 'cursor_relative_positioning', False)
            
            overlay_text = (f"Overlay: pos=({overlay_pos.x()}, {overlay_pos.y()}) "
                           f"size=({overlay_size.width()}x{overlay_size.height()}) "
                           f"visible={overlay_visible}\n"
                           f"Cursor positioning: {'ENABLED' if cursor_mode else 'DISABLED'}")
        else:
            overlay_text = "Overlay: Not created"
        
        self.overlay_status_label.setText(overlay_text)
    
    def create_test_overlay(self):
        """Create a test overlay window."""
        if self.overlay:
            self.overlay.close()
        
        self.overlay = OverlayWindow()
        self.overlay.resize(250, 80)
        
        # Style the overlay for better visibility
        self.overlay.setStyleSheet("""
            background-color: rgba(50, 150, 200, 220);
            border: 2px solid rgb(255, 255, 255);
            border-radius: 10px;
            color: white;
            font-weight: bold;
            font-size: 14px;
            padding: 10px;
        """)
        
        # Add test content
        layout = QVBoxLayout(self.overlay)
        title_label = QLabel("NixWhisper Test Overlay")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        pos_label = QLabel("Position tracking...")
        pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pos_label)
        
        self.overlay.show()
        self.log_test_result("OVERLAY_CREATED", "Test overlay window created and shown")
    
    def enable_cursor_positioning(self):
        """Enable cursor-relative positioning."""
        if not self.overlay:
            self.create_test_overlay()
        
        self.overlay.enable_cursor_relative_positioning(True)
        self.log_test_result("CURSOR_ENABLED", "Cursor-relative positioning enabled")
    
    def disable_cursor_positioning(self):
        """Disable cursor-relative positioning."""
        if self.overlay:
            self.overlay.enable_cursor_relative_positioning(False)
            self.log_test_result("CURSOR_DISABLED", "Cursor-relative positioning disabled")
    
    def update_cursor_offset(self):
        """Update cursor offset settings."""
        if self.overlay:
            x_offset = self.offset_x_spin.value()
            y_offset = self.offset_y_spin.value()
            self.overlay.set_cursor_offset(x_offset, y_offset)
            self.log_test_result("OFFSET_CHANGED", f"Cursor offset set to ({x_offset}, {y_offset})")
    
    def test_all_screens(self):
        """Test positioning on all screens."""
        if not self.overlay:
            self.create_test_overlay()
        
        self.enable_cursor_positioning()
        
        for i, info in enumerate(self.screen_info):
            self.log_test_result("SCREEN_TEST", f"Testing screen {i}: {info['name']} {info['geometry']}")
            
            # Move cursor to multiple positions on each screen
            screen_rect = info['geometry_rect']
            
            # Test positions: center, and offset positions to ensure we hit different areas
            test_positions = [
                ("center", screen_rect.x() + screen_rect.width() // 2, screen_rect.y() + screen_rect.height() // 2),
                ("top-quarter", screen_rect.x() + screen_rect.width() // 2, screen_rect.y() + screen_rect.height() // 4),
                ("bottom-quarter", screen_rect.x() + screen_rect.width() // 2, screen_rect.y() + 3 * screen_rect.height() // 4),
                ("left-quarter", screen_rect.x() + screen_rect.width() // 4, screen_rect.y() + screen_rect.height() // 2),
                ("right-quarter", screen_rect.x() + 3 * screen_rect.width() // 4, screen_rect.y() + screen_rect.height() // 2)
            ]
            
            for pos_name, target_x, target_y in test_positions:
                self.log_test_result("CURSOR_MOVE", 
                                   f"Screen {i} ({info['name']}) {pos_name}: "
                                   f"moving cursor to absolute ({target_x},{target_y}) "
                                   f"screen_offset=({screen_rect.x()},{screen_rect.y()})")
                
                # Use Qt to move cursor (works better than X11 for testing)
                from PyQt6.QtGui import QCursor
                QCursor.setPos(target_x, target_y)
                
                # Wait for position update
                time.sleep(0.3)
                QApplication.processEvents()
                
                # Verify cursor actually moved to expected position
                actual_cursor_pos = QCursor.pos()
                self.log_test_result("CURSOR_VERIFY", 
                                   f"Cursor move verification: target=({target_x},{target_y}) "
                                   f"actual=({actual_cursor_pos.x()},{actual_cursor_pos.y()})")
                
                # Check if overlay followed
                cursor_pos = get_cursor_position(include_screen_info=True)
                if cursor_pos:
                    overlay_pos = self.overlay.pos()
                    expected_x = target_x + self.offset_x_spin.value()
                    expected_y = target_y + self.offset_y_spin.value()
                    
                    # Check if overlay is on the correct screen
                    overlay_screen = self._get_screen_for_point(overlay_pos.x(), overlay_pos.y())
                    cursor_screen = self._get_screen_for_point(actual_cursor_pos.x(), actual_cursor_pos.y())
                    
                    self.log_test_result("POSITION_CHECK", 
                                       f"Screen {i} {pos_name}: "
                                       f"cursor=({actual_cursor_pos.x()},{actual_cursor_pos.y()}) cursor_screen={cursor_screen} "
                                       f"overlay=({overlay_pos.x()},{overlay_pos.y()}) overlay_screen={overlay_screen} "
                                       f"expected≈({expected_x},{expected_y}) "
                                       f"cursor_rel=({cursor_pos.x},{cursor_pos.y}) detected_screen={cursor_pos.screen_number}")
                else:
                    self.log_test_result("ERROR", f"Failed to get cursor position for screen {i} {pos_name}")
                
                time.sleep(0.4)  # Brief pause between positions
            
            time.sleep(0.7)  # Longer pause between screens
    
    def test_screen_edges(self):
        """Test positioning near screen edges."""
        if not self.overlay:
            self.create_test_overlay()
        
        self.enable_cursor_positioning()
        
        for i, info in enumerate(self.screen_info):
            screen_rect = info['geometry_rect']
            
            # Test positions: corners and edge centers
            test_positions = [
                ("top-left", screen_rect.x() + 10, screen_rect.y() + 10),
                ("top-right", screen_rect.x() + screen_rect.width() - 10, screen_rect.y() + 10),
                ("bottom-left", screen_rect.x() + 10, screen_rect.y() + screen_rect.height() - 10),
                ("bottom-right", screen_rect.x() + screen_rect.width() - 10, screen_rect.y() + screen_rect.height() - 10),
                ("center", screen_rect.x() + screen_rect.width() // 2, screen_rect.y() + screen_rect.height() // 2),
            ]
            
            self.log_test_result("EDGE_TEST", f"Testing edges for screen {i}")
            
            for pos_name, x, y in test_positions:
                from PyQt6.QtGui import QCursor
                QCursor.setPos(x, y)
                time.sleep(0.2)
                QApplication.processEvents()
                
                overlay_pos = self.overlay.pos()
                cursor_pos = get_cursor_position(include_screen_info=True)
                
                # Check if overlay stayed on screen
                overlay_on_screen = self._is_point_on_screen(overlay_pos.x(), overlay_pos.y(), i)
                
                self.log_test_result("EDGE_RESULT", 
                                   f"Screen {i} {pos_name}: cursor=({x},{y}) "
                                   f"overlay=({overlay_pos.x()},{overlay_pos.y()}) "
                                   f"on_screen={overlay_on_screen}")
                
                time.sleep(0.3)
    
    def run_automated_tests(self):
        """Run a full suite of automated tests."""
        self.log_test_result("AUTO_TEST_START", "Starting automated test suite")
        
        # Test 1: Basic overlay creation
        self.create_test_overlay()
        time.sleep(0.5)
        
        # Test 2: Enable cursor positioning
        self.enable_cursor_positioning()
        time.sleep(0.5)
        
        # Test 3: Test offset changes
        for offset in [(10, 10), (50, 30), (-20, 40), (0, 0)]:
            self.offset_x_spin.setValue(offset[0])
            self.offset_y_spin.setValue(offset[1])
            self.update_cursor_offset()
            time.sleep(0.3)
        
        # Test 4: Test all screens
        self.test_all_screens()
        
        # Test 5: Test screen edges
        self.test_screen_edges()
        
        # Test 6: Disable and re-enable
        self.disable_cursor_positioning()
        time.sleep(0.5)
        self.enable_cursor_positioning()
        
        self.log_test_result("AUTO_TEST_COMPLETE", "Automated test suite completed")
    
    def _get_screen_for_point(self, x: int, y: int) -> int:
        """Get the screen index for a given point."""
        for i, screen in enumerate(self.screens):
            if screen.geometry().contains(x, y):
                return i
        return -1  # Not on any screen
    
    def _is_point_on_screen(self, x: int, y: int, screen_index: int) -> bool:
        """Check if a point is on a specific screen."""
        if 0 <= screen_index < len(self.screens):
            return self.screens[screen_index].geometry().contains(x, y)
        return False
    
    def log_test_result(self, test_type: str, message: str):
        """Log a test result with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {test_type}: {message}"
        self.test_log.append(log_entry)
        
        # Update text display
        self.test_log_text.append(log_entry)
        
        # Auto-scroll to bottom
        from PyQt6.QtGui import QTextCursor
        self.test_log_text.moveCursor(QTextCursor.MoveOperation.End)
        
        print(log_entry)  # Also print to console
    
    def clear_test_log(self):
        """Clear the test log."""
        self.test_log.clear()
        self.test_log_text.clear()
        self.log_test_result("LOG_CLEARED", "Test log cleared")
    
    def closeEvent(self, event):
        """Handle window closing."""
        if self.overlay:
            self.overlay.close()
        
        # Stop timers
        self.update_timer.stop()
        if self.auto_test_timer.isActive():
            self.auto_test_timer.stop()
        
        # Save test log
        try:
            with open('multimonitor_test_log.txt', 'w') as f:
                f.write(f"NixWhisper Multimonitor Test Log\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                for entry in self.test_log:
                    f.write(entry + "\n")
            print("Test log saved to multimonitor_test_log.txt")
        except Exception as e:
            print(f"Failed to save test log: {e}")
        
        super().closeEvent(event)

def main():
    """Main function to run the multimonitor test."""
    app = QApplication(sys.argv)
    
    # Check if we have multiple screens
    screens = app.screens()
    print(f"Detected {len(screens)} screen(s)")
    
    if len(screens) < 2:
        print("WARNING: Only one screen detected. Multimonitor tests will be limited.")
        print("For full testing, please connect additional monitors.")
    
    # Create and show test window
    test_window = MultiMonitorTestWindow()
    test_window.show()
    
    print("\nMultimonitor Test Suite Started")
    print("=" * 40)
    print("Instructions:")
    print("1. Click 'Create Test Overlay' to create a test overlay window")
    print("2. Click 'Enable Cursor Positioning' to enable cursor following")
    print("3. Move your cursor around different screens and observe overlay behavior")
    print("4. Use 'Test All Screens' to automatically test each screen")
    print("5. Use 'Test Screen Edges' to test edge positioning behavior")
    print("6. Use 'Run Automated Tests' for a complete test suite")
    print("7. Check the test log for detailed results")
    print("=" * 40)
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())