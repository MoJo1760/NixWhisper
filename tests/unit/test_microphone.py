"""Tests for the microphone input module."""

import time
from unittest.mock import MagicMock, patch

import numpy as np

from nixwhisper.microphone import MicrophoneInput, TranscriptionResult


class TestMicrophoneInput:
    """Test suite for MicrophoneInput class."""
    def __init__(self):
        """Initialize test case with mock objects."""
        # Mock model and transcription results
        self.mock_model = None
        self.mock_recorder = None
        self.mic = None

        # Mock callbacks
        self.on_transcription = None
        self.on_audio_chunk = None
        self.on_silence = None

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Set up mock model and transcription results
        self.mock_model = MagicMock()
        mock_segment = MagicMock(
            text="Test transcription",
            start=0.0,
            end=2.5,
            avg_logprob=-0.5
        )
        self.mock_model.transcribe.return_value = (
            [mock_segment],
            MagicMock(
                text="Test transcription",
                language="en",
                language_probability=0.99
            )
        )

        # Set up callbacks
        self.on_transcription = MagicMock()
        self.on_audio_chunk = MagicMock()
        self.on_silence = MagicMock()

        # Set up recorder
        with patch('nixwhisper.microphone.AudioRecorder') as recorder_class:
            self.mock_recorder = MagicMock()
            recorder_class.return_value = self.mock_recorder

            # Create microphone instance
            self.mic = MicrophoneInput(
                model=self.mock_model,
                on_transcription=self.on_transcription,
                on_audio_chunk=self.on_audio_chunk,
                on_silence=self.on_silence
            )

            # Mock the worker threads
            self.mic.audio_thread = MagicMock()
            self.mic.processing_thread = MagicMock()

    def test_initialization(self):
        """Test that the MicrophoneInput initializes correctly."""
        assert isinstance(self.mic, MicrophoneInput)
        assert self.mic.model == self.mock_model

    def test_start_recording(self):
        """Test starting the recording."""
        def mock_callback(frames, *_):
            return frames, True

        self.mock_recorder.audio_callback = mock_callback
        self.mic.start()
        time.sleep(0.1)
        self.mic.stop()

        assert self.on_audio_chunk.call_count > 0

    def test_stop_recording(self):
        """Test stopping the recording."""
        self.mic.start()
        time.sleep(0.1)
        self.mic.stop()

        assert not self.mic.is_recording
        assert not self.mic.is_processing

    def test_audio_callback(self):
        """Test audio callback processing.

        This test verifies that the internal audio callback correctly processes
        audio data and triggers the on_audio_chunk callback.
        """
        audio_data = np.zeros((1600,), dtype=np.float32)
        # Using _audio_callback directly as it's part of the test interface
        self.mic._audio_callback(audio_data, 0.0, False)
        self.on_audio_chunk.assert_called_once_with(
            audio_data,
            self.mic.sample_rate
        )

    def test_get_transcription(self):
        """Test getting transcription results."""
        # Create test result
        test_result = TranscriptionResult(
            text="Test transcription",
            segments=[],
            language="en",
            language_probability=0.99
        )

        # Add result to queue
        self.mic.result_queue.put(test_result)

        # Get result
        result = self.mic.get_transcription(timeout=0.1)
        assert result == test_result

    def test_transcription_callback(self):
        """Test that transcription callbacks work correctly.

        This test verifies that the internal transcription callback correctly
        processes and forwards transcription results.
        """
        # Using _on_transcription directly as it's part of the test interface
        self.mic._on_transcription = self.on_transcription

        # Create test result
        result = TranscriptionResult(
            text="Test transcription",
            segments=[],
            language="en",
            language_probability=0.99
        )

        # Add result to queue
        self.mic.result_queue.put(result)

        # Start processing to trigger callback
        self.mic.start()
        time.sleep(0.1)
        self.mic.stop()

        # Verify callback was called
        self.on_transcription.assert_called_once_with(result)
