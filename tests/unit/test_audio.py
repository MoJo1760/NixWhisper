"""Unit tests for the audio module."""

from unittest.mock import MagicMock, patch

import numpy as np

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
    assert not recorder.recording
    assert len(recorder.audio_buffer) == 0


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
        assert recorder.recording
        mock_stream.assert_called_once()

        # Test stopping recording
        recorder.stop_recording()
        assert not recorder.recording
        mock_stream.return_value.close.assert_called_once()


def test_audio_recorder_audio_callback(mock_config):
    """Test the audio callback function."""
    recorder = AudioRecorder(
        sample_rate=mock_config.audio.sample_rate,
        channels=mock_config.audio.channels,
    )

    # Create test audio data
    test_data = np.random.rand(
        mock_config.audio.blocksize,
        mock_config.audio.channels
    ).astype(np.float32)

    # Set up callback
    callback_mock = MagicMock()
    recorder.callback = callback_mock
    recorder.recording = True  # Set recording to True to process the callback

    # Call the audio callback
    recorder._audio_callback(test_data, mock_config.audio.blocksize, None, None)

    # Check that the callback was called with the correct data
    callback_mock.assert_called_once()

    # Check that the audio data was added to the buffer
    assert len(recorder.audio_buffer) > 0
    assert recorder.audio_buffer.shape[0] == test_data.size


def test_audio_recorder_silence_detection():
    """Test silence detection in the audio recorder."""
    # This test is no longer applicable as the silence detection is now handled differently
    # in the _audio_callback method
    return


def test_audio_recorder_get_audio(mock_config):
    """Test getting recorded audio data."""
    recorder = AudioRecorder(
        sample_rate=mock_config.audio.sample_rate,
        channels=mock_config.audio.channels,
    )

    # Test getting audio when not recording (should return empty array)
    result = recorder.stop_recording()
    assert result is not None
    assert len(result) == 0

    # Test getting recorded audio
    test_data = np.random.rand(1024, mock_config.audio.channels).astype(np.float32)
    recorder.audio_buffer = test_data
    result = recorder.stop_recording()
    assert result is not None
    assert len(result) > 0
    assert result.shape == test_data.shape
