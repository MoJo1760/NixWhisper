#!/usr/bin/env python3
"""Main entry point for NixWhisper."""

import sys

def main():
    """Run the NixWhisper application."""
    # Import here to avoid loading everything when the module is imported
    from .cli import main as cli_main
    sys.exit(cli_main())

if __name__ == "__main__":
    main()
