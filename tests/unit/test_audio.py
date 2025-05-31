"""Unit tests for the audio module."""

import numpy as np
import pytest
import sounddevice as sd
from unittest.mock import MagicMock, patch

from nixwhisper.audio import AudioRecorder


def test_audio_recorder_initialization(mock_config):
    """Test that AudioRecorder initializes with the correct settings."""
    recorder = AudioRecorder(
        sample_rate=mock_config.audio.sample_rate,
        channels=mock_config.audio.channels,
        device=mock_config.audio.device,
        blocksize=mock_config.audio.blocksize,
    )
    
    assert recorder.sample_rate == mock_config.audio.sample_rate
    assert recorder.channels == mock_config.audio.channels
    assert recorder.blocksize == mock_config.audio.blocksize
    assert not recorder.is_recording
    assert recorder.audio_queue.empty()


def test_audio_recorder_start_stop(mock_config):
    """Test that AudioRecorder starts and stops recording."""
    with patch('sounddevice.InputStream') as mock_stream:
        recorder = AudioRecorder(
            sample_rate=mock_config.audio.sample_rate,
            channels=mock_config.audio.channels,
        )
        
        # Test starting recording
        callback = MagicMock()
        recorder.start_recording(callback)
        assert recorder.is_recording
        mock_stream.assert_called_once()
        
        # Test stopping recording
        recorder.stop_recording()
        assert not recorder.is_recording
        mock_stream.return_value.close.assert_called_once()


def test_audio_recorder_audio_callback(mock_config):
    """Test the audio callback function."""
    recorder = AudioRecorder(
        sample_rate=mock_config.audio.sample_rate,
        channels=mock_config.audio.channels,
    )
    
    # Create test audio data
    test_data = np.random.rand(mock_config.audio.blocksize, mock_config.audio.channels).astype(np.float32)
    
    # Set up callback
    callback_mock = MagicMock()
    recorder.callback = callback_mock
    
    # Call the audio callback
    recorder._audio_callback(test_data, mock_config.audio.blocksize, None, None)
    
    # Check that the callback was called with the correct data
    callback_mock.assert_called_once()
    
    # Check that the audio data was added to the queue
    assert not recorder.audio_queue.empty()
    queued_data = recorder.audio_queue.get()
    np.testing.assert_array_equal(queued_data, test_data)


def test_audio_recorder_silence_detection(mock_config):
    """Test silence detection in the audio recorder."""
    recorder = AudioRecorder(
        sample_rate=mock_config.audio.sample_rate,
        channels=mock_config.audio.channels,
        silence_threshold=0.01,
        silence_duration=0.5,
    )
    
    # Create silent audio data (below threshold)
    silent_data = np.zeros((mock_config.audio.blocksize, mock_config.audio.channels), dtype=np.float32) + 0.005
    
    # Create non-silent audio data (above threshold)
    non_silent_data = np.zeros((mock_config.audio.blocksize, mock_config.audio.channels), dtype=np.float32) + 0.02
    
    # Test with silent audio
    assert recorder._is_silent(silent_data)
    
    # Test with non-silent audio
    assert not recorder._is_silent(non_silent_data)
    
    # Test silence duration detection
    with patch('time.time', side_effect=[0, 0.6, 1.2]):
        recorder._last_sound_time = 0
        assert not recorder._check_silence_duration()  # 0.6s < silence_duration (0.5s)
        assert recorder._check_silence_duration()  # 1.2s > silence_duration (0.5s)


def test_audio_recorder_get_audio(mock_config):
    """Test getting audio data from the recorder."""
    recorder = AudioRecorder(
        sample_rate=mock_config.audio.sample_rate,
        channels=mock_config.audio.channels,
    )
    
    # Add some test data to the queue
    test_data = np.random.rand(mock_config.audio.blocksize, mock_config.audio.channels).astype(np.float32)
    recorder.audio_queue.put(test_data)
    
    # Get the audio data
    result = recorder.get_audio()
    
    # Check that the data was retrieved correctly
    np.testing.assert_array_equal(result, test_data)
    
    # Test with empty queue
    assert recorder.get_audio() is None
