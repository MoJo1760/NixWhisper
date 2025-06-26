#!/usr/bin/env python3
"""
Diagnostic script to identify screen detection issues.
"""
import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('diagnose_screens')

def check_environment():
    """Check environment variables and display server."""
    logger.info("=== Environment Check ===")
    
    # Check display environment variable
    display = os.environ.get('DISPLAY')
    logger.info(f"DISPLAY environment variable: {display if display else 'Not set'}")
    
    # Check XAUTHORITY
    xauth = os.environ.get('XAUTHORITY')
    logger.info(f"XAUTHORITY environment variable: {xauth if xauth else 'Not set'}")
    
    # Check if running in a container
    in_container = os.path.exists('/.dockerenv') or os.environ.get('CONTAINER')
    logger.info(f"Running in container: {in_container}")

def check_qt_screens():
    """Check screen detection using Qt."""
    logger.info("\n=== Qt Screen Detection ===")
    
    try:
        # Initialize QApplication
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        
        # Get screens
        screens = app.screens()
        logger.info(f"Number of screens detected by Qt: {len(screens)}")
        
        for i, screen in enumerate(screens):
            geom = screen.geometry()
            logger.info(
                f"  Screen {i} ({screen.name()}): {geom.width()}x{geom.height()} "
                f"at ({geom.x()}, {geom.y()})"
            )
            logger.info(f"  Available geometry: {screen.availableGeometry()}")
            logger.info(f"  Logical DPI: {screen.logicalDotsPerInch():.1f}")
            logger.info(f"  Physical DPI: {screen.physicalDotsPerInch():.1f}")
            logger.info(f"  Device pixel ratio: {screen.devicePixelRatio()}")
            
        return len(screens) > 0
        
    except Exception as e:
        logger.error(f"Error checking Qt screens: {e}")
        return False

def check_x11():
    """Check X11 server accessibility."""
    logger.info("\n=== X11 Server Check ===")
    
    try:
        from Xlib.display import Display
        
        try:
            display = Display(os.environ.get('DISPLAY', ':0'))
            screen = display.screen()
            logger.info(f"X11 Server Info:")
            logger.info(f"  Display: {display.get_display_name()}")
            logger.info(f"  Screen: {screen.width_in_pixels}x{screen.height_in_pixels}")
            logger.info(f"  Root window: {screen.root}")
            display.close()
            return True
        except Exception as e:
            logger.error(f"X11 connection failed: {e}")
            return False
            
    except ImportError:
        logger.warning("python-xlib not installed. Install with: pip install python-xlib")
        return False

def main():
    """Run all diagnostic checks."""
    logger.info("Starting screen detection diagnostics...\n")
    
    # Run environment checks
    check_environment()
    
    # Check X11 server
    x11_ok = check_x11()
    
    # Check Qt screens
    qt_ok = check_qt_screens()
    
    # Print summary
    logger.info("\n=== Diagnostic Summary ===")
    logger.info(f"X11 Server Access: {'OK' if x11_ok else 'FAILED'}")
    logger.info(f"Qt Screen Detection: {'OK' if qt_ok else 'FAILED'}")
    
    if not qt_ok:
        logger.warning("\nQt is not detecting any screens. Possible causes:")
        logger.warning("1. Missing display server (X11/Wayland)")
        logger.warning("2. Incorrect DISPLAY environment variable")
        logger.warning("3. Missing X11 authentication")
        
    # Keep the window open if running in interactive mode
    if '--gui' in sys.argv:
        app = QApplication.instance() or QApplication(sys.argv)
        window = QWidget()
        window.setWindowTitle("Screen Diagnostics")
        
        layout = QVBoxLayout()
        
        summary = """
        <h2>Screen Diagnostics</h2>
        <p><b>X11 Server Access:</b> {x11_status}</p>
        <p><b>Qt Screen Detection:</b> {qt_status}</p>
        <p>Check the console for detailed information.</p>
        """.format(
            x11_status="<span style='color: green;'>OK</span>" if x11_ok else "<span style='color: red;'>FAILED</span>",
            qt_status="<span style='color: green;'>OK</span>" if qt_ok else "<span style='color: red;'>FAILED</span>"
        )
        
        label = QLabel(summary)
        label.setTextFormat(Qt.TextFormat.RichText)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(window.close)
        
        layout.addWidget(label)
        layout.addWidget(close_btn)
        
        window.setLayout(layout)
        window.show()
        
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
