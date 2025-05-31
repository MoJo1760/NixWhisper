"""Configuration management for NixWhisper."""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class AudioConfig(BaseModel):
    """Audio capture configuration."""
    sample_rate: int = 16000
    channels: int = 1
    device: Optional[int] = None
    silence_threshold: float = 0.01
    silence_duration: float = 2.0
    blocksize: int = 1024

    @field_validator('sample_rate')
    @classmethod
    def validate_sample_rate(cls, v: int) -> int:
        if v < 8000 or v > 48000:
            raise ValueError("Sample rate must be between 8000 and 48000")
        return v


class ModelConfig(BaseModel):
    """Whisper model configuration."""
    name: str = "base.en"
    device: str = "auto"
    compute_type: str = "int8"
    language: Optional[str] = "en"
    task: str = "transcribe"
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0
    word_timestamps: bool = True
    download_root: str = Field(
        default_factory=lambda: str(Path.home() / ".cache" / "nixwhisper" / "models"),
        description="Directory to store downloaded models"
    )

    @field_validator('name')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        valid_models = [
            "tiny.en", "base.en", "small.en", "medium.en",
            "tiny", "base", "small", "medium", "large"
        ]
        if v not in valid_models:
            raise ValueError(f"Model must be one of {valid_models}")
        return v
        
    @field_validator('compute_type')
    @classmethod
    def validate_compute_type(cls, v: str) -> str:
        valid_types = ["int8", "int8_float16", "int16", "float16", "float32"]
        if v not in valid_types:
            raise ValueError(f"Compute type must be one of {valid_types}")
        return v


class HotkeyConfig(BaseModel):
    """Keyboard shortcut configuration."""
    toggle_listening: str = "<ctrl>+<alt>+space"
    copy_last: str = "<ctrl>+<alt>+c"
    exit_app: str = "<ctrl>+<alt>+x"


class UIConfig(BaseModel):
    """User interface configuration."""
    theme: str = "system"
    show_spectrogram: bool = True
    show_confidence: bool = True
    font_family: str = "Sans"
    font_size: int = 12
    window_width: int = 800
    window_height: int = 600
    window_x: Optional[int] = None
    window_y: Optional[int] = None


class Config(BaseModel):
    """Main configuration class."""
    audio: AudioConfig = Field(default_factory=AudioConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    hotkeys: HotkeyConfig = Field(default_factory=HotkeyConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'Config':
        """Load configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Loaded Config instance
        """
        config_path = Path(config_path)
        if not config_path.exists():
            logging.warning(f"Config file {config_path} not found, using defaults")
            return cls()
            
        with open(config_path, 'r') as f:
            config_data = json.load(f)
            
        return cls.parse_obj(config_data)
    
    def save(self, config_path: Union[str, Path]):
        """Save configuration to a JSON file.
        
        Args:
            config_path: Path to save the configuration file
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(self.dict(), f, indent=2)


def get_default_config_path() -> Path:
    """Get the default configuration file path.
    
    Returns:
        Path to the default configuration file
    """
    config_dir = Path.home() / ".config" / "nixwhisper"
    return config_dir / "config.json"


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """Load configuration from file or use defaults.
    
    Args:
        config_path: Optional path to config file. If None, uses default location.
        
    Returns:
        Loaded Config instance
    """
    if config_path is None:
        config_path = get_default_config_path()
    
    try:
        return Config.from_file(config_path)
    except Exception as e:
        logging.error(f"Error loading config from {config_path}: {e}")
        logging.info("Using default configuration")
        return Config()
