"""Configuration for speech-to-text transcribers."""

from pathlib import Path
from typing import Optional, Dict, Any, Union

from pydantic import BaseModel, Field, field_validator
from ..transcriber import get_available_backends, create_transcriber


class TranscriberConfig(BaseModel):
    """Configuration for speech-to-text transcribers."""

    # Backend settings
    backend: str = Field(
        default="faster-whisper",
        description="Backend to use for speech recognition"
    )

    # Model settings
    model_size: str = Field(
        default="base",
        description="Model size (tiny, base, small, medium, large, large-v2, large-v3)"
    )

    # Hardware settings
    device: str = Field(
        default="auto",
        description="Device to use (cpu, cuda, auto)"
    )

    compute_type: str = Field(
        default="int8",
        description="Compute type (int8, float16, float32)"
    )

    # Directory settings
    model_dir: Optional[Union[str, Path]] = Field(
        default=None,
        description="Directory to store/download models"
    )

    # Advanced settings
    advanced: Dict[str, Any] = Field(
        default_factory=dict,
        description="Advanced backend-specific settings"
    )
    
    @field_validator('backend')
    @classmethod
    def validate_backend(cls, v: str) -> str:
        """Validate that the specified backend is available."""
        available_backends = get_available_backends()

        if v not in available_backends:
            raise ValueError(
                f"Backend '{v}' is not available. "
                f"Available backends: {', '.join(available_backends.keys())}"
            )
        return v

    @field_validator('device')
    @classmethod
    def validate_device(cls, v: str) -> str:
        """Validate device setting."""
        v = v.lower()
        if v not in ('cpu', 'cuda', 'auto'):
            raise ValueError("Device must be one of: cpu, cuda, auto")
        return v

    @field_validator('compute_type')
    @classmethod
    def validate_compute_type(cls, v: str) -> str:
        """Validate compute type setting."""
        v = v.lower()
        if v not in ('int8', 'float16', 'float32'):
            raise ValueError("Compute type must be one of: int8, float16, float32")
        return v

    @field_validator('model_size')
    @classmethod
    def validate_model_size(cls, v: str) -> str:
        """Validate model size setting."""
        v = v.lower()
        valid_sizes = ('tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3')
        if v not in valid_sizes:
            raise ValueError(f"Model size must be one of: {', '.join(valid_sizes)}")
        return v
    
    def to_transcriber_kwargs(self) -> Dict[str, Any]:
        """Convert the config to keyword arguments for the transcriber."""
        return {
            'backend': self.backend,
            'model_size': self.model_size,
            'device': self.device,
            'compute_type': self.compute_type,
            'model_dir': self.model_dir,
            **self.advanced
        }

    def create_transcriber(self):
        """Create a transcriber instance with the current configuration."""
        return create_transcriber(**self.to_transcriber_kwargs())
