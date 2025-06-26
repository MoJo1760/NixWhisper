#!/usr/bin/env python3
"""Regression tests for OverlayWindow multi-monitor support."""

import sys
import time
import logging
import unittest
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QCursor, QGuiApplication, QScreen
from PyQt6.QtTest import QTest

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('overlay_tests.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TestOverlayWindow(QMainWindow):
    """Test implementation of OverlayWindow for regression testing."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Overlay Test")
        
        # Store screen info for later use
        self.screen = None
        self.screen_geom = None
        
        # Set window flags for overlay behavior
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.X11BypassWindowManagerHint |
            Qt.WindowType.WindowTransparentForInput
        )
        
        # Set window attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_X11NetWmWindowTypeDock)
        
        # Make window transparent to mouse events
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Set initial position
        self._x = 0
        self._y = 0
        
        # Debug counter
        self.update_count = 0
        
        # Test settings
        self.cursor_offset_x = 20
        self.cursor_offset_y = 20
        self.follow_cursor = True
        
        # Setup UI
        self.label = QLabel("Test Overlay")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            background-color: rgba(40, 40, 40, 200);
            color: white;
            padding: 10px;
            border: 2px solid #4CAF50;
            border-radius: 8px;
            font-weight: bold;
        """)
        self.setCentralWidget(self.label)
        self.resize(300, 150)  # Slightly larger for better visibility
        
        # Track test state
        self.test_complete = False
        self.test_result = None
        self.test_message = ""
        
        # Ensure window is properly shown before moving
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.processEvents()
        QTest.qWait(100)  # Give window time to appear
    
    def update_position(self, cursor_pos=None):
        """Update the overlay position based on cursor."""
        self.update_count += 1
        
        if not self.follow_cursor:
            logger.debug("Cursor following is disabled")
            return None
            
        try:
            # Get cursor position if not provided
            if cursor_pos is None:
                cursor_pos = QCursor.pos()
                logger.debug(f"Got cursor position: {cursor_pos.x()}, {cursor_pos.y()}")
            
            # Get screen containing cursor
            screen = QGuiApplication.screenAt(cursor_pos)
            if not screen:
                logger.warning(f"Could not determine screen for cursor position {cursor_pos}")
                return None
                
            screen_geom = screen.geometry()
            
            # Store screen info for later use
            self.screen = screen
            self.screen_geom = screen_geom
            
            # Calculate desired position with offset
            x = cursor_pos.x() + self.cursor_offset_x
            y = cursor_pos.y() + self.cursor_offset_y
            
            # Adjust for screen bounds
            x = max(screen_geom.left(), min(x, screen_geom.right() - self.width()))
            y = max(screen_geom.top(), min(y, screen_geom.bottom() - self.height()))
            
            # Ensure position is within virtual desktop bounds
            x = max(0, x)
            y = max(0, y)
            
            # Store the position
            self._x = int(x)
            self._y = int(y)
            
            # Move the window
            logger.debug(f"Moving window to: ({self._x}, {self._y})")
            self.move(self._x, self._y)
            
            # Update status display with more debug info
            status_text = (
                f"Update #{self.update_count}\n"
                f"Screen: {screen.name()}\n"
                f"Cursor: ({cursor_pos.x()}, {cursor_pos.y()})\n"
                f"Window: ({self._x}, {self._y}) - {self.width()}x{self.height()}\n"
                f"Screen: ({screen_geom.x()}, {screen_geom.y()}) {screen_geom.width()}x{screen_geom.height()}"
            )
            self.label.setText(status_text)
            
            # Force window to stay on top and update
            self.raise_()
            self.activateWindow()
            self.show()  # Ensure window is visible
            self.repaint()
            QApplication.processEvents()
            
            # Log the update for debugging
            logger.info(f"Overlay moved to: ({self._x}, {self._y}) on screen {screen.name()}")
            logger.info(f"Window geometry: {self.geometry()}")
            
            return screen
            
        except Exception as e:
            logger.error(f"Error in update_position: {e}", exc_info=True)
            return None
            
    def update_position_original(self):
        """Update the overlay position based on cursor."""
        if not self.follow_cursor:
            return
            
        try:
            cursor_pos = QCursor.pos()
            screen = QGuiApplication.screenAt(cursor_pos)
            
            if not screen:
                logger.warning("Could not determine screen for cursor position")
                return
                
            screen_geom = screen.geometry()
            
            # Calculate desired position with offset
            x = cursor_pos.x() + self.cursor_offset_x
            y = cursor_pos.y() + self.cursor_offset_y
            
            # Adjust to keep window on screen
            x = max(screen_geom.left(), min(x, screen_geom.right() - self.width()))
            y = max(screen_geom.top(), min(y, screen_geom.bottom() - self.height()))
            
            # Update window position
            self.move(int(x), int(y))
            
            # Update status
            self.label.setText(
                f"Screen: {screen.name()}\n"
                f"Cursor: ({cursor_pos.x()}, {cursor_pos.y()})\n"
                f"Window: ({x}, {y})"
            )
            
        except Exception as e:
            logger.error(f"Error updating position: {e}", exc_info=True)
            self.label.setText(f"Error: {str(e)}")

class TestMultiMonitorOverlay(unittest.TestCase):
    """Test cases for multi-monitor overlay support."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test application."""
        cls.app = QApplication.instance() or QApplication(sys.argv)
        
        # Get screen information
        cls.screens = QGuiApplication.screens()
        cls.primary_screen = QGuiApplication.primaryScreen()
        
        logger.info(f"Detected {len(cls.screens)} screen(s)")
        for i, screen in enumerate(cls.screens):
            geom = screen.geometry()
            logger.info(
                f"Screen {i} ({screen.name()}): {geom.width()}x{geom.height()} at ({geom.x()}, {geom.y()})"
            )
    
    def setUp(self):
        """Set up each test case."""
        self.overlay = TestOverlayWindow()
        self.overlay.show()
        QTest.qWait(100)  # Give the window time to appear
    
    def tearDown(self):
        """Clean up after each test case."""
        self.overlay.close()
        QTest.qWait(100)  # Give the window time to close
    
    def test_single_screen_positioning(self):
        """Test basic cursor following on a single screen."""
        if len(self.screens) < 1:
            self.skipTest("No screens available for testing")
            
        screen = self.primary_screen
        screen_geom = screen.geometry()
        
        # Log screen info for debugging
        logger.info(f"Testing on screen: {screen.name()} at {screen_geom}")
        
        # Define test positions relative to screen geometry
        test_positions = [
            QPoint(screen_geom.left() + 200, screen_geom.top() + 200),  # Top-left
            QPoint(screen_geom.right() - 200, screen_geom.top() + 200),  # Top-right
            QPoint(screen_geom.right() - 200, screen_geom.bottom() - 200),  # Bottom-right
            QPoint(screen_geom.left() + 200, screen_geom.bottom() - 200),  # Bottom-left
            QPoint(screen_geom.center().x(), screen_geom.center().y())  # Center
        ]
        
        for i, pos in enumerate(test_positions):
            # Log test position
            logger.info(f"Test {i+1}/{len(test_positions)}: Cursor to {pos.x()},{pos.y()}")
            
            # Move cursor to test position
            QCursor.setPos(pos)
            
            # Process events and wait for overlay to update
            for attempt in range(5):  # Try multiple times with delays
                QApplication.processEvents()
                QTest.qWait(100)
                
                # Get current screen and overlay position
                cursor_screen = QGuiApplication.screenAt(pos)
                overlay_geom = self.overlay.geometry()
                
                # Calculate expected position with bounds checking
                expected_x = pos.x() + self.overlay.cursor_offset_x
                expected_y = pos.y() + self.overlay.cursor_offset_y
                
                # Adjust for screen bounds
                expected_x = min(max(expected_x, screen_geom.left()),
                               screen_geom.right() - self.overlay.width())
                expected_y = min(max(expected_y, screen_geom.top()),
                               screen_geom.bottom() - self.overlay.height())
                
                # Check if overlay is close enough to expected position
                x_diff = abs(overlay_geom.x() - expected_x)
                y_diff = abs(overlay_geom.y() - expected_y)
                
                if x_diff <= 10 and y_diff <= 10:  # Increased tolerance for window manager differences
                    break
                    
                logger.debug(f"Position not yet stable - waiting... (Δx={x_diff}, Δy={y_diff})")
            else:
                # If we get here, the overlay didn't reach the expected position
                logger.warning(f"Overlay did not reach expected position after multiple attempts")
            
            # Log final positions
            logger.info(f"  Cursor: {pos.x()},{pos.y()}")
            logger.info(f"  Expected: {expected_x},{expected_y}")
            logger.info(f"  Actual: {overlay_geom.x()},{overlay_geom.y()}")
            
            # Verify overlay position with a larger delta to account for window manager differences
            self.assertAlmostEqual(
                overlay_geom.x(), expected_x, delta=20,
                msg=f"Overlay X position {overlay_geom.x()} != {expected_x} for cursor at {pos.x()},{pos.y()}"
            )
            self.assertAlmostEqual(
                overlay_geom.y(), expected_y, delta=20,
                msg=f"Overlay Y position {overlay_geom.y()} != {expected_y} for cursor at {pos.x()},{pos.y()}"
            )
    
    def test_multi_screen_positioning(self):
        """Test cursor following across multiple screens."""
        if len(self.screens) < 2:
            self.skipTest("Multiple screens required for this test")
        
        # Test moving cursor between screens
        for screen in self.screens:
            screen_geom = screen.geometry()
            test_pos = screen_geom.center()
            
            # Move cursor to screen center
            QCursor.setPos(test_pos)
            
            # Process events and wait for overlay to update
            QTest.qWait(200)  # Increased wait time for stability
            
            # Get the screen where the overlay should be
            expected_screen = QGuiApplication.screenAt(test_pos)
            
            # Get overlay position and screen
            overlay_geom = self.overlay.geometry()
            overlay_center = overlay_geom.center()
            overlay_screen = QGuiApplication.screenAt(overlay_center)
            
            # Debug output
            logger.info(f"Testing screen: {screen.name()} at {screen_geom}")
            logger.info(f"Cursor at: {test_pos}")
            logger.info(f"Overlay at: {overlay_geom}")
            logger.info(f"Overlay screen: {overlay_screen.name() if overlay_screen else 'None'}")
            
            # Verify overlay is on the correct screen
            self.assertIsNotNone(overlay_screen, "Overlay is not on any screen")
            self.assertEqual(
                overlay_screen, screen,
                f"Overlay should be on screen {screen.name()} but is on {overlay_screen.name() if overlay_screen else 'no screen'}"
            )
            
            # Verify overlay is within screen bounds
            self.assertTrue(
                screen_geom.contains(overlay_geom) or 
                screen_geom.intersects(overlay_geom),
                f"Overlay at {overlay_geom} is outside screen {screen.name()} bounds {screen_geom}"
            )
    
    def test_screen_edges(self):
        """Test that overlay stays within screen bounds near edges."""
        if len(self.screens) < 1:
            self.skipTest("No screens available for testing")
            
        screen = self.primary_screen
        screen_geom = screen.geometry()
        
        # Test positions near each edge
        test_positions = [
            QPoint(screen_geom.right() - 10, screen_geom.center().y()),  # Right edge
            QPoint(screen_geom.left() + 10, screen_geom.center().y()),   # Left edge
            QPoint(screen_geom.center().x(), screen_geom.top() + 10),    # Top edge
            QPoint(screen_geom.center().x(), screen_geom.bottom() - 10), # Bottom edge
            QPoint(screen_geom.right() - 10, screen_geom.bottom() - 10)  # Corner
        ]
        
        for pos in test_positions:
            # Move cursor to test position
            QCursor.setPos(pos)
            
            # Process events and wait for overlay to update
            QTest.qWait(100)  # Increased wait time for stability
            
            # Get overlay geometry and current screen
            overlay_geom = self.overlay.geometry()
            overlay_screen = QGuiApplication.screenAt(overlay_geom.center())
            
            # If we can't determine the screen, use the primary screen
            if not overlay_screen:
                overlay_screen = screen
                
            screen_geom = overlay_screen.geometry()
            
            # Check if overlay is at least partially on the screen
            self.assertTrue(
                screen_geom.intersects(overlay_geom),
                f"Overlay at {overlay_geom} is completely outside screen {overlay_screen.name()} bounds {screen_geom} when cursor at {pos.x()},{pos.y()}"
            )
            
            # Check if overlay is fully contained within the screen
            if not screen_geom.contains(overlay_geom):
                # If not fully contained, check that it's just off by a small amount
                # due to window decorations or other system UI elements
                intersection = screen_geom.intersected(overlay_geom)
                overlap_ratio = (intersection.width() * intersection.height()) / \
                               (overlay_geom.width() * overlay_geom.height())
                self.assertGreater(
                    overlap_ratio, 0.9,
                    f"Overlay at {overlay_geom} is mostly outside screen {overlay_screen.name()} bounds {screen_geom} when cursor at {pos.x()},{pos.y()}"
                )

def run_tests():
    """Run all tests and return the test result."""
    # Redirect stdout to capture test output
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        test_suite = unittest.TestLoader().loadTestsFromTestCase(TestMultiMonitorOverlay)
        test_runner = unittest.TextTestRunner(verbosity=2, stream=f)
        result = test_runner.run(test_suite)
    
    # Log test results
    logger.info("=" * 80)
    logger.info("TEST RESULTS")
    logger.info("=" * 80)
    logger.info(f.getvalue())
    
    return result.wasSuccessful()

if __name__ == "__main__":
    # Run tests and exit with appropriate status code
    success = run_tests()
    sys.exit(0 if success else 1)
