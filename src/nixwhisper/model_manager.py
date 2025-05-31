"""Model management for NixWhisper."""

import importlib.resources
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Union

from faster_whisper import WhisperModel

# This is the default model that will be bundled with the application
DEFAULT_BUNDLED_MODEL = "base.en"


class ModelManager:
    """Manages Whisper model loading and caching."""

    def __init__(self, cache_dir: Optional[Union[str, Path]] = None):
        """Initialize the model manager.
        
        Args:
            cache_dir: Directory to cache downloaded models. 
                     Defaults to ~/.cache/nixwhisper/models
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "nixwhisper" / "models"
        self._ensure_cache_dir()
        self.logger = logging.getLogger(__name__)
        self.current_model = None
        self.current_model_path = None
        
        # Ensure the bundled model is available
        self._ensure_bundled_model()

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_bundled_model_path(self) -> Path:
        """Get the path to the bundled model.
        
        Returns:
            Path: Path to the bundled model directory
        """
        # This will be the path in the installed package
        return Path(importlib.resources.files('nixwhisper') / 'models' / DEFAULT_BUNDLED_MODEL)
    
    def _is_bundled_model_available(self) -> bool:
        """Check if the bundled model is available.
        
        Returns:
            bool: True if the bundled model is available, False otherwise
        """
        try:
            bundled_path = self._get_bundled_model_path()
            return bundled_path.exists() and any(bundled_path.iterdir())
        except Exception as e:
            self.logger.debug(f"Error checking for bundled model: {e}")
            return False
    
    def _ensure_bundled_model(self) -> None:
        """Ensure the bundled model is available in the cache.
        
        If the bundled model is not in the cache, it will be copied from the
        package resources to the cache directory.
        """
        # Skip if the model is already in the cache
        if (self.cache_dir / DEFAULT_BUNDLED_MODEL).exists():
            return
            
        # Try to copy from bundled models
        if self._is_bundled_model_available():
            bundled_path = self._get_bundled_model_path()
            target_path = self.cache_dir / DEFAULT_BUNDLED_MODEL
            self.logger.info(f"Copying bundled model to cache: {target_path}")
            
            try:
                # Copy the entire model directory
                shutil.copytree(bundled_path, target_path)
                self.logger.info("Successfully copied bundled model to cache")
            except Exception as e:
                self.logger.error(f"Failed to copy bundled model: {e}")
                # Fall back to downloading the model
                self.download_model(DEFAULT_BUNDLED_MODEL)
        else:
            # If no bundled model is available, download it
            self.download_model(DEFAULT_BUNDLED_MODEL)

    def get_default_model_name(self) -> str:
        """Get the name of the default model.
        
        Returns:
            str: Name of the default model (e.g., 'base.en')
        """
        return DEFAULT_BUNDLED_MODEL

    def get_model_path(self, model_name: Optional[str] = None) -> str:
        """Get the path to a model, using bundled model or downloading if necessary.
        
        Args:
            model_name: Name of the model to get. If None, uses the default.
            
        Returns:
            str: Path to the model directory
        """
        model_name = model_name or self.get_default_model_name()
        model_path = self.cache_dir / model_name
        
        # If the model doesn't exist, try to use bundled model or download
        if not model_path.exists():
            if model_name == DEFAULT_BUNDLED_MODEL and self._is_bundled_model_available():
                # If this is the default model and we have a bundled version, use it
                bundled_path = self._get_bundled_model_path()
                model_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(bundled_path, model_path)
                self.logger.info(f"Using bundled model: {model_name}")
            else:
                # Otherwise, download the model
                self.logger.info(f"Model {model_name} not found in cache. Downloading...")
                self.download_model(model_name)
            
        return str(model_path)

    def download_model(self, model_name: str) -> None:
        """Download a Whisper model.
        
        Args:
            model_name: Name of the model to download
            
        Raises:
            ValueError: If the model name is invalid
        """
        valid_models = ["tiny.en", "base.en", "small.en", "medium.en"]
        if model_name not in valid_models:
            raise ValueError(f"Invalid model name. Must be one of: {', '.join(valid_models)}")
            
        # This will trigger the download if the model isn't already cached
        # by the faster-whisper library
        try:
            WhisperModel(model_name, device="cpu", download_root=self.cache_dir)
            self.logger.info(f"Successfully downloaded model: {model_name}")
        except Exception as e:
            self.logger.error(f"Failed to download model {model_name}: {str(e)}")
            raise

    def load_model(self, model_name: Optional[str] = None, device: str = "auto") -> WhisperModel:
        """Load a Whisper model.
        
        Args:
            model_name: Name of the model to load. If None, uses the default.
            device: Device to load the model on ('cpu', 'cuda', or 'auto')
            
        Returns:
            WhisperModel: Loaded Whisper model
        """
        model_name = model_name or self.get_default_model_name()
        model_path = self.get_model_path(model_name)
        
        try:
            self.logger.info(f"Loading model: {model_name} on device: {device}")
            model = WhisperModel(model_path, device=device)
            self.current_model = model
            self.current_model_path = model_path
            return model
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise

    def get_available_models(self) -> list:
        """Get a list of available models in the cache.
        
        Returns:
            list: List of available model names
        """
        if not os.path.exists(self.cache_dir):
            return []
            
        return [d for d in os.listdir(self.cache_dir) 
                if os.path.isdir(os.path.join(self.cache_dir, d))]
