"""Audio capture and processing for NixWhisper."""

import queue
import threading
from typing import Optional, Tuple, Callable

import numpy as np
import sounddevice as sd


class AudioRecorder:
    """Handles audio recording and processing."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device: Optional[int] = None,
        blocksize: int = 1024,
        silence_threshold: float = 0.01,
        silence_duration: float = 2.0,
    ):
        """Initialize the audio recorder.

        Args:
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            device: Input device ID (None for default)
            blocksize: Audio block size
            silence_threshold: RMS threshold for silence detection
            silence_duration: Duration of silence before stopping (seconds)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self.blocksize = blocksize
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        
        self.recording = False
        self.audio_queue = queue.Queue()
        self.audio_buffer = np.array([], dtype=np.float32)
        self.stream = None
        self.recording_thread = None
        self.callback = None
        self.silence_counter = 0
        self.silence_samples = int(silence_duration * sample_rate / blocksize)

    def _audio_callback(self, indata, frames, time, status):
        """Callback function for audio stream."""
        if status:
            print(f"Audio status: {status}")
        
        if self.recording:
            # Calculate RMS of the current block
            rms = np.sqrt(np.mean(indata**2))
            
            # Update silence counter
            if rms < self.silence_threshold:
                self.silence_counter += 1
            else:
                self.silence_counter = 0
            
            # Add to buffer and notify
            self.audio_buffer = np.append(self.audio_buffer, indata)
            if self.callback:
                self.callback(indata, rms, self.silence_counter >= self.silence_samples)

    def start_recording(self, callback: Optional[Callable] = None):
        """Start recording audio.
        
        Args:
            callback: Optional callback function with signature:
                     callback(audio_data: np.ndarray, rms: float, is_silent: bool)
        """
        if self.recording:
            return
            
        self.callback = callback
        self.recording = True
        self.audio_buffer = np.array([], dtype=np.float32)
        self.silence_counter = 0
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            device=self.device,
            blocksize=self.blocksize,
            dtype=np.float32,
            callback=self._audio_callback
        )
        
        self.stream.start()

    def stop_recording(self) -> np.ndarray:
        """Stop recording and return the recorded audio.
        
        Returns:
            Recorded audio as a numpy array
        """
        if not self.recording:
            return self.audio_buffer
            
        self.recording = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        return self.audio_buffer

    def get_audio_data(self) -> np.ndarray:
        """Get the recorded audio data.
        
        Returns:
            Recorded audio as a numpy array
        """
        return self.audio_buffer

    def is_recording(self) -> bool:
        """Check if currently recording.
        
        Returns:
            True if recording, False otherwise
        """
        return self.recording
