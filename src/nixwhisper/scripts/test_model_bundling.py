#!/usr/bin/env python3
"""Test script to verify model bundling functionality."""

import logging
import sys
import tempfile
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nixwhisper.model_manager import ModelManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_model_bundling():
    """Test that the model manager can use bundled models."""
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info("Using temporary directory: %s", temp_dir)

        # Initialize the model manager with the temp directory
        manager = ModelManager(cache_dir=Path(temp_dir) / "models")

        # Try to get the model path (should use bundled model if available)
        try:
            model_path = manager.get_model_path()
            logger.info("Successfully got model path: %s", model_path)

            # Verify the model directory exists and is not empty
            model_dir = Path(model_path)
            if not model_dir.exists():
                logger.error("Model directory does not exist!")
                return False

            if not any(model_dir.iterdir()):
                logger.error("Model directory is empty!")
                return False

            logger.info("Model directory contains files:")
            for f in model_dir.glob("*"):
                logger.info("  - %s", f.name)

            return True

        except Exception as e:
            logger.error("Error getting model path: %s", e, exc_info=True)
            return False

if __name__ == "__main__":
    if test_model_bundling():
        logger.info("✅ Model bundling test passed!")
        sys.exit(0)
    else:
        logger.error("❌ Model bundling test failed!")
        sys.exit(1)
