"""Base transcriber interface for speech-to-text backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union, Dict, Any


@dataclass
class TranscriptionSegment:
    """A single segment of a transcription."""
    start: float
    end: float
    text: str
    words: Optional[List[Dict[str, Any]]] = None
    speaker: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class TranscriptionResult:
    """Container for transcription results."""
    text: str
    language: str
    segments: List[TranscriptionSegment]
    language_probability: Optional[float] = None
    duration: float = 0.0
    model_load_time: float = 0.0
    inference_time: float = 0.0


class BaseTranscriber(ABC):
    """Base class for all speech-to-text transcribers."""
    
    @abstractmethod
    def load_model(self):
        """Load the model and any required resources."""
        pass
    
    @abstractmethod
    def transcribe(
        self,
        audio: Union[str, Path, bytes],
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe audio to text.
        
        Args:
            audio: Path to audio file or audio data as bytes
            language: Language code (e.g., 'en' for English)
            **kwargs: Additional arguments for the transcriber
            
        Returns:
            TranscriptionResult containing the transcribed text and metadata
        """
        pass
    
    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if the model is loaded.
        
        Returns:
            bool: True if the model is loaded, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """Get a list of supported language codes.
        
        Returns:
            List of supported language codes (e.g., ['en', 'es', 'fr'])
        """
        pass
