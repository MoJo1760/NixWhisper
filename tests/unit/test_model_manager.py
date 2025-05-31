"""Tests for the model manager module."""

import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from nixwhisper.model_manager import ModelManager


class TestModelManager:
    """Tests for the ModelManager class."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def model_manager(self, temp_cache_dir):
        """Create a ModelManager instance with a temporary cache directory."""
        return ModelManager(cache_dir=temp_cache_dir)
    
    def test_default_model_name(self, model_manager):
        """Test getting the default model name."""
        assert model_manager.get_default_model_name() == "base.en"
    
    @patch('nixwhisper.model_manager.WhisperModel')
    def test_download_model_success(self, mock_whisper, model_manager):
        """Test successful model download."""
        model_name = "tiny.en"
        
        # Create the model directory to simulate successful download
        model_dir = os.path.join(model_manager.cache_dir, model_name)
        os.makedirs(model_dir, exist_ok=True)
        
        # Call the method
        model_manager.download_model(model_name)
        
        # Verify WhisperModel was called with correct parameters
        mock_whisper.assert_called_once_with(
            model_name,
            device="cpu",
            download_root=model_manager.cache_dir
        )
    
    def test_download_model_invalid_name(self, model_manager):
        """Test downloading an invalid model name raises an error."""
        with pytest.raises(ValueError):
            model_manager.download_model("invalid-model")
    
    @patch('nixwhisper.model_manager.WhisperModel')
    def test_get_model_path_downloads_if_not_exists(self, mock_whisper, model_manager):
        """Test that get_model_path downloads the model if it doesn't exist."""
        model_name = "small.en"
        model_path = model_manager.get_model_path(model_name)
        
        # Should have called download_model
        mock_whisper.assert_called_once()
        assert model_path == os.path.join(model_manager.cache_dir, model_name)
    
    @patch('nixwhisper.model_manager.WhisperModel')
    def test_load_model(self, mock_whisper, model_manager):
        """Test loading a model."""
        model_name = "base.en"
        mock_model = MagicMock()
        mock_whisper.return_value = mock_model
        
        # Create the model directory to simulate that it's already downloaded
        model_dir = os.path.join(model_manager.cache_dir, model_name)
        os.makedirs(model_dir, exist_ok=True)
        
        # Test loading with default parameters
        model = model_manager.load_model(model_name, device="cpu")
        
        # Verify the model was loaded with correct parameters
        mock_whisper.assert_called_once_with(
            model_dir,
            device="cpu"
        )
        assert model == mock_model
        assert model_manager.current_model == mock_model
        assert model_manager.current_model_path == model_dir
    
    def test_get_available_models(self, model_manager, temp_cache_dir):
        """Test getting a list of available models."""
        # Create some dummy model directories
        os.makedirs(os.path.join(temp_cache_dir, "tiny.en"), exist_ok=True)
        os.makedirs(os.path.join(temp_cache_dir, "base.en"), exist_ok=True)
        
        # Create a file that should be ignored
        with open(os.path.join(temp_cache_dir, "not_a_model.txt"), 'w') as f:
            f.write("test")
        
        # Get available models
        models = model_manager.get_available_models()
        
        # Should only return directories, not files
        assert set(models) == {"tiny.en", "base.en"}
    
    def test_ensure_cache_dir_created(self, temp_cache_dir):
        """Test that the cache directory is created if it doesn't exist."""
        # Remove the temp dir to test creation
        if os.path.exists(temp_cache_dir):
            shutil.rmtree(temp_cache_dir)
        
        # This should create the directory
        manager = ModelManager(cache_dir=temp_cache_dir)
        
        assert os.path.exists(manager.cache_dir)
        assert os.path.isdir(manager.cache_dir)
