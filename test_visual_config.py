#!/usr/bin/env python3
"""
Test script for visual connection configuration integration.
"""

import sys
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from nixwhisper.config import Config, OverlayConfig
from nixwhisper.qt_gui import NixWhisperWindow
import json
import tempfile
import os

def test_config_integration():
    """Test that visual connection settings are properly integrated."""
    app = QApplication(sys.argv)
    
    print("=== Visual Connection Configuration Test ===")
    
    # Create a temporary config file with visual connection settings
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_config = {
            "ui": {
                "theme": "system",
                "hotkey": "Ctrl+Space",
                "silence_detection": True,
                "silence_threshold": 0.01,
                "silence_duration": 2.0
            },
            "overlay": {
                "cursor_connection_enabled": True,
                "cursor_connection_style": "arrow",
                "cursor_connection_color": "#ff6b9d",
                "cursor_connection_width": 3,
                "cursor_connection_arrow_size": 10,
                "cursor_connection_animated": True
            },
            "audio": {
                "sample_rate": 16000,
                "channels": 1
            },
            "model": {
                "name": "base.en"
            },
            "hotkeys": {
                "toggle_listening": "<ctrl>+<alt>+space"
            }
        }
        json.dump(test_config, f, indent=2)
        config_path = f.name
    
    try:
        print(f"✓ Created test config file: {config_path}")
        
        # Load config
        config = Config.from_file(config_path)
        print(f"✓ Loaded config successfully")
        print(f"  Visual connection enabled: {config.overlay.cursor_connection_enabled}")
        print(f"  Visual connection style: {config.overlay.cursor_connection_style}")
        print(f"  Visual connection color: {config.overlay.cursor_connection_color}")
        print(f"  Visual connection animated: {config.overlay.cursor_connection_animated}")
        
        # Create NixWhisperWindow with this config
        from nixwhisper.model_manager import ModelManager
        model_manager = ModelManager()  # Use default cache dir
        window = NixWhisperWindow(model_manager=model_manager, config=config)
        print(f"✓ Created NixWhisperWindow with custom config")
        
        # Initialize overlay to test config application
        print(f"Checking if overlay already exists: {hasattr(window, 'overlay') and window.overlay is not None}")
        init_result = window.init_overlay()
        print(f"Init overlay result: {init_result}")
        if init_result or (hasattr(window, 'overlay') and window.overlay):
            print(f"✓ Overlay available for testing")
            
            # Check that overlay settings match config
            overlay = window.overlay
            settings = overlay.get_cursor_connection_settings()
            print(f"✓ Retrieved overlay settings: {settings}")
            
            # Verify settings match what we configured
            expected_enabled = config.overlay.cursor_connection_enabled
            expected_style = config.overlay.cursor_connection_style
            expected_animated = config.overlay.cursor_connection_animated
            
            if settings['enabled'] == expected_enabled:
                print(f"  ✓ Enabled setting matches: {expected_enabled}")
            else:
                print(f"  ❌ Enabled mismatch: expected {expected_enabled}, got {settings['enabled']}")
            
            if settings['style'] == expected_style:
                print(f"  ✓ Style setting matches: {expected_style}")
            else:
                print(f"  ❌ Style mismatch: expected {expected_style}, got {settings['style']}")
            
            if settings['animated'] == expected_animated:
                print(f"  ✓ Animation setting matches: {expected_animated}")
            else:
                print(f"  ❌ Animation mismatch: expected {expected_animated}, got {settings['animated']}")
            
            # Test settings dialog
            print(f"\nTesting settings dialog...")
            from nixwhisper.qt_gui import SettingsDialog
            settings_dialog = SettingsDialog(window)
            print(f"✓ Created settings dialog")
            
            # Check that dialog loads current settings
            dialog_enabled = settings_dialog.visual_enable_cb.isChecked()
            dialog_style = settings_dialog.style_combo.currentText()
            dialog_color = settings_dialog.color_input.text()
            dialog_animated = settings_dialog.animation_cb.isChecked()
            
            print(f"  Dialog enabled: {dialog_enabled} (expected: {expected_enabled})")
            print(f"  Dialog style: {dialog_style} (expected: {expected_style})")
            print(f"  Dialog color: {dialog_color} (expected: {config.overlay.cursor_connection_color})")
            print(f"  Dialog animated: {dialog_animated} (expected: {expected_animated})")
            
            # Test saving new settings
            print(f"\nTesting settings save...")
            settings_dialog.visual_enable_cb.setChecked(False)
            settings_dialog.style_combo.setCurrentText("line")
            settings_dialog.color_input.setText("#00ff00")
            settings_dialog.animation_cb.setChecked(False)
            
            # Simulate accepting the dialog
            settings_dialog.accept()
            print(f"✓ Dialog accepted, settings should be updated")
            
            # Check that overlay settings were updated
            new_settings = overlay.get_cursor_connection_settings()
            print(f"  New overlay settings: {new_settings}")
            
            # Check that config was updated
            print(f"  New config enabled: {window.config.overlay.cursor_connection_enabled}")
            print(f"  New config style: {window.config.overlay.cursor_connection_style}")
            print(f"  New config color: {window.config.overlay.cursor_connection_color}")
            print(f"  New config animated: {window.config.overlay.cursor_connection_animated}")
            
            overlay.close()
        else:
            print(f"❌ Failed to initialize overlay")
        
        print(f"\n🎉 Configuration integration test completed!")
        
    finally:
        # Clean up temp file
        os.unlink(config_path)
        print(f"✓ Cleaned up temp config file")

if __name__ == "__main__":
    test_config_integration()