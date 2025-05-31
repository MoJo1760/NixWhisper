"""Transcriber module for speech-to-text backends."""

from pathlib import Path
from typing import Optional, Dict, Any, Type, Union

from .base import BaseTranscriber
from .faster_whisper_backend import FasterWhisperTranscriber

# Available backends with their implementations
BACKENDS = {
    'faster-whisper': FasterWhisperTranscriber,
    # Add other backends here as they are implemented
}


def create_transcriber(
    backend: str = 'faster-whisper',
    model_size: str = 'base',
    device: str = 'auto',
    compute_type: str = 'int8',
    model_dir: Optional[Union[str, Path]] = None,
    **kwargs
) -> BaseTranscriber:
    """Create a transcriber instance with the specified backend.
    
    Args:
        backend: Backend to use (e.g., 'faster-whisper')
        model_size: Model size (e.g., 'tiny', 'base', 'small', 'medium', 'large')
        device: Device to use ('cpu', 'cuda', 'auto')
        compute_type: Compute type ('int8', 'float16', 'float32')
        model_dir: Directory to store/download models
        **kwargs: Additional arguments for the transcriber
        
    Returns:
        An instance of the specified transcriber backend
        
    Raises:
        ValueError: If the specified backend is not available
    """
    if backend not in BACKENDS:
        available_backends = ", ".join(BACKENDS.keys())
        raise ValueError(
            f"Backend '{backend}' is not available. "
            f"Available backends: {available_backends}"
        )
    
    transcriber_class = BACKENDS[backend]
    return transcriber_class(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        model_dir=model_dir,
        **kwargs
    )


def get_available_backends() -> Dict[str, Type[BaseTranscriber]]:
    """Get a dictionary of available transcriber backends.
    
    Returns:
        Dictionary mapping backend names to their implementation classes
    """
    return BACKENDS.copy()
