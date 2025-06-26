#!/usr/bin/env python3
"""
Quick live test of NixWhisper with enhanced cursor positioning features.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtGui import QCursor, QColor, QFont
from PyQt6.QtCore import Qt, QTimer
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position
import time

class LiveTestDemo:
    """Interactive demo for testing cursor positioning features."""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.overlay = None
        self.info_timer = QTimer()
        self.info_timer.timeout.connect(self.update_info)
        
    def create_demo_overlay(self):
        """Create a highly visible demo overlay."""
        if self.overlay:
            self.overlay.close()
        
        self.overlay = OverlayWindow()
        self.overlay.resize(300, 120)
        
        # Make it very visible
        self.overlay.setStyleSheet("""
            background-color: rgba(255, 100, 0, 240);
            border: 3px solid yellow;
            border-radius: 15px;
            color: white;
            font-weight: bold;
            font-size: 14px;
            padding: 10px;
        """)
        
        # Add content
        layout = QVBoxLayout(self.overlay)
        
        title = QLabel("🎯 NixWhisper Live Test")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Control buttons
        controls = QHBoxLayout()
        
        arrow_btn = QPushButton("Arrow")
        arrow_btn.clicked.connect(lambda: self.set_connection_style('arrow'))
        controls.addWidget(arrow_btn)
        
        line_btn = QPushButton("Line")
        line_btn.clicked.connect(lambda: self.set_connection_style('line'))
        controls.addWidget(line_btn)
        
        none_btn = QPushButton("None")
        none_btn.clicked.connect(lambda: self.set_connection_style('none'))
        controls.addWidget(none_btn)
        
        layout.addLayout(controls)
        
        # Show and configure
        self.overlay.show()
        self.overlay.enable_cursor_relative_positioning(True)
        self.overlay.set_cursor_offset(60, 60)
        
        # Enable visual connection with bright colors
        self.overlay.set_cursor_connection_enabled(True)
        self.overlay.set_cursor_connection_style('arrow')
        self.overlay.set_cursor_connection_color(QColor(255, 255, 0, 255))  # Bright yellow
        self.overlay.set_cursor_connection_animated(True)
        
        print("✓ Demo overlay created!")
        print("  • Orange overlay with yellow border")
        print("  • Bright yellow arrow pointing to cursor")
        print("  • Offset: 60x60 pixels from cursor")
        print("  • Animation: Enabled")
        
        return self.overlay
    
    def set_connection_style(self, style):
        """Change connection style."""
        if self.overlay:
            self.overlay.set_cursor_connection_style(style)
            print(f"✓ Connection style changed to: {style}")
    
    def update_info(self):
        """Update status information."""
        if self.overlay and self.status_label:
            cursor_pos = QCursor.pos()
            overlay_pos = self.overlay.pos()
            
            # Get tracking info
            tracked = get_cursor_position(include_screen_info=True)
            if tracked:
                screen_info = f"Screen {tracked.screen_number}"
                tracking_status = "✅ Tracking"
            else:
                screen_info = "Unknown"
                tracking_status = "❌ Not tracking"
            
            status_text = f"{tracking_status}\nCursor: ({cursor_pos.x()}, {cursor_pos.y()})\nOverlay: ({overlay_pos.x()}, {overlay_pos.y()})\n{screen_info}"
            self.status_label.setText(status_text)
    
    def run_live_demo(self):
        """Run the interactive live demo."""
        print("🚀 NixWhisper Live Test Demo")
        print("=" * 40)
        
        # Create demo overlay
        self.create_demo_overlay()
        
        # Start info updates
        self.info_timer.start(200)  # Update every 200ms
        
        # Show instructions
        msg = QMessageBox()
        msg.setWindowTitle("NixWhisper Live Test")
        msg.setText("""
🎯 Live Test Instructions:

1. Move your cursor around the screen
2. Watch the orange overlay follow your cursor
3. Notice the yellow arrow pointing to your cursor
4. Try the buttons to change connection style
5. Test on multiple monitors if available

Features to test:
• Cursor following across screens
• Visual connection indicators  
• Real-time positioning updates
• Button controls for styles

Click OK to start testing!
""")
        msg.exec()
        
        print("\n📝 Testing Instructions:")
        print("1. Move cursor around - overlay should follow")
        print("2. Cross monitor boundaries if you have multiple screens")
        print("3. Try the Arrow/Line/None buttons")
        print("4. Watch the status info update in real-time")
        print("5. Press Ctrl+C in terminal to exit")
        
        try:
            # Run the application
            self.app.exec()
        except KeyboardInterrupt:
            print("\n✓ Demo stopped by user")
        finally:
            if self.overlay:
                self.overlay.close()
            print("✓ Demo cleanup completed")

def main():
    """Main function for live demo."""
    demo = LiveTestDemo()
    demo.run_live_demo()

if __name__ == "__main__":
    main()