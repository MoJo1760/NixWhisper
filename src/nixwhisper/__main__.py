#!/usr/bin/env python3
"""Main entry point for NixWhisper."""

import argparse
import logging
import sys
from typing import Optional, List, Callable, Tuple, Any

def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="NixWhisper - Offline Speech-to-Text")
    parser.add_argument(
        "--cli", 
        action="store_true",
        help="Force command-line interface mode (skip GUI)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(args)

def setup_logging(debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

def get_qt_gui_handler() -> Tuple[Optional[Callable], str]:
    """Get the Qt GUI handler if available."""
    try:
        from .qt_gui import run_qt_gui
        from .model_manager import ModelManager
        
        def qt_handler():
            run_qt_gui()
            return 0
            
        return qt_handler, "Qt"
    except ImportError as e:
        logging.warning(f"Qt GUI not available: {e}")
        return None, "Qt"

def main() -> int:
    """Run the NixWhisper application."""
    try:
        args = parse_args()
        setup_logging(args.debug)
        
        logger = logging.getLogger(__name__)
        
        # If CLI mode is explicitly requested, skip GUI check
        if args.cli:
            logger.info("Starting in CLI mode (--cli flag detected)")
            from .cli import main as cli_main
            return cli_main()
        
        # Try to use Qt GUI
        gui_handler, gui_name = get_qt_gui_handler()
        if gui_handler is not None:
            logger.info(f"Starting {gui_name} GUI")
            return gui_handler()
        
        # If no GUI is available, fall back to CLI
        logger.warning("No GUI available, falling back to CLI mode")
        from .cli import main as cli_main
        return cli_main()
    except Exception as e:
        logger.error(f"Error starting NixWhisper: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
