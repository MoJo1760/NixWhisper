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
            model_name="tiny",  # Use tiny model for faster tests
            device="cpu",
            compute_type="int8",
        )
    
    def test_record_and_transcribe(self, test_audio_file: str, audio_recorder: AudioRecorder, 
                                 whisper_transcriber: WhisperTranscriber) -> None:
        """Test recording audio and transcribing it with Whisper."""
        # Load the test audio file
        audio_data, sample_rate = sf.read(test_audio_file, dtype='float32')
        
        # Simulate recording by adding audio data to the recorder's queue
        audio_recorder.audio_queue.put(audio_data)
        
        # Get the recorded audio
        recorded_audio = audio_recorder.get_audio()
        assert recorded_audio is not None
        
        # Transcribe the audio
        result = whisper_transcriber.transcribe(recorded_audio, sample_rate=sample_rate)
        
        # Check the result
        assert isinstance(result, TranscriptionResult)
        assert isinstance(result.text, str)
        
        # The transcription might not be accurate for the test audio,
        # but we should get some text back
        assert len(result.text) > 0
    
    def test_silence_detection(self, audio_recorder: AudioRecorder) -> None:
        """Test silence detection in the audio recorder."""
        # Create silent audio data (below threshold)
        silent_audio = np.zeros((16000, 1), dtype=np.float32) + 0.001
        
        # Check that it's detected as silent
        assert audio_recorder._is_silent(silent_audio)
        
        # Create non-silent audio data (above threshold)
        non_silent_audio = np.random.rand(16000, 1).astype(np.float32) * 0.1
        
        # Check that it's detected as non-silent
        assert not audio_recorder._is_silent(non_silent_audio)
    
    def test_whisper_model_loading(self, whisper_transcriber: WhisperTranscriber) -> None:
        """Test that the Whisper model loads correctly."""
        # Model should be loaded on first use
        assert whisper_transcriber.model is not None
        
        # Check model properties
        assert whisper_transcriber.model.device == "cpu"
        assert whisper_transcriber.model.compute_type == "int8"
    
    def test_transcription_with_timestamps(self, test_audio_file: str, 
                                          whisper_transcriber: WhisperTranscriber) -> None:
        """Test transcription with word-level timestamps."""
        # Load the test audio file
        audio_data, sample_rate = sf.read(test_audio_file, dtype='float32')
        
        # Transcribe with word timestamps
        result = whisper_transcriber.transcribe(
            audio_data, 
            sample_rate=sample_rate,
            word_timestamps=True
        )
        
        # Check the result
        assert isinstance(result, TranscriptionResult)
        assert len(result.text) > 0
        
        # Check that we got segments with timestamps
        assert len(result.segments) > 0
        segment = result.segments[0]
        assert segment.start >= 0
        assert segment.end > segment.start
        
        # Check for word timestamps if available
        if hasattr(segment, 'words') and segment.words:
            assert len(segment.words) > 0
            word = segment.words[0]
            assert word.start >= segment.start
            assert word.end <= segment.end
            assert len(word.word) > 0
