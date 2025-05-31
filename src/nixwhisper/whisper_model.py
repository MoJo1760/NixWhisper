"""Whisper model integration for NixWhisper."""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np
import torch
from faster_whisper import WhisperModel


@dataclass
class TranscriptionSegment:
    """A single segment of a transcription."""
    start: float
    end: float
    text: str
    words: Optional[List[dict]] = None
    speaker: Optional[str] = None
    confidence: Optional[float] = None


class TranscriptionResult:
    """Container for transcription results."""
    
    def __init__(self, text: str, language: Optional[str] = None, segments=None, **kwargs):
        self.text = text
        self.language = language
        self.segments = []
        
        # Convert segments to objects with attributes if they're dictionaries
        if segments is not None:
            for segment in segments:
                if isinstance(segment, dict):
                    # Convert dictionary to an object with attributes
                    segment_obj = type('Segment', (), segment)
                    # Convert words if they exist
                    if 'words' in segment and segment['words'] is not None:
                        words = []
                        for word in segment['words']:
                            if isinstance(word, dict):
                                words.append(type('Word', (), word))
                            else:
                                words.append(word)
                        segment_obj.words = words
                    self.segments.append(segment_obj)
                else:
                    self.segments.append(segment)
        
        self.language_probability = kwargs.get('language_probability')
        self.duration = kwargs.get('duration', 0.0)
        self.model_load_time = kwargs.get('model_load_time', 0.0)
        self.inference_time = kwargs.get('inference_time', 0.0)
    
    def __str__(self):
        return self.text
        
    def __repr__(self):
        return f"TranscriptionResult(text='{self.text}', language='{self.language}', segments={len(self.segments)})"


class WhisperTranscriber:
    """Handles Whisper model loading and audio transcription."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
        model_dir: Optional[Union[str, Path]] = None,
    ):
        """Initialize the Whisper transcriber.

        Args:
            model_size: Model size (tiny, base, small, medium, large)
            device: Device to use (cpu, cuda, auto)
            compute_type: Compute type (int8, float16, float32)
            model_dir: Directory to store downloaded models
        """
        self.model_size = model_size
        self.device = device.lower()
        self.compute_type = compute_type
        self.model_dir = str(model_dir) if model_dir else None
        self.model = None
        self.loaded_model_size = None
        self.load_time = 0.0

    def is_loaded(self) -> bool:
        """Check if the model is loaded.
        
        Returns:
            bool: True if the model is loaded, False otherwise
        """
        return self.model is not None and self.loaded_model_size == self.model_size
        
    def load_model(self):
        """Load the Whisper model.
        
        The model will only be loaded if it hasn't been loaded yet or if the model size has changed.
        """
        if self.is_loaded():
            return

        # Determine device and compute type
        if self.device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = self.compute_type if device == "cuda" else "int8"
        else:
            device = self.device
            compute_type = self.compute_type

        # Load the model
        start_time = time.time()
        self.model = WhisperModel(
            model_size_or_path=self.model_size,
            device=device,
            compute_type=compute_type,
            download_root=self.model_dir,
        )
        self.load_time = time.time() - start_time
        self.loaded_model_size = self.model_size

    def transcribe(
        self,
        audio: Union[np.ndarray, str],
        language: Optional[str] = None,
        task: str = "transcribe",
        beam_size: int = 5,
        best_of: int = 5,
        temperature: float = 0.0,
        word_timestamps: bool = False,
        sample_rate: Optional[int] = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe audio using the Whisper model.

        Args:
            audio: Audio data as numpy array or path to audio file
            language: Language code (e.g., 'en')
            task: Task type ('transcribe' or 'translate')
            beam_size: Beam size for decoding
            best_of: Number of candidates when sampling with non-zero temperature
            temperature: Sampling temperature (0.0 for deterministic)
            word_timestamps: Whether to include word-level timestamps
            **kwargs: Additional arguments for the model

        Returns:
            TranscriptionResult containing the results
        """
        if self.model is None or self.loaded_model_size != self.model_size:
            self.load_model()

        start_time = time.time()

        # Prepare arguments for transcription
        transcribe_kwargs = {
            'audio': audio,
            'language': language,
            'task': task,
            'beam_size': beam_size,
            'best_of': best_of,
            'temperature': temperature,
            'word_timestamps': word_timestamps,
            **kwargs
        }
        
        # Remove None values
        transcribe_kwargs = {k: v for k, v in transcribe_kwargs.items() if v is not None}
        
        # Transcribe the audio
        segments, info = self.model.transcribe(**transcribe_kwargs)

        # Convert generator to list and join text
        segments_list = list(segments)
        text = " ".join(segment.text for segment in segments_list)

        # Prepare segments data
        segments_data = []
        for segment in segments_list:
            segment_data = {
                'start': segment.start,
                'end': segment.end,
                'text': segment.text,
            }
            
            # Handle words if they exist
            words = getattr(segment, 'words', None)
            if words is not None:
                segment_data['words'] = [{
                    'word': word.word,
                    'start': word.start,
                    'end': word.end,
                    'probability': getattr(word, 'probability', 0.0),
                } for word in words]
            
            segments_data.append(segment_data)

        # Create result object
        result = TranscriptionResult(
            text=text,
            segments=segments_data,
            language=getattr(info, 'language', None),
            language_probability=getattr(info, 'language_probability', None),
            duration=time.time() - start_time,
            model_load_time=self.load_time,
            inference_time=time.time() - start_time,
        )

        return result

    def get_available_models(self) -> List[str]:
        """Get a list of available Whisper models.

        Returns:
            List of available model sizes
        """
        return ["tiny", "base", "small", "medium", "large"]

    def get_available_devices(self) -> List[str]:
        """Get a list of available devices.

        Returns:
            List of available devices
        """
        devices = ["cpu"]
        if torch.cuda.is_available():
            devices.append("cuda")
        return devices

    def get_available_compute_types(self) -> List[str]:
        """Get a list of available compute types.

        Returns:
            List of available compute types
        """
        return ["int8", "float16", "float32"]
