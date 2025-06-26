#!/usr/bin/env python3
"""
Diagnose overlay positioning issues during actual application use.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout
from PyQt6.QtGui import QCursor, QColor
from PyQt6.QtCore import Qt, QTimer
from nixwhisper.qt_gui import NixWhisperWindow
from nixwhisper.model_manager import ModelManager
from nixwhisper.config import load_config
from nixwhisper.x11_cursor import get_cursor_position

class OverlayDiagnostic:
    """Diagnose overlay positioning issues."""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.diagnostic_timer = QTimer()
        self.diagnostic_timer.timeout.connect(self.check_overlay_status)
        self.window = None
        
    def create_main_window(self):
        """Create the main NixWhisper window."""
        config = load_config()
        model_manager = ModelManager()
        self.window = NixWhisperWindow(model_manager=model_manager, config=config)
        self.window.show()
        
        print("✓ Main NixWhisper window created")
        return self.window
    
    def check_overlay_status(self):
        """Check and report overlay status."""
        if not self.window:
            return
            
        # Get cursor position
        cursor_qt = QCursor.pos()
        cursor_tracked = get_cursor_position(include_screen_info=True)
        
        # Check if overlay exists
        overlay = getattr(self.window, 'overlay', None)
        
        print(f"\n--- Overlay Diagnostic ---")
        print(f"Cursor (Qt): ({cursor_qt.x()}, {cursor_qt.y()})")
        
        if cursor_tracked:
            abs_x = cursor_tracked.screen_x + cursor_tracked.x
            abs_y = cursor_tracked.screen_y + cursor_tracked.y
            print(f"Cursor (Tracked): ({abs_x}, {abs_y}) on screen {cursor_tracked.screen_number}")
        else:
            print(f"Cursor (Tracked): FAILED")
        
        if overlay:
            overlay_pos = overlay.pos()
            overlay_visible = overlay.isVisible()
            overlay_size = overlay.size()
            
            print(f"Overlay exists: YES")
            print(f"Overlay visible: {overlay_visible}")
            print(f"Overlay position: ({overlay_pos.x()}, {overlay_pos.y()})")
            print(f"Overlay size: {overlay_size.width()}x{overlay_size.height()}")
            
            # Check if overlay has cursor positioning enabled
            cursor_positioning = getattr(overlay, 'cursor_relative_positioning', False)
            print(f"Cursor positioning enabled: {cursor_positioning}")
            
            if cursor_positioning and cursor_tracked:
                expected_x = abs_x + getattr(overlay, 'cursor_offset_x', 0)
                expected_y = abs_y + getattr(overlay, 'cursor_offset_y', 0)
                distance = ((overlay_pos.x() - expected_x) ** 2 + (overlay_pos.y() - expected_y) ** 2) ** 0.5
                print(f"Expected position: ({expected_x}, {expected_y})")
                print(f"Position accuracy: {distance:.1f}px difference")
                
                if distance > 50:
                    print(f"⚠️  ISSUE: Large positioning error!")
                else:
                    print(f"✅ Positioning looks good")
        else:
            print(f"Overlay exists: NO")
            print(f"⚠️  The overlay hasn't been created yet")
            
        # Check recording state
        is_recording = getattr(self.window, 'is_recording', False)
        print(f"Recording active: {is_recording}")
        
        if is_recording and not (overlay and overlay.isVisible()):
            print(f"❌ PROBLEM: Recording but overlay not visible!")
        elif not is_recording and overlay and overlay.isVisible():
            print(f"ℹ️  INFO: Not recording but overlay is visible (may be normal)")
        
        print("-" * 30)
    
    def run_diagnostic(self):
        """Run the overlay diagnostic."""
        print("🔍 NixWhisper Overlay Diagnostic Tool")
        print("=" * 50)
        
        # Create main window
        self.create_main_window()
        
        # Start diagnostic timer
        self.diagnostic_timer.start(2000)  # Every 2 seconds
        
        print("\n📋 DIAGNOSTIC INSTRUCTIONS:")
        print("1. This tool will monitor overlay status every 2 seconds")
        print("2. Try pressing Ctrl+Space to start recording")
        print("3. Watch the diagnostic output to see what happens")
        print("4. Move your cursor around while recording")
        print("5. Look for any issues reported")
        print("6. Press Ctrl+C to exit")
        
        print("\n🎯 WHAT TO LOOK FOR:")
        print("• Overlay should be created when recording starts")
        print("• Overlay should be visible during recording")
        print("• Overlay position should follow cursor accurately")
        print("• Cursor positioning should be enabled")
        
        print("\n--- Starting diagnostic monitoring ---")
        
        try:
            self.app.exec()
        except KeyboardInterrupt:
            print("\n✓ Diagnostic stopped by user")
        finally:
            self.diagnostic_timer.stop()

def main():
    """Main diagnostic function."""
    diagnostic = OverlayDiagnostic()
    diagnostic.run_diagnostic()

if __name__ == "__main__":
    main()