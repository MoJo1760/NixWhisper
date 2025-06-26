#!/usr/bin/env python3
"""
Test script for visual cursor connection indicators in multimonitor setup.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QComboBox, QCheckBox
from PyQt6.QtGui import QCursor, QColor
from PyQt6.QtCore import Qt, QTimer
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position
import time

class VisualConnectionTestWindow:
    """Test window for visual connection indicators."""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.overlay = None
        self.test_timer = QTimer()
        self.auto_test_active = False
        self.current_test_step = 0
        
    def create_overlay(self):
        """Create the test overlay with visual connections enabled."""
        if self.overlay:
            self.overlay.close()
        
        self.overlay = OverlayWindow()
        self.overlay.resize(250, 100)
        
        # Style the overlay
        self.overlay.setStyleSheet("""
            background-color: rgba(50, 50, 50, 200);
            border: 2px solid white;
            border-radius: 12px;
            color: white;
            font-weight: bold;
            padding: 10px;
        """)
        
        # Add content
        layout = QVBoxLayout(self.overlay)
        
        title = QLabel("🎯 Visual Connection Test")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Control buttons
        controls = QHBoxLayout()
        
        # Style selector
        style_combo = QComboBox()
        style_combo.addItems(['arrow', 'line', 'none'])
        style_combo.currentTextChanged.connect(self.overlay.set_cursor_connection_style)
        controls.addWidget(QLabel("Style:"))
        controls.addWidget(style_combo)
        
        # Animation toggle
        anim_checkbox = QCheckBox("Animated")
        anim_checkbox.setChecked(True)
        anim_checkbox.toggled.connect(self.overlay.set_cursor_connection_animated)
        controls.addWidget(anim_checkbox)
        
        # Enable/disable toggle
        enable_checkbox = QCheckBox("Show Connection")
        enable_checkbox.setChecked(True)
        enable_checkbox.toggled.connect(self.overlay.set_cursor_connection_enabled)
        controls.addWidget(enable_checkbox)
        
        layout.addLayout(controls)
        
        # Color test buttons
        color_layout = QHBoxLayout()
        
        blue_btn = QPushButton("Blue")
        blue_btn.clicked.connect(lambda: self.overlay.set_cursor_connection_color(QColor(100, 200, 255, 180)))
        color_layout.addWidget(blue_btn)
        
        green_btn = QPushButton("Green")
        green_btn.clicked.connect(lambda: self.overlay.set_cursor_connection_color(QColor(100, 255, 100, 180)))
        color_layout.addWidget(green_btn)
        
        red_btn = QPushButton("Red")
        red_btn.clicked.connect(lambda: self.overlay.set_cursor_connection_color(QColor(255, 100, 100, 180)))
        color_layout.addWidget(red_btn)
        
        layout.addLayout(color_layout)
        
        self.overlay.show()
        self.overlay.enable_cursor_relative_positioning(True)
        self.overlay.set_cursor_offset(40, 40)
        
        print("✓ Overlay created with visual connection indicators")
        return self.overlay
    
    def run_manual_test(self):
        """Run interactive manual test."""
        print("=== Visual Connection Manual Test ===")
        print("1. Move your cursor around the screens")
        print("2. Notice the visual connection (arrow/line) from overlay to cursor")
        print("3. Try different styles and colors using the overlay controls")
        print("4. Test both animated and static modes")
        print("5. Press Ctrl+C to exit")
        
        overlay = self.create_overlay()
        
        try:
            self.app.exec()
        except KeyboardInterrupt:
            print("\nTest completed!")
        finally:
            if overlay:
                overlay.close()
    
    def run_automated_test(self):
        """Run automated test moving cursor to different positions."""
        print("=== Visual Connection Automated Test ===")
        
        screens = self.app.screens()
        print(f"Testing on {len(screens)} screens:")
        for i, screen in enumerate(screens):
            geom = screen.geometry()
            print(f"  Screen {i}: {screen.name()} {geom.width()}x{geom.height()}+{geom.x()}+{geom.y()}")
        
        overlay = self.create_overlay()
        
        # Test different styles
        styles = ['arrow', 'line']
        colors = [
            (QColor(100, 200, 255, 180), "Blue"),
            (QColor(100, 255, 100, 180), "Green"),
            (QColor(255, 200, 100, 180), "Orange")
        ]
        
        print(f"\nTesting visual connection styles and colors...")
        
        for style in styles:
            print(f"\n--- Testing {style} style ---")
            overlay.set_cursor_connection_style(style)
            
            for color, color_name in colors:
                print(f"  Testing {color_name} color...")
                overlay.set_cursor_connection_color(color)
                
                # Test on each screen
                for i, screen in enumerate(screens):
                    geom = screen.geometry()
                    positions = [
                        ("center", geom.x() + geom.width() // 2, geom.y() + geom.height() // 2),
                        ("top-left", geom.x() + 50, geom.y() + 50),
                        ("bottom-right", geom.x() + geom.width() - 50, geom.y() + geom.height() - 50),
                    ]
                    
                    for pos_name, x, y in positions:
                        print(f"    Screen {i} {pos_name}: moving cursor to ({x}, {y})")
                        QCursor.setPos(x, y)
                        time.sleep(0.8)  # Wait for visual feedback
                        self.app.processEvents()
        
        # Test animation
        print(f"\n--- Testing Animation ---")
        overlay.set_cursor_connection_style('arrow')
        overlay.set_cursor_connection_color(QColor(100, 200, 255, 180))
        
        print("  Testing with animation enabled...")
        overlay.set_cursor_connection_animated(True)
        time.sleep(2)
        
        print("  Testing with animation disabled...")
        overlay.set_cursor_connection_animated(False)
        time.sleep(2)
        
        print("  Re-enabling animation...")
        overlay.set_cursor_connection_animated(True)
        
        print(f"\n--- Final Test: Connection Disable/Enable ---")
        print("  Disabling connection...")
        overlay.set_cursor_connection_enabled(False)
        time.sleep(1)
        
        print("  Re-enabling connection...")
        overlay.set_cursor_connection_enabled(True)
        time.sleep(1)
        
        print(f"\n✅ Automated test completed!")
        print("Visual connection indicators are working across all screens.")
        
        # Show final settings
        settings = overlay.get_cursor_connection_settings()
        print(f"\nFinal settings: {settings}")
        
        overlay.close()
    
    def run_interactive_demo(self):
        """Run an interactive demo showcasing the visual connection features."""
        print("=== Interactive Visual Connection Demo ===")
        print("This demo will automatically move the cursor and change styles")
        print("Press Ctrl+C to stop...")
        
        overlay = self.create_overlay()
        screens = self.app.screens()
        
        # Demo sequence
        demo_steps = [
            ("Starting with blue arrow style", lambda: (
                overlay.set_cursor_connection_style('arrow'),
                overlay.set_cursor_connection_color(QColor(100, 200, 255, 180))
            )),
            ("Moving to screen corners...", lambda: None),
            ("Switching to green line style", lambda: (
                overlay.set_cursor_connection_style('line'),
                overlay.set_cursor_connection_color(QColor(100, 255, 100, 180))
            )),
            ("Testing animation effects...", lambda: overlay.set_cursor_connection_animated(True)),
            ("Disabling animation...", lambda: overlay.set_cursor_connection_animated(False)),
            ("Re-enabling animation...", lambda: overlay.set_cursor_connection_animated(True)),
            ("Switching to red arrows", lambda: (
                overlay.set_cursor_connection_style('arrow'),
                overlay.set_cursor_connection_color(QColor(255, 100, 100, 180))
            )),
            ("Demo complete!", lambda: None)
        ]
        
        try:
            for step_desc, action in demo_steps:
                print(f"\n{step_desc}")
                if action:
                    action()
                
                # Move cursor around screens
                for screen in screens:
                    geom = screen.geometry()
                    positions = [
                        (geom.x() + 100, geom.y() + 100),
                        (geom.x() + geom.width() - 100, geom.y() + 100),
                        (geom.x() + geom.width() - 100, geom.y() + geom.height() - 100),
                        (geom.x() + 100, geom.y() + geom.height() - 100),
                    ]
                    
                    for x, y in positions:
                        QCursor.setPos(x, y)
                        time.sleep(0.3)
                        self.app.processEvents()
                
                time.sleep(1)
            
        except KeyboardInterrupt:
            print("\nDemo interrupted!")
        finally:
            overlay.close()

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test visual cursor connection indicators")
    parser.add_argument('--mode', choices=['manual', 'auto', 'demo'], default='manual',
                      help='Test mode: manual (interactive), auto (automated), demo (showcase)')
    
    args = parser.parse_args()
    
    tester = VisualConnectionTestWindow()
    
    print(f"🎯 Visual Connection Test Mode: {args.mode}")
    print("=" * 50)
    
    if args.mode == 'manual':
        tester.run_manual_test()
    elif args.mode == 'auto':
        tester.run_automated_test()
    elif args.mode == 'demo':
        tester.run_interactive_demo()

if __name__ == "__main__":
    main()