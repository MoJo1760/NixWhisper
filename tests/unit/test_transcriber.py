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
    TranscriberConfig,
    FasterWhisperTranscriber,
)


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
        assert kwargs == {
            'backend': 'faster-whisper',
            'model_size': 'small',
            'device': 'cuda',
            'compute_type': 'float16',
            'model_dir': Path('/tmp/models'),
            'beam_size': 5
        }


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
    """Tests for the FasterWhisperTranscriber class."""
    
    @pytest.fixture
    def mock_whisper_model(self):
        """Create a mock WhisperModel instance."""
        with patch('faster_whisper.WhisperModel') as mock_model:
            # Mock the transcribe method
            mock_instance = mock_model.return_value
            
            # Create a mock segment
            mock_segment = MagicMock()
            mock_segment.text = "Test transcription"
            mock_segment.start = 0.0
            mock_segment.end = 2.5
            mock_segment.avg_logprob = -0.5
            
            # Mock the transcribe method to return our mock segment
            mock_instance.transcribe.return_value = (
                [mock_segment],  # segments
                MagicMock(language='en', language_probability=0.99)  # info
            )
            
            yield mock_model
    
    def test_load_model(self, mock_whisper_model):
        """Test loading the Whisper model."""
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
        mock_whisper_model.assert_called_once_with(
            model_size_or_path="tiny",
            device="cpu",
            compute_type="int8",
            download_root=None
        )
    
    def test_transcribe_file(self, mock_whisper_model):
        """Test transcribing an audio file."""
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
            assert isinstance(result, dict)
            assert "text" in result
            assert result["text"] == "Test transcription"
            
            # Verify the model was called with the correct parameters
            mock_whisper_model.return_value.transcribe.assert_called_once()
            args, kwargs = mock_whisper_model.return_value.transcribe.call_args
            
            assert args[0] == temp_path
            assert kwargs["language"] == "en"
            
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
