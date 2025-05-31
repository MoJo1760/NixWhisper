"""Model management for NixWhisper."""

import logging
import os
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel


class ModelManager:
    """Manages Whisper model loading and caching."""

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the model manager.
        
        Args:
            cache_dir: Directory to cache downloaded models. Defaults to ~/.cache/nixwhisper/models
        """
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/nixwhisper/models")
        self._ensure_cache_dir()
        self.logger = logging.getLogger(__name__)
        self.current_model = None
        self.current_model_path = None

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_default_model_name(self) -> str:
        """Get the name of the default model.
        
        Returns:
            str: Name of the default model (e.g., 'base.en')
        """
        return "base.en"

    def get_model_path(self, model_name: Optional[str] = None) -> str:
        """Get the path to a model, downloading it if necessary.
        
        Args:
            model_name: Name of the model to get. If None, uses the default.
            
        Returns:
            str: Path to the model directory
        """
        model_name = model_name or self.get_default_model_name()
        model_path = os.path.join(self.cache_dir, model_name)
        
        # If the model doesn't exist, download it
        if not os.path.exists(model_path):
            self.logger.info(f"Model {model_name} not found in cache. Downloading...")
            self.download_model(model_name)
            
        return model_path

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
