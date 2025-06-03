#!/usr/bin/env python3
"""Script to download the default Whisper model for bundling with the package.

This script should be run during the build process to include the default model
with the package distribution.
"""

import argparse
import logging
import shutil
from pathlib import Path

from faster_whisper import WhisperModel

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_model(model_name: str, output_dir: Path) -> None:
    """Download a Whisper model to the specified directory.

    Args:
        model_name: Name of the model to download (e.g., 'base.en')
        output_dir: Directory to save the downloaded model
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading model '%s' to %s", model_name, output_dir)

    try:
        # This will download the model if it's not already in the cache
        WhisperModel(model_name, device="cpu", download_root=str(output_dir))
        logger.info("Successfully downloaded model: %s", model_name)
    except Exception as e:
        logger.error("Failed to download model %s: %s", model_name, e)
        raise

def main() -> None:
    """Main function to parse arguments and download the model."""
    parser = argparse.ArgumentParser(description="Download Whisper model for bundling")
    parser.add_argument(
        "--model",
        type=str,
        default="base.en",
        help="Name of the Whisper model to download (default: base.en)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "src" / "nixwhisper" / "models" / "base.en",
        help="Output directory for the downloaded model (default: src/nixwhisper/models/base.en)"
    )

    args = parser.parse_args()

    # Ensure the output directory exists
    args.output.mkdir(parents=True, exist_ok=True)

    # Download the model
    download_model(args.model, args.output)

if __name__ == "__main__":
    main()
