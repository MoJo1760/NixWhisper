#!/usr/bin/env python3
"""
Cross-application testing for cursor positioning in NixWhisper.
Tests cursor tracking accuracy in different applications.
"""

import sys
sys.path.insert(0, 'src')

import subprocess
import time
import signal
from typing import List, Dict, Optional, Tuple
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout
from PyQt6.QtGui import QCursor, QColor
from PyQt6.QtCore import Qt, QTimer
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position
import psutil

class CrossApplicationTester:
    """Test cursor positioning across different applications."""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.overlay = None
        self.test_processes = []
        self.test_results = []
        
    def create_test_overlay(self):
        """Create overlay for testing with enhanced visibility."""
        if self.overlay:
            self.overlay.close()
        
        self.overlay = OverlayWindow()
        self.overlay.resize(300, 80)
        
        # Make it highly visible for testing
        self.overlay.setStyleSheet("""
            background-color: rgba(255, 165, 0, 240);
            border: 3px solid red;
            border-radius: 15px;
            color: black;
            font-weight: bold;
            font-size: 14px;
            padding: 15px;
        """)
        
        # Add content
        layout = QVBoxLayout(self.overlay)
        title = QLabel("🔍 Cross-App Test Overlay")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Enable all visual features for testing
        self.overlay.show()
        self.overlay.enable_cursor_relative_positioning(True)
        self.overlay.set_cursor_offset(40, 40)
        self.overlay.set_cursor_connection_enabled(True)
        self.overlay.set_cursor_connection_style('arrow')
        self.overlay.set_cursor_connection_color(QColor(255, 0, 0, 200))  # Bright red
        self.overlay.set_cursor_connection_animated(True)
        
        print("✓ Test overlay created with enhanced visibility")
        return self.overlay
    
    def is_application_running(self, app_name: str) -> bool:
        """Check if an application is currently running."""
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                # Check process name
                if app_name.lower() in proc.info['name'].lower():
                    return True
                # Check command line for flatpak apps, snaps, etc.
                if proc.info['cmdline']:
                    cmdline_str = ' '.join(proc.info['cmdline']).lower()
                    if app_name.lower() in cmdline_str:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    def launch_application(self, app_command: str, app_name: str) -> Optional[subprocess.Popen]:
        """Launch an application for testing."""
        try:
            print(f"  Launching {app_name}...")
            # Try to launch the application
            process = subprocess.Popen(
                app_command.split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=None
            )
            
            # Wait a bit for the app to start
            time.sleep(2)
            
            # Check if it's actually running
            if self.is_application_running(app_name):
                print(f"    ✓ {app_name} launched successfully")
                self.test_processes.append(process)
                return process
            else:
                print(f"    ❌ {app_name} failed to launch or not detected")
                return None
                
        except FileNotFoundError:
            print(f"    ❌ {app_name} not found ({app_command})")
            return None
        except Exception as e:
            print(f"    ❌ Error launching {app_name}: {e}")
            return None
    
    def test_application_cursor_tracking(self, app_name: str, duration: int = 5) -> Dict:
        """Test cursor tracking accuracy in a specific application."""
        print(f"\n--- Testing cursor tracking in {app_name} ---")
        print(f"  Duration: {duration} seconds")
        print(f"  Instructions: Move your cursor around within {app_name}")
        
        if not self.is_application_running(app_name):
            return {"app": app_name, "running": False, "error": "Application not running"}
        
        start_time = time.time()
        samples = []
        
        while time.time() - start_time < duration:
            # Get cursor position
            cursor_qt = QCursor.pos()
            cursor_tracked = get_cursor_position(include_screen_info=True)
            overlay_pos = self.overlay.pos() if self.overlay else None
            
            # Record sample
            sample = {
                "timestamp": time.time() - start_time,
                "cursor_qt": (cursor_qt.x(), cursor_qt.y()),
                "cursor_tracked": None,
                "overlay_pos": (overlay_pos.x(), overlay_pos.y()) if overlay_pos else None,
                "tracking_working": False
            }
            
            if cursor_tracked:
                abs_x = cursor_tracked.screen_x + cursor_tracked.x
                abs_y = cursor_tracked.screen_y + cursor_tracked.y
                sample["cursor_tracked"] = (abs_x, abs_y)
                sample["tracking_working"] = True
                
                # Check position accuracy (within 10px tolerance)
                qt_x, qt_y = sample["cursor_qt"]
                tracked_x, tracked_y = sample["cursor_tracked"]
                distance = ((qt_x - tracked_x) ** 2 + (qt_y - tracked_y) ** 2) ** 0.5
                sample["position_accurate"] = distance < 10
            
            samples.append(sample)
            time.sleep(0.1)  # 10 FPS sampling
            self.app.processEvents()
        
        # Analyze results
        total_samples = len(samples)
        tracking_samples = sum(1 for s in samples if s["tracking_working"])
        accurate_samples = sum(1 for s in samples if s.get("position_accurate", False))
        
        tracking_rate = (tracking_samples / total_samples * 100) if total_samples > 0 else 0
        accuracy_rate = (accurate_samples / tracking_samples * 100) if tracking_samples > 0 else 0
        
        result = {
            "app": app_name,
            "running": True,
            "duration": duration,
            "total_samples": total_samples,
            "tracking_samples": tracking_samples,
            "accurate_samples": accurate_samples,
            "tracking_rate": tracking_rate,
            "accuracy_rate": accuracy_rate,
            "samples": samples[-10:]  # Keep last 10 samples for debugging
        }
        
        print(f"  Results:")
        print(f"    Tracking rate: {tracking_rate:.1f}% ({tracking_samples}/{total_samples})")
        print(f"    Accuracy rate: {accuracy_rate:.1f}% ({accurate_samples}/{tracking_samples})")
        
        return result
    
    def test_text_editors(self):
        """Test cursor tracking in common text editors."""
        print("\n=== Testing Text Editors ===")
        
        text_editors = [
            ("gedit", "gedit"),
            ("code", "code"),  # VS Code
            ("subl", "sublime_text"),  # Sublime Text
            ("vim", "vim"),
            ("emacs", "emacs"),
            ("mousepad", "mousepad"),  # XFCE editor
            ("kate", "kate"),  # KDE editor
            ("leafpad", "leafpad"),  # Lightweight editor
        ]
        
        available_editors = []
        
        # Check which editors are available
        print("Checking available text editors...")
        for command, process_name in text_editors:
            # Try to find the command
            try:
                result = subprocess.run(['which', command], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    available_editors.append((command, process_name))
                    print(f"  ✓ {command} found")
                else:
                    print(f"  ❌ {command} not found")
            except:
                print(f"  ❌ Error checking {command}")
        
        if not available_editors:
            print("❌ No text editors found for testing")
            return []
        
        results = []
        
        # Test each available editor
        for command, process_name in available_editors[:3]:  # Test first 3 to save time
            print(f"\n--- Testing {command} ---")
            
            # Check if already running
            if self.is_application_running(process_name):
                print(f"  {process_name} is already running")
                result = self.test_application_cursor_tracking(process_name, duration=8)
            else:
                # Try to launch it
                process = self.launch_application(command, process_name)
                if process:
                    # Wait for user to interact
                    print(f"  Please switch to {process_name} and move your cursor around...")
                    time.sleep(2)
                    result = self.test_application_cursor_tracking(process_name, duration=8)
                else:
                    result = {"app": process_name, "running": False, "error": "Failed to launch"}
            
            results.append(result)
            time.sleep(1)  # Brief pause between tests
        
        return results
    
    def test_terminals(self):
        """Test cursor tracking in terminal applications."""
        print("\n=== Testing Terminal Applications ===")
        
        terminals = [
            ("gnome-terminal", "gnome-terminal"),
            ("konsole", "konsole"),  # KDE terminal
            ("xfce4-terminal", "xfce4-terminal"),  # XFCE terminal
            ("terminator", "terminator"),
            ("alacritty", "alacritty"),
            ("kitty", "kitty"),
            ("xterm", "xterm"),
        ]
        
        available_terminals = []
        
        # Check which terminals are available
        print("Checking available terminals...")
        for command, process_name in terminals:
            try:
                result = subprocess.run(['which', command], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    available_terminals.append((command, process_name))
                    print(f"  ✓ {command} found")
                else:
                    print(f"  ❌ {command} not found")
            except:
                print(f"  ❌ Error checking {command}")
        
        if not available_terminals:
            print("❌ No terminals found for testing")
            return []
        
        results = []
        
        # Test each available terminal
        for command, process_name in available_terminals[:2]:  # Test first 2 to save time
            print(f"\n--- Testing {command} ---")
            
            # Check if already running
            if self.is_application_running(process_name):
                print(f"  {process_name} is already running")
                result = self.test_application_cursor_tracking(process_name, duration=6)
            else:
                # Try to launch it
                process = self.launch_application(command, process_name)
                if process:
                    print(f"  Please switch to {process_name} and move your cursor around...")
                    time.sleep(2)
                    result = self.test_application_cursor_tracking(process_name, duration=6)
                else:
                    result = {"app": process_name, "running": False, "error": "Failed to launch"}
            
            results.append(result)
            time.sleep(1)
        
        return results
    
    def cleanup_test_processes(self):
        """Clean up any processes launched during testing."""
        print("\nCleaning up test processes...")
        for process in self.test_processes:
            try:
                if process.poll() is None:  # Process is still running
                    print(f"  Terminating process {process.pid}")
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:  # Still running, force kill
                        process.kill()
            except:
                pass
        self.test_processes.clear()
    
    def generate_test_report(self, all_results: List[Dict]):
        """Generate a comprehensive test report."""
        print("\n" + "=" * 60)
        print("CROSS-APPLICATION CURSOR TRACKING TEST REPORT")
        print("=" * 60)
        
        total_apps = len(all_results)
        successful_apps = len([r for r in all_results if r.get("running", False)])
        
        print(f"Total applications tested: {total_apps}")
        print(f"Successfully tested: {successful_apps}")
        print(f"Success rate: {(successful_apps/total_apps*100):.1f}%" if total_apps > 0 else "N/A")
        
        print(f"\nDetailed Results:")
        print("-" * 60)
        
        for result in all_results:
            app_name = result["app"]
            if not result.get("running", False):
                print(f"{app_name:20} ❌ NOT RUNNING - {result.get('error', 'Unknown error')}")
                continue
            
            tracking_rate = result.get("tracking_rate", 0)
            accuracy_rate = result.get("accuracy_rate", 0)
            
            # Determine status
            if tracking_rate >= 95 and accuracy_rate >= 90:
                status = "✅ EXCELLENT"
            elif tracking_rate >= 80 and accuracy_rate >= 75:
                status = "✓ GOOD"
            elif tracking_rate >= 60:
                status = "⚠ FAIR"
            else:
                status = "❌ POOR"
            
            print(f"{app_name:20} {status:12} Track:{tracking_rate:5.1f}% Acc:{accuracy_rate:5.1f}%")
        
        # Summary recommendations
        print(f"\nRecommendations:")
        print("-" * 60)
        
        poor_apps = [r for r in all_results if r.get("running") and r.get("tracking_rate", 0) < 60]
        if poor_apps:
            print("⚠ Applications with poor tracking performance:")
            for app in poor_apps:
                print(f"  - {app['app']}: Consider investigating cursor tracking issues")
        
        excellent_apps = [r for r in all_results if r.get("running") and 
                         r.get("tracking_rate", 0) >= 95 and r.get("accuracy_rate", 0) >= 90]
        if excellent_apps:
            print("✅ Applications with excellent performance:")
            for app in excellent_apps:
                print(f"  - {app['app']}: Cursor tracking working perfectly")
        
        return all_results
    
    def run_cross_application_tests(self):
        """Run comprehensive cross-application tests."""
        print("🔍 Cross-Application Cursor Tracking Test Suite")
        print("=" * 50)
        
        # Create test overlay
        self.create_test_overlay()
        
        try:
            all_results = []
            
            # Test text editors
            editor_results = self.test_text_editors()
            all_results.extend(editor_results)
            
            # Test terminals
            terminal_results = self.test_terminals()
            all_results.extend(terminal_results)
            
            # Generate final report
            self.generate_test_report(all_results)
            
        finally:
            # Cleanup
            self.cleanup_test_processes()
            if self.overlay:
                self.overlay.close()
            print("\n✓ Test suite completed and cleaned up")

def main():
    """Main function to run cross-application tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test cursor positioning across applications")
    parser.add_argument('--editors-only', action='store_true', 
                       help='Test only text editors')
    parser.add_argument('--terminals-only', action='store_true',
                       help='Test only terminals')
    
    args = parser.parse_args()
    
    tester = CrossApplicationTester()
    
    if args.editors_only:
        print("Running text editor tests only...")
        tester.create_test_overlay()
        try:
            results = tester.test_text_editors()
            tester.generate_test_report(results)
        finally:
            tester.cleanup_test_processes()
            if tester.overlay:
                tester.overlay.close()
    elif args.terminals_only:
        print("Running terminal tests only...")
        tester.create_test_overlay()
        try:
            results = tester.test_terminals()
            tester.generate_test_report(results)
        finally:
            tester.cleanup_test_processes()
            if tester.overlay:
                tester.overlay.close()
    else:
        tester.run_cross_application_tests()

if __name__ == "__main__":
    main()