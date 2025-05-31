"""Faster-Whisper backend for speech-to-text transcription."""

import time
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

import numpy as np
import torch
from faster_whisper import WhisperModel

from .base import BaseTranscriber, TranscriptionResult, TranscriptionSegment


class FasterWhisperTranscriber(BaseTranscriber):
    """Faster-Whisper implementation of the BaseTranscriber interface."""
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
        model_dir: Optional[Union[str, Path]] = None,
        **kwargs
    ):
        """Initialize the Faster-Whisper transcriber.
        
        Args:
            model_size: Model size (tiny, base, small, medium, large, large-v2, large-v3)
            device: Device to use (cpu, cuda, auto)
            compute_type: Compute type (int8, float16, float32)
            model_dir: Directory to store/download models
            **kwargs: Additional arguments for WhisperModel
        """
        self.model_size = model_size
        self.device = device.lower()
        self.compute_type = compute_type
        self.model_dir = str(model_dir) if model_dir else None
        self.model = None
        self._supported_languages = [
            'en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja', 'pt', 'tr',
            'pl', 'ca', 'nl', 'ar', 'sv', 'it', 'id', 'hi', 'fi', 'vi',
            'he', 'uk', 'el', 'ms', 'cs', 'ro', 'da', 'hu', 'ta', 'no',
            'th', 'ur', 'hr', 'bg', 'lt', 'la', 'mi', 'ml', 'cy', 'sk',
            'te', 'fa', 'lv', 'bn', 'sr', 'az', 'sl', 'kn', 'et', 'mk',
            'br', 'eu', 'is', 'hy', 'ne', 'mn', 'bs', 'kk', 'sq', 'sw',
            'gl', 'mr', 'pa', 'si', 'km', 'sn', 'yo', 'so', 'af', 'oc',
            'ka', 'be', 'tg', 'sd', 'gu', 'am', 'yi', 'lo', 'uz', 'fo',
            'ht', 'ps', 'tk', 'nn', 'mt', 'sa', 'lb', 'my', 'bo', 'tl',
            'mg', 'as', 'tt', 'haw', 'ln', 'ha', 'ba', 'jw', 'su'
        ]
        self.kwargs = kwargs
        self._load_time = 0.0
    
    def load_model(self):
        """Load the Whisper model."""
        if self.is_loaded:
            return
            
        start_time = time.time()
        
        # Handle device selection
        if self.device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = self.compute_type if device == "cuda" else "int8"
        else:
            device = self.device
            compute_type = self.compute_type
        
        # Initialize the model
        self.model = WhisperModel(
            self.model_size,
            device=device,
            compute_type=compute_type,
            download_root=self.model_dir,
            **self.kwargs
        )
        
        self._load_time = time.time() - start_time
    
    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self.model is not None
    
    @property
    def supported_languages(self) -> List[str]:
        """Get a list of supported language codes."""
        return self._supported_languages
    
    def transcribe(
        self,
        audio: Union[str, Path, bytes, np.ndarray],
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio to text using Faster-Whisper.
        
        Args:
            audio: Path to audio file, audio data as bytes, or numpy array
            language: Language code (e.g., 'en' for English)
            **kwargs: Additional arguments for the transcriber
            
        Returns:
            TranscriptionResult containing the transcribed text and metadata
        """
        if not self.is_loaded:
            self.load_model()
        
        # Handle different input types
        if isinstance(audio, Path):
            audio = str(audio)
        elif isinstance(audio, bytes):
            # Convert bytes to numpy array of float32
            audio = np.frombuffer(audio, dtype=np.float32)
            # Reshape to 1D array if it's not already
            if len(audio.shape) > 1:
                audio = audio.reshape(-1)
        
        # Set default options
        options = {
            "language": language,
            "task": "transcribe",
            "beam_size": 5,
            "best_of": 5,
            "vad_filter": True,
            "word_timestamps": True,
        }
        options.update(kwargs)
        
        # Run transcription
        start_time = time.time()
        segments, info = self.model.transcribe(audio, **options)
        
        # Convert segments to our format
        transcription_segments = []
        full_text = []
        
        for segment in segments:
            # Create word-level timestamps if available
            words = None
            if hasattr(segment, 'words') and segment.words:
                words = [
                    {
                        'word': word.word,
                        'start': word.start,
                        'end': word.end,
                        'confidence': word.probability
                    }
                    for word in segment.words
                ]
            
            # Create segment
            seg = TranscriptionSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
                words=words,
                speaker=None,  # Speaker diarization not supported by default
                confidence=segment.avg_logprob if hasattr(segment, 'avg_logprob') else None
            )
            
            transcription_segments.append(seg)
            full_text.append(segment.text.strip())
        
        # Calculate total duration
        duration = time.time() - start_time
        
        return TranscriptionResult(
            text=" ".join(full_text).strip(),
            language=info.language if hasattr(info, 'language') else language or "en",
            segments=transcription_segments,
            language_probability=getattr(info, 'language_probability', None),
            duration=duration,
            model_load_time=self._load_time,
            inference_time=duration
        )
