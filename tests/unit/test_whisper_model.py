"""Unit tests for the whisper_model module."""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from nixwhisper.whisper_model import WhisperTranscriber, TranscriptionResult


@dataclass
class MockSegment:
    """Mock class for whisper.Segment"""
    text: str
    start: float = 0.0
    end: float = 1.0
    words: list = None


@dataclass
class MockWord:
    """Mock class for whisper.Word"""
    word: str
    start: float
    end: float
    probability: float = 0.9


def test_transcription_result_initialization():
    """Test that TranscriptionResult initializes correctly."""
    # Test with minimal arguments
    result = TranscriptionResult("test text")
    assert result.text == "test text"
    assert result.language is None
    assert result.segments == []
    
    # Test with all arguments
    segments = [MockSegment("test")]
    result = TranscriptionResult("test text", "en", segments)
    assert result.text == "test text"
    assert result.language == "en"
    assert result.segments == segments


def test_transcription_result_str():
    """Test the string representation of TranscriptionResult."""
    result = TranscriptionResult("test text", "en")
    assert str(result) == "test text"
    assert repr(result) == "TranscriptionResult(text='test text', language='en', segments=0)"


def test_whisper_transcriber_initialization(mock_config):
    """Test that WhisperTranscriber initializes with the correct settings."""
    with patch('nixwhisper.whisper_model.WhisperModel') as mock_model:
        transcriber = WhisperTranscriber(
            model_size=mock_config.model.name,
            device=mock_config.model.device,
            compute_type=mock_config.model.compute_type,
        )
        
        assert transcriber.model_size == mock_config.model.name
        assert transcriber.device == mock_config.model.device
        assert transcriber.compute_type == mock_config.model.compute_type
        assert transcriber.model is None
        assert not transcriber.is_loaded()


@patch('nixwhisper.whisper_model.WhisperModel')
def test_whisper_transcriber_load_model(mock_whisper_model, mock_config):
    """Test loading the Whisper model."""
    # Setup the mock model
    mock_model = MagicMock()
    mock_whisper_model.return_value = mock_model
    
    transcriber = WhisperTranscriber(
        model_size=mock_config.model.name,
        device=mock_config.model.device,
        compute_type=mock_config.model.compute_type,
    )
    
    # Test loading the model
    transcriber.load_model()
    
    # Check that the model was loaded with the correct parameters
    mock_whisper_model.assert_called_once_with(
        model_size_or_path=mock_config.model.name,
        device=mock_config.model.device,
        compute_type=mock_config.model.compute_type,
        download_root=None,
    )
    
    assert transcriber.is_loaded()
    
    # Reset the mock call count
    mock_whisper_model.reset_mock()
    
    # Test loading when model is already loaded
    transcriber.load_model()
    mock_whisper_model.assert_not_called()  # Should not call WhisperModel again


@patch('nixwhisper.whisper_model.WhisperModel')
def test_whisper_transcriber_transcribe_audio(mock_whisper_model, mock_config):
    """Test transcribing audio with the Whisper model."""
    # Set up mock model
    mock_model = MagicMock()
    
    # Create a mock info object with attributes
    class MockInfo:
        def __init__(self):
            self.language = 'en'
            self.language_probability = 0.99
    
    mock_info = MockInfo()
    
    mock_model.transcribe.return_value = (
        [MockSegment("test transcription")],
        mock_info
    )
    mock_whisper_model.return_value = mock_model
    
    transcriber = WhisperTranscriber(
        model_size=mock_config.model.name,
        device=mock_config.model.device,
        compute_type=mock_config.model.compute_type,
    )
    
    # Create test audio data
    sample_rate = mock_config.audio.sample_rate
    audio_data = np.random.rand(sample_rate * 5, 1).astype(np.float32)  # 5 seconds of audio
    
    # Test transcription
    result = transcriber.transcribe(audio_data, sample_rate=sample_rate)
    
    # Check that the model was called with the correct parameters
    mock_model.transcribe.assert_called_once()
    
    # Check the result
    assert isinstance(result, TranscriptionResult)
    assert result.text == "test transcription"
    assert result.language == "en"
    assert len(result.segments) == 1
    assert result.segments[0].text == "test transcription"


@patch('nixwhisper.whisper_model.WhisperModel')
def test_whisper_transcriber_transcribe_with_word_timestamps(mock_whisper_model, mock_config):
    """Test transcription with word timestamps."""
    # Set up mock model with word timestamps
    mock_segment = MockSegment(
        "test transcription",
        words=[
            MockWord("test", 0.0, 0.5),
            MockWord("transcription", 0.5, 1.0),
        ]
    )
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], {'language': 'en'})
    mock_whisper_model.return_value = mock_model
    
    transcriber = WhisperTranscriber(
        model_size=mock_config.model.name,
        device=mock_config.model.device,
        compute_type=mock_config.model.compute_type,
    )
    
    # Create test audio data
    sample_rate = mock_config.audio.sample_rate
    audio_data = np.random.rand(sample_rate * 5, 1).astype(np.float32)  # 5 seconds of audio
    
    # Test transcription with word timestamps
    result = transcriber.transcribe(
        audio_data,
        sample_rate=sample_rate,
        word_timestamps=True,
    )
    
    # Check that the model was called with word timestamps enabled
    call_kwargs = mock_model.transcribe.call_args[1]
    assert call_kwargs.get('word_timestamps') is True
    
    # Check the result
    assert isinstance(result, TranscriptionResult)
    assert result.text == "test transcription"
    assert len(result.segments) == 1
    assert len(result.segments[0].words) == 2
    assert result.segments[0].words[0].word == "test"
