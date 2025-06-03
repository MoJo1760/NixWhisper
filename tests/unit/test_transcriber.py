"""Tests for the transcriber module."""
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from nixwhisper.transcriber import create_transcriber, get_available_backends
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
        assert (
            "Model size must be one of: tiny, base, small, medium, large, "
            "large-v2, large-v3"
        ) in str(excinfo.value)

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
        expected = {
            'backend': 'faster-whisper',
            'model_size': 'small',
            'device': 'cuda',
            'compute_type': 'float16',
            'beam_size': 5
        }
        model_dir = kwargs.pop('model_dir')
        assert str(Path(model_dir)) == str(Path('/tmp/models'))
        assert kwargs == expected

    def test_to_transcriber_kwargs_model_dir(self):
        """Test converting config to transcriber kwargs with model_dir."""
        config = TranscriberConfig(
            backend="faster-whisper",
            model_size="small",
            device="cuda",
            compute_type="float16",
            model_dir="/tmp/models",
            advanced={"beam_size": 5}
        )
        kwargs = config.to_transcriber_kwargs()
        expected = {
            'backend': 'faster-whisper',
            'model_size': 'small',
            'device': 'cuda',
            'compute_type': 'float16',
            'beam_size': 5
        }
        model_dir = kwargs.pop('model_dir')
        assert str(Path(model_dir)) == str(Path('/tmp/models'))
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


@pytest.fixture
def mock_whisper_model():
    """Setup mock Whisper model."""
    with patch('nixwhisper.transcriber.faster_whisper_backend.WhisperModel') as mock_model_class:
        mock_model_instance = MagicMock()
        mock_model_class.return_value = mock_model_instance

        # Create a mock segment
        mock_segment = MagicMock()
        mock_segment.text = "Test transcription"
        mock_segment.start = 0.0
        mock_segment.end = 2.5
        mock_segment.avg_logprob = -0.5

        # Mock the transcribe method
        mock_model_instance.transcribe.return_value = (
            [mock_segment],
            MagicMock(language='en', language_probability=0.99)
        )

        yield mock_model_instance


class TestFasterWhisperTranscriber:
    """Test the FasterWhisperTranscriber class."""
    def test_load_model(self):
        """Test loading the Whisper model."""
        with patch('nixwhisper.transcriber.faster_whisper_backend.WhisperModel'):
            transcriber = FasterWhisperTranscriber(
                model_size="tiny",
                device="cpu",
                compute_type="int8"
            )
            assert not transcriber.is_loaded
            transcriber.load_model()
            assert transcriber.is_loaded

    def test_transcribe_file(self):
        """Test transcribing an audio file."""
        with patch(
            'nixwhisper.transcriber.faster_whisper_backend.WhisperModel'
        ) as mock:
            transcriber = FasterWhisperTranscriber(
                model_size="tiny",
                device="cpu",
                compute_type="int8"
            )
            mock_segment = MagicMock(
                text="Test transcription",
                start=0.0,
                end=2.5,
                avg_logprob=-0.5
            )
            mock.return_value.transcribe.return_value = (
                [mock_segment],
                MagicMock(language='en', language_probability=0.99)
            )
            with tempfile.NamedTemporaryFile(
                suffix='.wav', delete=False
            ) as temp_file:
                temp_path = temp_file.name
            try:
                # Test file path transcription
                result = transcriber.transcribe(temp_path, language="en")
                assert hasattr(result, 'text')
                assert result.text == "Test transcription"
                args, kwargs = mock.return_value.transcribe.call_args
                assert args[0] == temp_path
                assert kwargs["language"] == "en"
                assert kwargs["task"] == "transcribe"
                assert kwargs["beam_size"] == 5
                assert kwargs["vad_filter"] is True
                # Test raw bytes transcription
                mock.return_value.transcribe.reset_mock()
                test_audio_data = b'\x00\x01\x02\x03'
                result = transcriber.transcribe(
                    test_audio_data, language="es"
                )
                assert hasattr(result, 'text')
                assert result.text == "Test transcription"
                args, kwargs = mock.return_value.transcribe.call_args
                assert isinstance(args[0], np.ndarray)
                assert args[0].dtype == np.float32
                assert kwargs["language"] == "es"
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def test_supported_languages(self):
        """Test getting supported languages."""
        transcriber = FasterWhisperTranscriber()
        languages = transcriber.supported_languages
        assert isinstance(languages, list)
        assert len(languages) > 0
        assert all(isinstance(lang, str) for lang in languages)
        assert all(lang in languages for lang in ["en", "es", "fr", "de"])
