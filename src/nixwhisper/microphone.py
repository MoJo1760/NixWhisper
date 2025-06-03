"""Real-time microphone input handling for NixWhisper."""

import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable

import numpy as np
from faster_whisper import WhisperModel

from .audio import AudioRecorder
from .transcriber.base import TranscriptionResult, TranscriptionSegment

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """Represents a chunk of audio data with timing information."""
    data: np.ndarray
    sample_rate: int
    timestamp: float


class MicrophoneInput:
    """Handles real-time microphone input and processing."""

    def __init__(self, model: WhisperModel, **kwargs):
        """Initialize the microphone input handler.

        Args:
            model: Loaded Whisper model for transcription
            **kwargs: Additional configuration options:
                sample_rate: Audio sample rate in Hz (default: 16000)
                channels: Number of audio channels (default: 1)
                device: Audio device ID (default: None)
                silence_threshold: RMS threshold for silence detection (default: 0.01)
                silence_duration: Duration of silence before stopping (default: 1.0)
                chunk_duration: Duration of each audio chunk to process (default: 1.0)
        """
        self.model = model
        self.sample_rate = kwargs.get('sample_rate', 16000)
        self.channels = kwargs.get('channels', 1)
        self.device = kwargs.get('device', None)
        self.silence_threshold = kwargs.get('silence_threshold', 0.01)
        self.silence_duration = kwargs.get('silence_duration', 1.0)
        self.chunk_duration = kwargs.get('chunk_duration', 1.0)
        self.chunk_samples = int(self.chunk_duration * self.sample_rate)

        # Audio processing state
        self.recorder = AudioRecorder(
            sample_rate=self.sample_rate,
            channels=self.channels,
            device=self.device,
            silence_threshold=self.silence_threshold,
            silence_duration=self.silence_duration
        )

        self.audio_queue: queue.Queue[AudioChunk] = queue.Queue()
        self.processing_queue: queue.Queue[AudioChunk] = queue.Queue()
        self.result_queue: queue.Queue[TranscriptionResult] = queue.Queue()

        self.is_recording = False
        self.is_processing = False
        self.audio_thread: Optional[threading.Thread] = None
        self.processing_thread: Optional[threading.Thread] = None

        # Callbacks
        self._on_transcription: Optional[Callable[[TranscriptionResult], None]] = None
        self._on_audio_chunk: Optional[Callable[[np.ndarray, int], None]] = None
        self._on_silence: Optional[Callable[[bool], None]] = None
    def start(self) -> None:
        """Start recording and processing audio."""
        if self.is_recording:
            return

        self.is_recording = True
        self.is_processing = True

        # Start audio recording thread
        self.audio_thread = threading.Thread(
            target=self._audio_worker,
            daemon=True
        )
        self.audio_thread.start()

        # Start processing thread
        self.processing_thread = threading.Thread(
            target=self._processing_worker,
            daemon=True
        )
        self.processing_thread.start()

        # Start audio recorder with callback
        self.recorder.start_recording(callback=self._audio_callback)
    def stop(self) -> None:
        """Stop recording and processing audio."""
        if not self.is_recording:
            return

        self.is_recording = False
        self.recorder.stop_recording()

        # Signal processing to stop
        self.is_processing = False

        # Wait for threads to finish
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)  # pylint: disable=no-member
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)  # pylint: disable=no-member

    def _audio_callback(self, audio_data: np.ndarray, _: float, is_silent: bool) -> None:
        """Callback for audio data from the recorder.

        Args:
            audio_data: Audio data as numpy array
            _: RMS value (unused)
            is_silent: Whether the audio is silent
        """
        if not self.is_recording:
            return

        # Notify about silence status
        if self._on_silence is not None:
            try:
                self._on_silence(is_silent)
            except (RuntimeError, ValueError) as e:
                logger.error("Error in silence callback: %s", e)

        # Add to queue for processing
        chunk = AudioChunk(
            data=audio_data,
            sample_rate=self.sample_rate,
            timestamp=time.time()
        )
        self.audio_queue.put(chunk)

        # Notify about new audio chunk
        if self._on_audio_chunk is not None:
            try:
                self._on_audio_chunk(audio_data, self.sample_rate)
            except (RuntimeError, ValueError) as e:
                logger.error("Error in audio chunk callback: %s", e)
    def _audio_worker(self) -> None:
        """Worker thread for processing audio chunks."""
        buffer = np.array([], dtype=np.float32)

        while self.is_recording or not self.audio_queue.empty():
            try:
                # Get next audio chunk with timeout
                chunk = self.audio_queue.get(timeout=0.1)
                buffer = np.append(buffer, chunk.data.flatten())

                # Process when we have enough samples
                while len(buffer) >= self.chunk_samples:
                    # Take a chunk
                    chunk_data = buffer[:self.chunk_samples]
                    buffer = buffer[self.chunk_samples:]

                    # Create chunk and add to processing queue
                    chunk = AudioChunk(
                        data=chunk_data,
                        sample_rate=self.sample_rate,
                        timestamp=time.time()
                    )
                    self.processing_queue.put(chunk)

                self.audio_queue.task_done()

            except queue.Empty:
                continue
            except (RuntimeError, ValueError, np.AxisError) as e:
                logger.error("Error in audio worker: %s", str(e))
    def _processing_worker(self) -> None:
        """Worker thread for processing audio chunks with the Whisper model."""
        while self.is_processing or not self.processing_queue.empty():
            try:
                # Get next chunk to process with timeout
                chunk = self.processing_queue.get(timeout=0.1)

                # Transcribe the audio chunk
                # Get language from config or default to English
                language = getattr(self.model, 'language', 'en')
                segments, info = self.model.transcribe(
                    chunk.data.astype(np.float32).reshape(1, -1),
                    sample_rate=chunk.sample_rate,
                    language=language,
                    task="transcribe",
                    word_timestamps=True
                )

                # Convert to our format using utility
                from ..utils.transcription import process_whisper_segments
                transcription_segments, full_text = process_whisper_segments(segments)

                # Create result
                if full_text:
                    result = TranscriptionResult(
                        text=" ".join(full_text).strip(),
                        language=info.language if hasattr(info, 'language') else "en",
                        segments=transcription_segments,
                        language_probability=getattr(info, 'language_probability', None),
                        duration=chunk.duration if hasattr(chunk, 'duration') else 0,
                        model_load_time=0,  # Already loaded
                        inference_time=time.time() - chunk.timestamp
                    )

                    # Notify about new transcription
                    if self._on_transcription is not None:
                        try:
                            self._on_transcription(result)
                        except (RuntimeError, ValueError) as e:
                            logger.error("Error in transcription callback: %s", str(e))

                    # Also add to result queue
                    self.result_queue.put(result)

                self.processing_queue.task_done()

            except queue.Empty:
                continue
            except (RuntimeError, ValueError, np.AxisError) as e:
                logger.error("Error in processing worker: %s", str(e))
    def get_transcription(self, timeout: Optional[float] = None) -> Optional[TranscriptionResult]:
        """Get the next available transcription result.
        
        Args:
            timeout: Maximum time to wait for a result (None to block)
            
        Returns:
            TranscriptionResult or None if no result is available
        """
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
