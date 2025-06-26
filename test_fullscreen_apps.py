#!/usr/bin/env python3
"""
Test cursor tracking in full-screen applications.
"""

import sys
sys.path.insert(0, 'src')

import subprocess
import time
from typing import List, Dict
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout
from PyQt6.QtGui import QCursor, QColor
from PyQt6.QtCore import Qt
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position
import psutil

class FullscreenTester:
    """Test cursor tracking in full-screen applications."""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.overlay = None
        
    def create_test_overlay(self):
        """Create overlay optimized for full-screen testing."""
        if self.overlay:
            self.overlay.close()
        
        self.overlay = OverlayWindow()
        self.overlay.resize(250, 60)
        
        # Ultra-visible styling for full-screen testing
        self.overlay.setStyleSheet("""
            background-color: rgba(255, 0, 255, 220);
            border: 2px solid yellow;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            font-size: 12px;
            padding: 8px;
        """)
        
        layout = QVBoxLayout(self.overlay)
        title = QLabel("🎮 Fullscreen Test")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Configure for maximum visibility
        self.overlay.show()
        self.overlay.enable_cursor_relative_positioning(True)
        self.overlay.set_cursor_offset(30, 30)
        self.overlay.set_cursor_connection_enabled(True)
        self.overlay.set_cursor_connection_style('arrow')
        self.overlay.set_cursor_connection_color(QColor(255, 255, 0, 255))  # Bright yellow
        self.overlay.set_cursor_connection_animated(True)
        
        print("✓ Full-screen test overlay created")
        return self.overlay
    
    def test_browser_fullscreen(self, duration: int = 10):
        """Test cursor tracking in browser full-screen mode."""
        print("\n=== Testing Browser Full-Screen Mode ===")
        print("Instructions:")
        print("1. Open a web browser")
        print("2. Press F11 to enter full-screen mode")
        print("3. Move your cursor around for testing")
        print("4. Press F11 again to exit full-screen when done")
        print("\nPress Enter when ready to start the test...")
        input()
        
        return self.run_tracking_test("Browser (Full-screen)", duration)
    
    def test_video_fullscreen(self, duration: int = 8):
        """Test cursor tracking with full-screen video."""
        print("\n=== Testing Video Player Full-Screen ===")
        print("Instructions:")
        print("1. Open a video player (e.g., VLC, totem)")
        print("2. Play a video and enter full-screen mode")
        print("3. Move your cursor around (it may hide/show)")
        print("4. Exit full-screen when done")
        print("\nPress Enter when ready to start the test...")
        input()
        
        return self.run_tracking_test("Video Player (Full-screen)", duration)
    
    def test_game_mode(self, duration: int = 6):
        """Test cursor tracking in game-like applications."""
        print("\n=== Testing Game/Interactive Applications ===")
        print("Instructions:")
        print("1. Open a game or interactive application")
        print("2. Enter full-screen if available")
        print("3. Move your cursor around the application")
        print("4. Check if overlay follows cursor correctly")
        print("\nPress Enter when ready to start the test...")
        input()
        
        return self.run_tracking_test("Game/Interactive App", duration)
    
    def run_tracking_test(self, app_name: str, duration: int) -> Dict:
        """Run cursor tracking test for the specified duration."""
        print(f"\n--- Testing cursor tracking in {app_name} ---")
        print(f"Duration: {duration} seconds")
        print("🎯 Move your cursor around to test tracking accuracy")
        
        start_time = time.time()
        samples = []
        
        while time.time() - start_time < duration:
            # Get cursor position from different sources
            cursor_qt = QCursor.pos()
            cursor_tracked = get_cursor_position(include_screen_info=True)
            overlay_pos = self.overlay.pos() if self.overlay else None
            
            # Record sample
            sample = {
                "timestamp": time.time() - start_time,
                "cursor_qt": (cursor_qt.x(), cursor_qt.y()),
                "cursor_tracked": None,
                "overlay_pos": (overlay_pos.x(), overlay_pos.y()) if overlay_pos else None,
                "tracking_working": False,
                "position_accurate": False
            }
            
            if cursor_tracked:
                abs_x = cursor_tracked.screen_x + cursor_tracked.x
                abs_y = cursor_tracked.screen_y + cursor_tracked.y
                sample["cursor_tracked"] = (abs_x, abs_y)
                sample["tracking_working"] = True
                
                # Check position accuracy (within 15px tolerance for full-screen)
                qt_x, qt_y = sample["cursor_qt"]
                tracked_x, tracked_y = sample["cursor_tracked"]
                distance = ((qt_x - tracked_x) ** 2 + (qt_y - tracked_y) ** 2) ** 0.5
                sample["position_accurate"] = distance < 15
                sample["distance"] = distance
            
            samples.append(sample)
            time.sleep(0.1)  # 10 FPS sampling
            self.app.processEvents()
        
        # Analyze results
        total_samples = len(samples)
        tracking_samples = sum(1 for s in samples if s["tracking_working"])
        accurate_samples = sum(1 for s in samples if s["position_accurate"])
        
        tracking_rate = (tracking_samples / total_samples * 100) if total_samples > 0 else 0
        accuracy_rate = (accurate_samples / tracking_samples * 100) if tracking_samples > 0 else 0
        
        # Calculate average distance for accuracy samples
        distances = [s.get("distance", 0) for s in samples if s.get("distance") is not None]
        avg_distance = sum(distances) / len(distances) if distances else 0
        
        result = {
            "app": app_name,
            "duration": duration,
            "total_samples": total_samples,
            "tracking_samples": tracking_samples,
            "accurate_samples": accurate_samples,
            "tracking_rate": tracking_rate,
            "accuracy_rate": accuracy_rate,
            "avg_distance": avg_distance,
            "max_distance": max(distances) if distances else 0
        }
        
        print(f"  Results:")
        print(f"    Tracking rate: {tracking_rate:.1f}% ({tracking_samples}/{total_samples})")
        print(f"    Accuracy rate: {accuracy_rate:.1f}% ({accurate_samples}/{tracking_samples})")
        print(f"    Average distance: {avg_distance:.1f}px")
        print(f"    Max distance: {result['max_distance']:.1f}px")
        
        return result
    
    def test_manual_fullscreen_scenarios(self):
        """Test various full-screen scenarios manually."""
        print("\n🎮 Full-Screen Application Testing Suite")
        print("=" * 50)
        
        results = []
        
        try:
            # Test browser full-screen
            browser_result = self.test_browser_fullscreen()
            results.append(browser_result)
            
            # Test video full-screen
            video_result = self.test_video_fullscreen()
            results.append(video_result)
            
            # Test game/interactive apps
            game_result = self.test_game_mode()
            results.append(game_result)
            
        except KeyboardInterrupt:
            print("\n⚠ Testing interrupted by user")
        
        return results
    
    def generate_fullscreen_report(self, results: List[Dict]):
        """Generate report for full-screen testing."""
        print("\n" + "=" * 60)
        print("FULL-SCREEN APPLICATION CURSOR TRACKING REPORT")
        print("=" * 60)
        
        if not results:
            print("No test results to report.")
            return
        
        print(f"Total scenarios tested: {len(results)}")
        
        print(f"\nDetailed Results:")
        print("-" * 60)
        
        for result in results:
            app_name = result["app"]
            tracking_rate = result["tracking_rate"]
            accuracy_rate = result["accuracy_rate"]
            avg_distance = result["avg_distance"]
            
            # Determine status based on full-screen criteria
            if tracking_rate >= 90 and accuracy_rate >= 85:
                status = "✅ EXCELLENT"
            elif tracking_rate >= 75 and accuracy_rate >= 70:
                status = "✓ GOOD"
            elif tracking_rate >= 50:
                status = "⚠ FAIR"
            else:
                status = "❌ POOR"
            
            print(f"{app_name:25} {status:12}")
            print(f"{'':25} Track: {tracking_rate:5.1f}% | Acc: {accuracy_rate:5.1f}% | Avg Dist: {avg_distance:4.1f}px")
        
        # Analysis and recommendations
        print(f"\nAnalysis:")
        print("-" * 60)
        
        excellent_tests = [r for r in results if r["tracking_rate"] >= 90 and r["accuracy_rate"] >= 85]
        if excellent_tests:
            print("✅ Excellent performance in:")
            for test in excellent_tests:
                print(f"  - {test['app']}")
        
        poor_tests = [r for r in results if r["tracking_rate"] < 50]
        if poor_tests:
            print("❌ Poor performance in:")
            for test in poor_tests:
                print(f"  - {test['app']}: May need investigation")
        
        fair_tests = [r for r in results if 50 <= r["tracking_rate"] < 75]
        if fair_tests:
            print("⚠ Fair performance (could be improved):")
            for test in fair_tests:
                print(f"  - {test['app']}: Consider optimization")
        
        print(f"\nRecommendations:")
        print("-" * 60)
        print("• Full-screen applications may hide/show cursor differently")
        print("• Some games capture cursor exclusively (expected behavior)")
        print("• Video players may auto-hide cursor (normal behavior)")
        print("• Browser full-screen should work consistently")
        
        return results

def main():
    """Main function for full-screen testing."""
    tester = FullscreenTester()
    tester.create_test_overlay()
    
    try:
        results = tester.test_manual_fullscreen_scenarios()
        tester.generate_fullscreen_report(results)
    finally:
        if tester.overlay:
            tester.overlay.close()
        print("\n✓ Full-screen testing completed")

if __name__ == "__main__":
    main()