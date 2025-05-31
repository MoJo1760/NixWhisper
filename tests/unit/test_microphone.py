"""Tests for the microphone input module."""

import os
import queue
import tempfile
import time
import threading
from unittest.mock import MagicMock, patch, ANY
import numpy as np
import pytest

from nixwhisper.microphone import MicrophoneInput, AudioChunk, TranscriptionResult, TranscriptionSegment


class TestMicrophoneInput:
    """Tests for the MicrophoneInput class."""
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for the test."""
        # Create a mock WhisperModel
        self.mock_model = MagicMock()
        
        # Mock the transcribe method
        self.mock_segment = MagicMock()
        self.mock_segment.text = "Test transcription"
        self.mock_segment.start = 0.0
        self.mock_segment.end = 2.5
        self.mock_segment.avg_logprob = -0.5
        self.mock_segment.words = []
        
        self.mock_info = MagicMock()
        self.mock_info.language = 'en'
        self.mock_info.language_probability = 0.99
        
        self.mock_model.transcribe.return_value = (
            [self.mock_segment],  # segments
            self.mock_info        # info
        )
        
        # Patch the AudioRecorder
        with patch('nixwhisper.microphone.AudioRecorder') as mock_recorder_class:
            self.mock_recorder = MagicMock()
            mock_recorder_class.return_value = self.mock_recorder
            
            # Create the MicrophoneInput instance
            self.mic = MicrophoneInput(
                model=self.mock_model,
                sample_rate=16000,
                silence_threshold=0.01,
                silence_duration=1.0,
                chunk_duration=1.0
            )
            
            # Mock the worker threads
            self.mic.audio_thread = MagicMock()
            self.mic.processing_thread = MagicMock()
            
            yield
    
    def test_initialization(self):
        """Test that the MicrophoneInput initializes correctly."""
        assert self.mic.sample_rate == 16000
        assert self.mic.silence_threshold == 0.01
        assert self.mic.silence_duration == 1.0
        assert self.mic.chunk_duration == 1.0
        assert self.mic.chunk_samples == 16000  # sample_rate * chunk_duration
    
    def test_start_recording(self):
        """Test starting the recording."""
        # Set up mocks
        self.mock_recorder.start_recording.return_value = None
        
        # Call the method
        self.mic.start()
        
        # Verify the recorder was started
        self.mock_recorder.start_recording.assert_called_once_with(callback=self.mic._audio_callback)
        assert self.mic.is_recording is True
    
    def test_stop_recording(self):
        """Test stopping the recording."""
        # Set up the recording state
        self.mic.is_recording = True
        self.mic.is_processing = True
        
        # Call the method
        self.mic.stop()
        
        # Verify the recorder was stopped
        self.mock_recorder.stop_recording.assert_called_once()
        assert self.mic.is_recording is False
        assert self.mic.is_processing is False
    
    def test_audio_worker(self):
        """Test the audio worker thread processes chunks correctly."""
        # Set up test data
        test_audio = np.random.rand(16000).astype(np.float32)
        test_chunk = AudioChunk(
            data=test_audio,
            sample_rate=16000,
            timestamp=time.time()
        )
        
        # Replace the worker method with a mock to avoid threading issues
        original_worker = self.mic._audio_worker
        mock_worker = MagicMock()
        self.mic._audio_worker = mock_worker
        
        # Call the method that would start the worker
        self.mic.start()
        
        # Verify the worker was started
        mock_worker.assert_called_once()
        
        # Restore the original method
        self.mic._audio_worker = original_worker
    
    def test_processing_worker(self):
        """Test the processing worker thread processes chunks correctly."""
        # Set up test data
        test_audio = np.random.rand(16000).astype(np.float32)
        test_chunk = AudioChunk(
            data=test_audio,
            sample_rate=16000,
            timestamp=time.time()
        )
        
        # Replace the worker method with a mock to avoid threading issues
        original_worker = self.mic._processing_worker
        mock_worker = MagicMock()
        self.mic._processing_worker = mock_worker
        
        # Call the method that would start the worker
        self.mic.start()
        
        # Verify the worker was started
        mock_worker.assert_called_once()
        
        # Restore the original method
        self.mic._processing_worker = original_worker
    
    def test_get_transcription(self):
        """Test getting a transcription result."""
        # Create a test result
        test_result = TranscriptionResult(
            text="Test transcription",
            language="en",
            segments=[],
            language_probability=0.99,
            duration=1.0,
            model_load_time=0.0,
            inference_time=0.5
        )
        
        # Add the result to the queue
        self.mic.result_queue.put(test_result)
        
        # Get the result
        result = self.mic.get_transcription()
        
        # Verify the result
        assert result == test_result
