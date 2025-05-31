"""Tests for the transcriber module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import numpy as np

from nixwhisper.transcriber import (
    create_transcriber,
    get_available_backends,
)
from nixwhisper.transcriber.config import TranscriberConfig
from nixwhisper.transcriber.faster_whisper_backend import FasterWhisperTranscriber


class TestTranscriberConfig:
    """Tests for the TranscriberConfig class."""
    
    def test_default_config(self):
        """Test creating a config with default values."""
        config = TranscriberConfig()
        assert config.backend == "faster-whisper"
        assert config.model_size == "base"
        assert config.device == "auto"
        assert config.compute_type == "int8"
        assert config.model_dir is None
        assert config.advanced == {}
    
    def test_custom_config(self):
        """Test creating a config with custom values."""
        config = TranscriberConfig(
            backend="faster-whisper",
            model_size="small",
            device="cuda",
            compute_type="float16",
            model_dir="/tmp/models",
            advanced={"beam_size": 5}
        )
        assert config.backend == "faster-whisper"
        assert config.model_size == "small"
        assert config.device == "cuda"
        assert config.compute_type == "float16"
        assert str(config.model_dir) == "/tmp/models"
        assert config.advanced == {"beam_size": 5}
    
    def test_invalid_backend(self):
        """Test validation for invalid backend."""
        with pytest.raises(ValueError) as excinfo:
            TranscriberConfig(backend="invalid-backend")
        assert "Backend 'invalid-backend' is not available" in str(excinfo.value)
    
    def test_invalid_device(self):
        """Test validation for invalid device."""
        with pytest.raises(ValueError) as excinfo:
            TranscriberConfig(device="invalid-device")
        assert "Device must be one of: cpu, cuda, auto" in str(excinfo.value)
    
    def test_invalid_compute_type(self):
        """Test validation for invalid compute type."""
        with pytest.raises(ValueError) as excinfo:
            TranscriberConfig(compute_type="invalid-type")
        assert "Compute type must be one of: int8, float16, float32" in str(excinfo.value)
    
    def test_invalid_model_size(self):
        """Test validation for invalid model size."""
        with pytest.raises(ValueError) as excinfo:
            TranscriberConfig(model_size="huge")
        assert "Model size must be one of: tiny, base, small, medium, large, large-v2, large-v3" in str(excinfo.value)
    
    def test_to_transcriber_kwargs(self):
        """Test converting config to transcriber kwargs."""
        config = TranscriberConfig(
            backend="faster-whisper",
            model_size="small",
            device="cuda",
            compute_type="float16",
            model_dir="/tmp/models",
            advanced={"beam_size": 5}
        )
        kwargs = config.to_transcriber_kwargs()
        
        # Check all keys and values except model_dir
        expected = {
            'backend': 'faster-whisper',
            'model_size': 'small',
            'device': 'cuda',
            'compute_type': 'float16',
            'beam_size': 5
        }
        
        # Get the model_dir and check if it's a Path object or a string that can be converted to Path
        model_dir = kwargs.pop('model_dir')
        assert str(Path(model_dir)) == str(Path('/tmp/models'))
        
        # Check the rest of the dictionary
        assert kwargs == expected


class TestCreateTranscriber:
    """Tests for the create_transcriber function."""
    
    def test_create_default_transcriber(self):
        """Test creating a transcriber with default settings."""
        transcriber = create_transcriber()
        assert isinstance(transcriber, FasterWhisperTranscriber)
        assert transcriber.model_size == "base"
        assert transcriber.device == "auto"
        assert transcriber.compute_type == "int8"
    
    def test_create_custom_transcriber(self):
        """Test creating a transcriber with custom settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            transcriber = create_transcriber(
                backend="faster-whisper",
                model_size="small",
                device="cpu",
                compute_type="float32",
                model_dir=temp_dir,
                beam_size=5
            )
            
            assert isinstance(transcriber, FasterWhisperTranscriber)
            assert transcriber.model_size == "small"
            assert transcriber.device == "cpu"
            assert transcriber.compute_type == "float32"
    
    def test_get_available_backends(self):
        """Test getting available backends."""
        backends = get_available_backends()
        assert isinstance(backends, dict)
        assert "faster-whisper" in backends
        assert backends["faster-whisper"] == FasterWhisperTranscriber


class TestFasterWhisperTranscriber:
    """Test the FasterWhisperTranscriber class."""
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks for all tests in this class."""
        self.mock_model_patcher = patch('nixwhisper.transcriber.faster_whisper_backend.WhisperModel')
        self.mock_model_class = self.mock_model_patcher.start()
        self.mock_model_instance = MagicMock()
        self.mock_model_class.return_value = self.mock_model_instance
        
        # Create a mock segment
        self.mock_segment = MagicMock()
        self.mock_segment.text = "Test transcription"
        self.mock_segment.start = 0.0
        self.mock_segment.end = 2.5
        self.mock_segment.avg_logprob = -0.5
        
        # Mock the transcribe method to return our mock segment
        self.mock_model_instance.transcribe.return_value = (
            [self.mock_segment],  # segments
            MagicMock(language='en', language_probability=0.99)  # info
        )
        
        yield
        
        # Clean up patches
        self.mock_model_patcher.stop()
    
    def test_load_model(self):
        """Test loading the Whisper model."""
        # Reset the mock call count
        self.mock_model_class.reset_mock()
        
        transcriber = FasterWhisperTranscriber(
            model_size="tiny",
            device="cpu",
            compute_type="int8"
        )
        
        # Model should not be loaded initially
        assert not transcriber.is_loaded
        
        # Load the model
        transcriber.load_model()
        
        # Model should now be loaded
        assert transcriber.is_loaded
        
        # Verify the model was created with the correct parameters
        self.mock_model_class.assert_called_once_with(
            "tiny",  # model_size is passed as a positional argument
            device="cpu",
            compute_type="int8",
            download_root=None
        )
    
    def test_transcribe_file(self):
        """Test transcribing an audio file."""
        # Create a test segment
        mock_segment = MagicMock()
        mock_segment.text = "Test transcription"
        mock_segment.start = 0.0
        mock_segment.end = 2.5
        mock_segment.avg_logprob = -0.5
        
        # Mock the transcribe method to return our test segment
        self.mock_model_instance.transcribe.return_value = (
            [mock_segment],  # segments
            MagicMock(language='en', language_probability=0.99)  # info
        )
        
        transcriber = FasterWhisperTranscriber(
            model_size="tiny",
            device="cpu",
            compute_type="int8"
        )
        
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Transcribe the file
            result = transcriber.transcribe(temp_path, language="en")
            
            # Verify the result
            assert hasattr(result, 'text')
            assert result.text == "Test transcription"
            
            # Verify the model was called with the correct parameters
            self.mock_model_instance.transcribe.assert_called_once()
            
            # Get the args and kwargs passed to transcribe
            args, kwargs = self.mock_model_instance.transcribe.call_args
            
            # The first argument should be the file path
            assert args[0] == temp_path
            
            # Verify language parameter
            assert kwargs["language"] == "en"
            
            # Verify other default parameters
            assert kwargs["task"] == "transcribe"
            assert kwargs["beam_size"] == 5
            assert kwargs["vad_filter"] is True
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_supported_languages(self):
        """Test getting supported languages."""
        transcriber = FasterWhisperTranscriber()
        languages = transcriber.supported_languages
        
        # Should return a list of language codes
        assert isinstance(languages, list)
        assert len(languages) > 0
        assert all(isinstance(lang, str) for lang in languages)
        
        # Should include common languages
        assert "en" in languages  # English
        assert "es" in languages  # Spanish
        assert "fr" in languages  # French
        assert "de" in languages  # German
