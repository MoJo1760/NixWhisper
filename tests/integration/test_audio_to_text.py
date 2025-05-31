"""Integration tests for audio recording and text transcription."""

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from nixwhisper.audio import AudioRecorder
from nixwhisper.whisper_model import WhisperTranscriber, TranscriptionResult


def create_test_audio_file(file_path: str, sample_rate: int = 16000, duration: float = 1.0) -> None:
    """Create a test audio file with a simple sine wave.
    
    Args:
        file_path: Path to save the audio file
        sample_rate: Sample rate in Hz
        duration: Duration in seconds
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio_data = np.sin(2 * np.pi * 440 * t) * 0.1  # 440 Hz sine wave
    sf.write(file_path, audio_data, sample_rate)


@pytest.mark.integration
class TestAudioToTextIntegration:
    """Integration tests for audio recording and text transcription."""
    
    @pytest.fixture
    def test_audio_file(self, tmp_path: Path) -> str:
        """Create a temporary test audio file."""
        audio_file = tmp_path / "test_audio.wav"
        create_test_audio_file(str(audio_file))
        return str(audio_file)
    
    @pytest.fixture
    def audio_recorder(self) -> AudioRecorder:
        """Create an AudioRecorder instance for testing."""
        return AudioRecorder(
            sample_rate=16000,
            channels=1,
            blocksize=1024,
        )
    
    @pytest.fixture
    def whisper_transcriber(self) -> WhisperTranscriber:
        """Create a WhisperTranscriber instance for testing."""
        return WhisperTranscriber(
            model_size="tiny",  # Use tiny model for faster tests
            device="cpu",
            compute_type="int8",
        )
    
    def test_record_and_transcribe(self, test_audio_file: str, audio_recorder: AudioRecorder, 
                                 whisper_transcriber: WhisperTranscriber) -> None:
        """Test recording audio and transcribing it with Whisper."""
        # Load the test audio file and ensure it's mono
        audio_data, sample_rate = sf.read(test_audio_file, dtype='float32')
        if len(audio_data.shape) > 1:  # Convert to mono if stereo
            audio_data = np.mean(audio_data, axis=1)
        
        # Ensure the audio is not silent
        audio_data = audio_data * 0.5  # Reduce volume to avoid clipping
        
        # Start recording
        audio_recorder.start_recording()
        
        # Simulate audio callback with test data
        # Process in chunks to simulate real recording
        chunk_size = 1024
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            audio_recorder._audio_callback(chunk.reshape(-1, 1), len(chunk), None, None)
        
        # Stop recording and get the audio
        recorded_audio = audio_recorder.stop_recording()
        assert len(recorded_audio) > 0, "No audio was recorded"
        
        # Ensure audio is in the correct format (mono)
        if len(recorded_audio.shape) > 1:
            recorded_audio = np.mean(recorded_audio, axis=1)
        
        # Transcribe the audio
        result = whisper_transcriber.transcribe(recorded_audio, sample_rate=sample_rate)
        
        # Check the result
        assert isinstance(result, TranscriptionResult)
        assert isinstance(result.text, str)
        
        # For the test audio, we might not get meaningful text, but we should get some output
        # Let's just check that the result is a valid TranscriptionResult
        assert hasattr(result, 'language'), "Result should have a language attribute"
        assert hasattr(result, 'segments'), "Result should have segments attribute"
    
    def test_silence_detection(self, audio_recorder: AudioRecorder) -> None:
        """Test silence detection in the audio recorder."""
        # Create silent audio data (below threshold)
        silent_audio = np.zeros((audio_recorder.blocksize, audio_recorder.channels), dtype=np.float32) + 0.001
        
        # Reset silence counter and recording state
        audio_recorder.silence_counter = 0
        audio_recorder.recording = True
        
        # Process silent audio - should increase silence counter
        audio_recorder._audio_callback(silent_audio, audio_recorder.blocksize, None, None)
        assert audio_recorder.silence_counter == 1, "Silence counter should increment for silent audio"
        
        # Create non-silent audio data (above threshold)
        non_silent_audio = np.random.rand(audio_recorder.blocksize, audio_recorder.channels).astype(np.float32) * 0.1
        
        # Process non-silent audio - should reset silence counter
        audio_recorder._audio_callback(non_silent_audio, audio_recorder.blocksize, None, None)
        assert audio_recorder.silence_counter == 0, "Silence counter should reset on non-silent audio"
    
    def test_whisper_model_loading(self, whisper_transcriber: WhisperTranscriber) -> None:
        """Test that the Whisper model loads correctly."""
        # Model should be loaded on first use
        # The model is lazy-loaded, so we need to perform a transcription to ensure it loads
        audio_data = np.random.rand(16000).astype(np.float32) * 0.1  # 1 second of noise
        result = whisper_transcriber.transcribe(audio_data, sample_rate=16000)
        assert isinstance(result, TranscriptionResult)
        assert isinstance(result.text, str)
    
    def test_transcription_with_timestamps(self, test_audio_file: str, 
                                          whisper_transcriber: WhisperTranscriber) -> None:
        """Test transcription with word-level timestamps."""
        # Load the test audio file and ensure it's mono
        audio_data, sample_rate = sf.read(test_audio_file, dtype='float32')
        if len(audio_data.shape) > 1:  # Convert to mono if stereo
            audio_data = np.mean(audio_data, axis=1)
        
        # Ensure the audio is not silent
        audio_data = audio_data * 0.5  # Reduce volume to avoid clipping
        
        # Transcribe with word timestamps
        result = whisper_transcriber.transcribe(
            audio_data, 
            sample_rate=sample_rate,
            word_timestamps=True
        )
        
        # Check the result
        assert isinstance(result, TranscriptionResult), "Result should be a TranscriptionResult"
        
        # For the test audio, we might not get meaningful text, but we should get a valid result
        assert hasattr(result, 'language'), "Result should have a language attribute"
        assert hasattr(result, 'segments'), "Result should have segments attribute"
        
        # If we have segments, check their structure
        if result.segments:
            segment = result.segments[0]
            assert hasattr(segment, 'start'), "Segment should have start time"
            assert hasattr(segment, 'end'), "Segment should have end time"
            
            # Check word timestamps if available
            if hasattr(segment, 'words') and segment.words:
                word = segment.words[0]
                assert hasattr(word, 'word'), "Word should have text"
                assert hasattr(word, 'start'), "Word should have start time"
                assert hasattr(word, 'end'), "Word should have end time"
