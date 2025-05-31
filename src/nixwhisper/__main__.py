#!/usr/bin/env python3
"""Main entry point for NixWhisper."""

import argparse
import logging
import sys
from typing import Optional, List

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

def main() -> int:
    """Run the NixWhisper application."""
    args = parse_args()
    setup_logging(args.debug)
    
    logger = logging.getLogger(__name__)
    
    # If CLI mode is explicitly requested, skip GUI check
    if args.cli:
        logger.info("Starting in CLI mode (--cli flag detected)")
        from .cli import main as cli_main
        return cli_main()
    
    # Try to import GUI components
    try:
        from .gui import main as gui_main
        logger.info("Starting in GUI mode")
        return gui_main()
    except ImportError as e:
        logger.warning("GUI components not available, falling back to CLI mode")
        logger.debug(f"GUI import error: {e}")
        from .cli import main as cli_main
        return cli_main()
    except Exception as e:
        logger.error(f"Error starting NixWhisper: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
