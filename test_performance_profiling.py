#!/usr/bin/env python3
"""
Performance profiling for cursor position tracking in NixWhisper.
Tests CPU usage, memory consumption, and timing accuracy.
"""

import sys
sys.path.insert(0, 'src')

import time
import threading
import psutil
import statistics
from typing import List, Dict, Tuple
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout
from PyQt6.QtGui import QCursor, QColor
from PyQt6.QtCore import Qt, QTimer
from nixwhisper.qt_gui import OverlayWindow
from nixwhisper.x11_cursor import get_cursor_position, X11CursorTracker

class PerformanceProfiler:
    """Profile cursor tracking performance and resource usage."""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.overlay = None
        self.profiling_active = False
        self.profile_data = []
        
    def create_test_overlay(self):
        """Create overlay for performance testing."""
        if self.overlay:
            self.overlay.close()
        
        self.overlay = OverlayWindow()
        self.overlay.resize(200, 50)
        
        self.overlay.setStyleSheet("""
            background-color: rgba(0, 150, 255, 200);
            border: 1px solid white;
            border-radius: 5px;
            color: white;
            font-size: 11px;
            padding: 5px;
        """)
        
        layout = QVBoxLayout(self.overlay)
        title = QLabel("📊 Performance Test")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.overlay.show()
        self.overlay.enable_cursor_relative_positioning(True)
        self.overlay.set_cursor_offset(20, 20)
        
        print("✓ Performance test overlay created")
        return self.overlay
    
    def profile_cursor_tracking_function(self, iterations: int = 1000) -> Dict:
        """Profile the raw cursor tracking function performance."""
        print(f"\n--- Profiling cursor tracking function ({iterations} iterations) ---")
        
        # Warm up
        for _ in range(10):
            get_cursor_position()
        
        # Profile timing
        start_time = time.perf_counter()
        times = []
        
        for i in range(iterations):
            iter_start = time.perf_counter()
            position = get_cursor_position(include_screen_info=True)
            iter_end = time.perf_counter()
            
            iter_time = (iter_end - iter_start) * 1000  # Convert to milliseconds
            times.append(iter_time)
            
            # Brief pause every 100 iterations to prevent overwhelming
            if i % 100 == 0 and i > 0:
                time.sleep(0.001)
        
        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        min_time = min(times)
        max_time = max(times)
        stdev_time = statistics.stdev(times) if len(times) > 1 else 0
        
        # Calculate frequency
        avg_freq = 1000 / avg_time if avg_time > 0 else 0  # calls per second
        
        result = {
            "iterations": iterations,
            "total_time_ms": total_time,
            "avg_time_ms": avg_time,
            "median_time_ms": median_time,
            "min_time_ms": min_time,
            "max_time_ms": max_time,
            "stdev_time_ms": stdev_time,
            "avg_frequency_hz": avg_freq,
            "times": times[-100:]  # Keep last 100 samples for analysis
        }
        
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average time per call: {avg_time:.3f}ms")
        print(f"  Median time: {median_time:.3f}ms")
        print(f"  Min time: {min_time:.3f}ms")
        print(f"  Max time: {max_time:.3f}ms")
        print(f"  Standard deviation: {stdev_time:.3f}ms")
        print(f"  Average frequency: {avg_freq:.1f} Hz")
        
        return result
    
    def profile_cursor_tracker_class(self, duration: int = 30) -> Dict:
        """Profile the CursorTracker class performance."""
        print(f"\n--- Profiling CursorTracker class ({duration}s) ---")
        
        # Get initial system stats
        process = psutil.Process()
        initial_cpu = process.cpu_percent()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create tracker
        tracker = X11CursorTracker()
        callback_count = 0
        callback_times = []
        
        def test_callback(position):
            nonlocal callback_count, callback_times
            callback_count += 1
            callback_times.append(time.time())
        
        # Start tracking
        tracker.add_position_callback(test_callback)
        tracker.start_polling(interval=100)  # 100ms interval = 10 Hz
        
        start_time = time.time()
        cpu_samples = []
        memory_samples = []
        
        # Monitor for specified duration
        while time.time() - start_time < duration:
            time.sleep(0.5)  # Sample every 500ms
            
            # Get CPU and memory usage
            cpu_percent = process.cpu_percent()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            cpu_samples.append(cpu_percent)
            memory_samples.append(memory_mb)
            
            self.app.processEvents()
        
        # Stop tracking
        tracker.stop_polling()
        end_time = time.time()
        
        # Calculate callback frequency
        actual_duration = end_time - start_time
        callback_frequency = callback_count / actual_duration
        
        # Calculate timing accuracy
        expected_callbacks = int(actual_duration * 10)  # 10 Hz expected
        callback_accuracy = (callback_count / expected_callbacks * 100) if expected_callbacks > 0 else 0
        
        # Calculate resource usage
        avg_cpu = statistics.mean(cpu_samples) if cpu_samples else 0
        max_cpu = max(cpu_samples) if cpu_samples else 0
        avg_memory = statistics.mean(memory_samples) if memory_samples else 0
        max_memory = max(memory_samples) if memory_samples else 0
        memory_delta = avg_memory - initial_memory
        
        result = {
            "duration_s": actual_duration,
            "callback_count": callback_count,
            "expected_callbacks": expected_callbacks,
            "callback_frequency_hz": callback_frequency,
            "callback_accuracy_percent": callback_accuracy,
            "avg_cpu_percent": avg_cpu,
            "max_cpu_percent": max_cpu,
            "avg_memory_mb": avg_memory,
            "max_memory_mb": max_memory,
            "memory_delta_mb": memory_delta,
            "cpu_samples": cpu_samples,
            "memory_samples": memory_samples
        }
        
        print(f"  Duration: {actual_duration:.1f}s")
        print(f"  Callbacks received: {callback_count} (expected: {expected_callbacks})")
        print(f"  Callback frequency: {callback_frequency:.2f} Hz")
        print(f"  Timing accuracy: {callback_accuracy:.1f}%")
        print(f"  Average CPU usage: {avg_cpu:.2f}%")
        print(f"  Peak CPU usage: {max_cpu:.2f}%")
        print(f"  Average memory usage: {avg_memory:.1f} MB")
        print(f"  Memory delta: {memory_delta:+.2f} MB")
        
        return result
    
    def profile_overlay_performance(self, duration: int = 20) -> Dict:
        """Profile overlay positioning and rendering performance."""
        print(f"\n--- Profiling overlay performance ({duration}s) ---")
        
        if not self.overlay:
            self.create_test_overlay()
        
        # Get initial system stats
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.time()
        update_count = 0
        cpu_samples = []
        memory_samples = []
        
        # Simulate cursor movement for testing
        print("  Simulating cursor movement and overlay updates...")
        
        while time.time() - start_time < duration:
            # Simulate movement by setting cursor position
            current_time = time.time() - start_time
            
            # Create circular motion pattern for consistent testing
            angle = current_time * 2  # 2 radians per second
            center_x, center_y = 400, 400
            radius = 100
            
            x = int(center_x + radius * (1 + 0.5 * (angle % 6.28)))  # Vary radius
            y = int(center_y + radius * (1 + 0.5 * (angle % 6.28)))
            
            QCursor.setPos(x, y)
            update_count += 1
            
            # Sample system resources every 10 updates
            if update_count % 10 == 0:
                cpu_percent = process.cpu_percent()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                cpu_samples.append(cpu_percent)
                memory_samples.append(memory_mb)
            
            time.sleep(0.05)  # 20 FPS update rate
            self.app.processEvents()
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Calculate performance metrics
        update_frequency = update_count / actual_duration
        avg_cpu = statistics.mean(cpu_samples) if cpu_samples else 0
        max_cpu = max(cpu_samples) if cpu_samples else 0
        avg_memory = statistics.mean(memory_samples) if memory_samples else 0
        max_memory = max(memory_samples) if memory_samples else 0
        memory_delta = avg_memory - initial_memory
        
        result = {
            "duration_s": actual_duration,
            "update_count": update_count,
            "update_frequency_hz": update_frequency,
            "avg_cpu_percent": avg_cpu,
            "max_cpu_percent": max_cpu,
            "avg_memory_mb": avg_memory,
            "max_memory_mb": max_memory,
            "memory_delta_mb": memory_delta
        }
        
        print(f"  Duration: {actual_duration:.1f}s")
        print(f"  Updates: {update_count}")
        print(f"  Update frequency: {update_frequency:.2f} Hz")
        print(f"  Average CPU usage: {avg_cpu:.2f}%")
        print(f"  Peak CPU usage: {max_cpu:.2f}%")
        print(f"  Average memory usage: {avg_memory:.1f} MB")
        print(f"  Memory delta: {memory_delta:+.2f} MB")
        
        return result
    
    def profile_different_polling_rates(self) -> Dict:
        """Profile performance at different polling rates."""
        print(f"\n--- Profiling different polling rates ---")
        
        polling_rates = [50, 100, 200, 500, 1000]  # milliseconds
        results = {}
        
        for interval_ms in polling_rates:
            print(f"\n  Testing {interval_ms}ms interval ({1000/interval_ms:.1f} Hz)...")
            
            tracker = X11CursorTracker()
            callback_count = 0
            
            def count_callback(position):
                nonlocal callback_count
                callback_count += 1
            
            # Test for 10 seconds
            tracker.add_position_callback(count_callback)
            tracker.start_polling(interval=interval_ms)
            
            start_time = time.time()
            initial_cpu = psutil.Process().cpu_percent()
            
            time.sleep(10)  # Run for 10 seconds
            
            end_time = time.time()
            final_cpu = psutil.Process().cpu_percent()
            tracker.stop_polling()
            
            duration = end_time - start_time
            expected_callbacks = int(duration * 1000 / interval_ms)
            accuracy = (callback_count / expected_callbacks * 100) if expected_callbacks > 0 else 0
            
            results[interval_ms] = {
                "interval_ms": interval_ms,
                "target_hz": 1000 / interval_ms,
                "actual_callbacks": callback_count,
                "expected_callbacks": expected_callbacks,
                "accuracy_percent": accuracy,
                "cpu_usage_percent": final_cpu
            }
            
            print(f"    Callbacks: {callback_count}/{expected_callbacks} ({accuracy:.1f}%)")
            print(f"    CPU usage: {final_cpu:.2f}%")
        
        return results
    
    def generate_performance_report(self, function_profile: Dict, tracker_profile: Dict, 
                                  overlay_profile: Dict, polling_rates: Dict):
        """Generate comprehensive performance report."""
        print("\n" + "=" * 70)
        print("NIXWHISPER CURSOR TRACKING PERFORMANCE REPORT")
        print("=" * 70)
        
        print(f"\n📊 Function Performance:")
        print("-" * 40)
        print(f"Average call time: {function_profile['avg_time_ms']:.3f}ms")
        print(f"Maximum call time: {function_profile['max_time_ms']:.3f}ms")
        print(f"Theoretical max frequency: {function_profile['avg_frequency_hz']:.1f} Hz")
        
        print(f"\n🔄 Cursor Tracker Performance:")
        print("-" * 40)
        print(f"Callback accuracy: {tracker_profile['callback_accuracy_percent']:.1f}%")
        print(f"Average CPU usage: {tracker_profile['avg_cpu_percent']:.2f}%")
        print(f"Memory impact: {tracker_profile['memory_delta_mb']:+.2f} MB")
        
        print(f"\n🎨 Overlay Performance:")
        print("-" * 40)
        print(f"Update frequency: {overlay_profile['update_frequency_hz']:.2f} Hz")
        print(f"Average CPU usage: {overlay_profile['avg_cpu_percent']:.2f}%")
        print(f"Memory impact: {overlay_profile['memory_delta_mb']:+.2f} MB")
        
        print(f"\n⚡ Polling Rate Analysis:")
        print("-" * 40)
        for interval_ms, data in polling_rates.items():
            hz = data['target_hz']
            accuracy = data['accuracy_percent']
            cpu = data['cpu_usage_percent']
            print(f"{interval_ms:4d}ms ({hz:4.1f}Hz): {accuracy:5.1f}% accuracy, {cpu:5.2f}% CPU")
        
        # Recommendations
        print(f"\n💡 Performance Recommendations:")
        print("-" * 40)
        
        # Function performance assessment
        if function_profile['avg_time_ms'] < 1.0:
            print("✅ Function performance: Excellent (< 1ms average)")
        elif function_profile['avg_time_ms'] < 5.0:
            print("✓ Function performance: Good (< 5ms average)")
        else:
            print("⚠ Function performance: May need optimization")
        
        # CPU usage assessment
        if tracker_profile['avg_cpu_percent'] < 2.0:
            print("✅ CPU usage: Very low impact (< 2%)")
        elif tracker_profile['avg_cpu_percent'] < 5.0:
            print("✓ CPU usage: Low impact (< 5%)")
        else:
            print("⚠ CPU usage: Consider reducing polling frequency")
        
        # Memory usage assessment
        if abs(tracker_profile['memory_delta_mb']) < 5.0:
            print("✅ Memory usage: Minimal impact (< 5MB)")
        elif abs(tracker_profile['memory_delta_mb']) < 20.0:
            print("✓ Memory usage: Low impact (< 20MB)")
        else:
            print("⚠ Memory usage: Consider investigating memory leaks")
        
        # Optimal polling rate recommendation
        best_rate = None
        best_score = 0
        for interval_ms, data in polling_rates.items():
            # Score based on accuracy and CPU efficiency
            score = data['accuracy_percent'] - (data['cpu_usage_percent'] * 10)
            if score > best_score:
                best_score = score
                best_rate = interval_ms
        
        if best_rate:
            print(f"🎯 Recommended polling rate: {best_rate}ms ({1000/best_rate:.1f}Hz)")
        
        print(f"\n📈 Overall Assessment:")
        print("-" * 40)
        
        # Overall performance score
        function_score = min(100, 1000 / function_profile['avg_time_ms'])
        cpu_score = max(0, 100 - tracker_profile['avg_cpu_percent'] * 10)
        accuracy_score = tracker_profile['callback_accuracy_percent']
        
        overall_score = (function_score + cpu_score + accuracy_score) / 3
        
        if overall_score >= 85:
            print("🌟 Overall Performance: EXCELLENT")
        elif overall_score >= 70:
            print("✅ Overall Performance: GOOD")
        elif overall_score >= 50:
            print("✓ Overall Performance: ACCEPTABLE")
        else:
            print("⚠ Overall Performance: NEEDS IMPROVEMENT")
        
        print(f"   Performance Score: {overall_score:.1f}/100")
    
    def run_full_performance_suite(self):
        """Run comprehensive performance testing suite."""
        print("🚀 NixWhisper Performance Testing Suite")
        print("=" * 50)
        
        self.create_test_overlay()
        
        try:
            # Profile individual function
            function_profile = self.profile_cursor_tracking_function(1000)
            
            # Profile tracker class
            tracker_profile = self.profile_cursor_tracker_class(30)
            
            # Profile overlay performance
            overlay_profile = self.profile_overlay_performance(20)
            
            # Profile different polling rates
            polling_rates = self.profile_different_polling_rates()
            
            # Generate comprehensive report
            self.generate_performance_report(
                function_profile, tracker_profile, overlay_profile, polling_rates
            )
            
        finally:
            if self.overlay:
                self.overlay.close()
            print("\n✓ Performance testing completed")

def main():
    """Main function for performance profiling."""
    profiler = PerformanceProfiler()
    profiler.run_full_performance_suite()

if __name__ == "__main__":
    main()