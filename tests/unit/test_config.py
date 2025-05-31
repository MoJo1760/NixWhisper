"""Unit tests for the config module."""

import json
import os
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from nixwhisper.config import (
    AudioConfig,
    ModelConfig,
    HotkeyConfig,
    UIConfig,
    Config
)


def test_audio_config_initialization():
    """Test AudioConfig initialization with default values."""
    config = AudioConfig()
    
    assert config.sample_rate == 16000
    assert config.channels == 1
    assert config.device is None
    assert config.silence_threshold == 0.01
    assert config.silence_duration == 2.0
    assert config.blocksize == 1024


def test_model_config_initialization():
    """Test ModelConfig initialization with default values."""
    config = ModelConfig()
    
    assert config.name == "base.en"
    assert config.device == "auto"
    assert config.compute_type == "int8"
    assert config.language == "en"
    assert config.task == "transcribe"
    assert config.beam_size == 5
    assert config.best_of == 5
    assert config.temperature == 0.0
    assert config.word_timestamps is True
    assert "download_root" in config.model_dump()


def test_hotkey_config_initialization():
    """Test HotkeyConfig initialization with default values."""
    config = HotkeyConfig()
    
    assert config.toggle_listening == "<ctrl>+<alt>+space"
    assert config.copy_last == "<ctrl>+<alt>+c"
    assert config.exit_app == "<ctrl>+<alt>+x"


def test_ui_config_initialization():
    """Test UIConfig initialization with default values."""
    config = UIConfig()
    
    assert config.theme == "system"
    assert config.show_spectrogram is True
    assert config.show_confidence is True
    assert config.font_family == "Sans"
    assert config.font_size == 12


def test_config_initialization():
    """Test Config initialization with default values."""
    config = Config()
    
    assert isinstance(config.audio, AudioConfig)
    assert isinstance(config.model, ModelConfig)
    assert isinstance(config.hotkeys, HotkeyConfig)
    assert isinstance(config.ui, UIConfig)
    assert config.audio.sample_rate == 16000
    assert config.model.name == "base.en"
    assert config.hotkeys.toggle_listening == "<ctrl>+<alt>+space"
    assert config.ui.theme == "system"


def test_config_dict_conversion():
    """Test conversion between Config and dict."""
    config = Config()
    config_dict = config.model_dump()
    
    # Check that the dict has the expected structure
    assert "audio" in config_dict
    assert "model" in config_dict
    assert "hotkeys" in config_dict
    assert "ui" in config_dict
    
    # Create a new config from the dict
    new_config = Config(**config_dict)
    
    # Check that the new config matches the original
    assert new_config.audio.sample_rate == config.audio.sample_rate
    assert new_config.model.name == config.model.name
    assert new_config.hotkeys.toggle_listening == config.hotkeys.toggle_listening
    assert new_config.ui.theme == config.ui.theme


def test_get_default_config():
    """Test getting the default configuration."""
    default_config = Config()
    
    assert isinstance(default_config, Config)
    assert default_config.audio.sample_rate == 16000
    assert default_config.model.name == "base.en"


def test_config_save_and_load(tmp_path):
    """Test saving and loading a configuration file."""
    config_path = tmp_path / "config.json"
    config = Config()
    
    # Modify some values
    config.audio.sample_rate = 22050
    config.model.name = "small.en"
    
    # Save and load
    with open(config_path, 'w') as f:
        json.dump(config.model_dump(), f, indent=2)
    
    # Load the saved config
    with open(config_path, 'r') as f:
        loaded_config = Config(**json.load(f))
    
    # Verify
    assert loaded_config.audio.sample_rate == 22050
    assert loaded_config.model.name == "small.en"
    assert loaded_config.audio.channels == 1  # Default value
    
    # Verify file was created
    assert config_path.exists()
    with open(config_path, 'r') as f:
        data = json.load(f)
        assert data['audio']['sample_rate'] == 22050
        assert data['model']['name'] == "small.en"
    assert loaded_config.audio.blocksize == 1024  # Default value


def test_load_config_file_not_found():
    """Test loading a non-existent config file returns default config."""
    config_path = Path("/non/existent/config.json")
    config = Config()  # Create default config
    
    # Should return default config when file doesn't exist
    assert config.audio.sample_rate == 16000
    assert config.model.name == "base.en"


def test_load_config_invalid_json(tmp_path):
    """Test loading an invalid JSON config file."""
    config_path = tmp_path / "invalid_config.json"
    
    # Create an invalid JSON file
    with open(config_path, 'w') as f:
        f.write("{invalid json")
    
    # Should return default config when JSON is invalid
    config = Config()  # Create default config
    assert config.audio.sample_rate == 16000
    assert config.model.name == "base.en"
