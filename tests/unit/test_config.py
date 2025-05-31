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
    Config,
    load_config,
    get_default_config_path,
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
    
    assert config.name == "base"
    assert config.device == "auto"
    assert config.compute_type == "int8"
    assert config.language is None
    assert config.task == "transcribe"
    assert config.beam_size == 5
    assert config.best_of == 5
    assert config.temperature == 0.0
    assert config.word_timestamps is False


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
    assert config.model.name == "base"
    assert config.hotkeys.toggle_listening == "<ctrl>+<alt>+space"
    assert config.ui.theme == "system"


def test_config_dict_conversion():
    """Test conversion between Config and dict."""
    config = Config()
    config_dict = config.dict()
    
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
    default_config = get_default_config()
    
    assert isinstance(default_config, Config)
    assert default_config.audio.sample_rate == 16000
    assert default_config.model.name == "base"


def test_ensure_config_dir(tmp_path):
    """Test ensuring the configuration directory exists."""
    config_dir = tmp_path / "test_config"
    
    # Directory should not exist yet
    assert not config_dir.exists()
    
    # Ensure the directory exists
    ensure_config_dir(str(config_dir))
    
    # Directory should now exist
    assert config_dir.exists()
    assert config_dir.is_dir()
    
    # Calling again should not raise an error
    ensure_config_dir(str(config_dir))


def test_get_config_path():
    """Test getting the configuration file path."""
    with patch('appdirs.user_config_dir', return_value='/test/config'):
        config_path = get_config_path()
        assert str(config_path) == '/test/config/nixwhisper/config.json'
        
        # With custom filename
        config_path = get_config_path('custom.json')
        assert str(config_path) == '/test/config/nixwhisper/custom.json'


def test_save_and_load_config(tmp_path):
    """Test saving and loading a configuration file."""
    config_path = tmp_path / "config.json"
    config = Config()
    
    # Modify some values
    config.audio.sample_rate = 22050
    config.model.name = "small"
    
    # Save and load
    config.save(config_path)
    loaded_config = load_config(config_path)
    
    # Verify
    assert loaded_config.audio.sample_rate == 22050
    assert loaded_config.model.name == "small"
    assert loaded_config.audio.channels == 1  # Default value
    
    # Verify file was created
    assert config_path.exists()
    with open(config_path, 'r') as f:
        data = json.load(f)
        assert data['audio']['sample_rate'] == 22050
        assert data['model']['name'] == "small"
    assert loaded_config.audio.blocksize == 1024  # Default value


def test_load_config_file_not_found():
    """Test loading a non-existent config file returns default config."""
    config_path = Path("/non/existent/config.json")
    config = load_config(config_path)
    
    # Should return default config when file doesn't exist
    assert config.audio.sample_rate == 16000
    assert config.model.name == "base"


def test_load_config_invalid_json(tmp_path):
    """Test loading an invalid JSON config file."""
    config_path = tmp_path / "invalid_config.json"
    
    # Create an invalid JSON file
    with open(config_path, 'w') as f:
        f.write("{invalid json")
    
    # Should return default config when JSON is invalid
    config = load_config(config_path)
    assert config.audio.sample_rate == 16000
    assert config.model.name == "base"
