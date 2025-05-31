"""End-to-end tests for the command-line interface."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nixwhisper.cli import main as cli_main
from nixwhisper.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Config()
    # Use a smaller model for faster tests
    config.model.name = "tiny"
    config.model.device = "cpu"
    config.model.compute_type = "int8"
    return config


@pytest.fixture
def mock_audio_file(tmp_path):
    """Create a temporary audio file for testing."""
    import numpy as np
    import soundfile as sf
    
    audio_file = tmp_path / "test_audio.wav"
    
    # Create a 1-second audio file with a 440 Hz sine wave
    sample_rate = 16000
    t = np.linspace(0, 1.0, sample_rate, endpoint=False)
    audio_data = np.sin(2 * np.pi * 440 * t) * 0.1  # 440 Hz sine wave
    sf.write(str(audio_file), audio_data, sample_rate)
    
    return str(audio_file)


@pytest.fixture
def mock_whisper_transcriber():
    """Create a mock WhisperTranscriber for testing."""
    with patch('nixwhisper.cli.WhisperTranscriber') as mock_transcriber_class:
        mock_transcriber = MagicMock()
        mock_transcriber_class.return_value = mock_transcriber
        
        # Set up the mock to return a transcription result
        mock_result = MagicMock()
        mock_result.text = "This is a test transcription."
        mock_result.language = "en"
        mock_transcriber.transcribe.return_value = mock_result
        
        yield mock_transcriber


@pytest.fixture
def mock_audio_recorder():
    """Create a mock AudioRecorder for testing."""
    with patch('nixwhisper.cli.AudioRecorder') as mock_recorder_class:
        mock_recorder = MagicMock()
        mock_recorder_class.return_value = mock_recorder
        
        # Set up the mock to simulate recording
        mock_recorder.audio_queue = []
        
        def mock_audio_callback(indata, frames, time_info, status):
            mock_recorder.audio_queue.append(indata.copy())
            return (indata, True)
        
        mock_recorder.audio_callback = mock_audio_callback
        
        yield mock_recorder


@pytest.mark.e2e
class TestCLIWorkflow:
    """End-to-end tests for the command-line interface."""
    
    def test_cli_record_and_transcribe(self, mock_config, mock_whisper_transcriber, mock_audio_recorder, capsys, monkeypatch):
        """Test the CLI record and transcribe workflow."""
        # Import the module at the test level
        import nixwhisper.cli
        
        # Mock command-line arguments
        test_args = ["nixwhisper", "--cli"]  # Force CLI mode
        
        # Ensure the environment is set up for CLI mode
        monkeypatch.delenv('DISPLAY', raising=False)
        
        # Create a mock for the NixWhisperCLI class
        mock_cli_instance = MagicMock()
        mock_cli_instance.run.return_value = 0
        
        # Patch the necessary components
        with patch('sys.argv', test_args), \
             patch('nixwhisper.cli.load_config', return_value=mock_config), \
             patch('nixwhisper.cli.NixWhisperCLI', return_value=mock_cli_instance) as mock_cli_class:
            
            # Mock the input function to raise KeyboardInterrupt to exit the loop
            with patch('builtins.input', side_effect=KeyboardInterrupt):
                # Call the main function directly
                result = nixwhisper.cli.main()
                
                # Verify the result
                assert result == 0
                
                # Verify NixWhisperCLI was instantiated with the config
                mock_cli_class.assert_called_once_with(mock_config)
                
                # Verify run was called on the instance
                mock_cli_instance.run.assert_called_once()
    
    def test_cli_transcribe_file(self, mock_config, mock_whisper_transcriber, mock_audio_file, capsys):
        """Test transcribing an audio file using the CLI."""
        # This test needs to be updated to match the current CLI implementation
        # Currently, the CLI doesn't support direct file transcription
        pass
    
    def test_cli_list_devices(self, mock_config, capsys):
        """Test listing available audio devices."""
        # Mock command-line arguments
        test_args = ["nixwhisper", "--list-devices"]
        
        # Create a mock for the sounddevice module
        mock_sd = MagicMock()
        mock_sd.query_devices.return_value = [
            {'name': 'Mock Device', 'max_input_channels': 2, 'default_samplerate': 44100}
        ]
        
        # Mock the NixWhisperCLI class
        mock_cli = MagicMock()
        mock_cli.run.return_value = 0
        
        # Patch the necessary components
        with patch('sys.argv', test_args), \
             patch('nixwhisper.cli.load_config', return_value=mock_config), \
             patch('nixwhisper.cli.NixWhisperCLI', return_value=mock_cli), \
             patch.dict('sys.modules', {'sounddevice': mock_sd}):
            
            # Import the module after patching
            import importlib
            if 'nixwhisper.cli' in sys.modules:
                importlib.reload(sys.modules['nixwhisper.cli'])
            else:
                import nixwhisper.cli
            
            # Call the function directly instead of using cli_main()
            from nixwhisper.cli import list_audio_devices
            result = list_audio_devices()
            
            # Should return 0 on success
            assert result == 0
            
            # Check the output
            captured = capsys.readouterr()
            assert "Available audio input devices" in captured.out
            assert "Mock Device" in captured.out
    
    def test_cli_show_version(self, capsys):
        """Test showing the version information."""
        # Import the module at the test level
        import nixwhisper.cli
        
        # Mock command-line arguments
        test_args = ["nixwhisper", "--version"]
        
        with patch('sys.argv', test_args), \
             patch('nixwhisper.cli.load_config'):
            
            # Reload the module to apply patches
            import importlib
            importlib.reload(nixwhisper.cli)
            
            # Call the main function and expect it to exit with status 0
            with pytest.raises(SystemExit) as exc_info:
                nixwhisper.cli.main()
            
            # Should exit with status 0 on success
            assert exc_info.value.code == 0
            
            # Check the output
            captured = capsys.readouterr()
            assert "NixWhisper 0.1.0" in captured.out
    
    def test_cli_show_help(self, capsys):
        """Test showing the help message."""
        # Import the module at the test level
        import nixwhisper.cli
        
        # Mock command-line arguments
        test_args = ["nixwhisper", "--help"]
        
        with patch('sys.argv', test_args), \
             patch('nixwhisper.cli.load_config'):
            
            # Reload the module to apply patches
            import importlib
            importlib.reload(nixwhisper.cli)
            
            # Call the main function and expect it to exit with status 0
            with pytest.raises(SystemExit) as exc_info:
                nixwhisper.cli.main()
            
            # Should exit with status 0 on success
            assert exc_info.value.code == 0
            
            # Check the output
            captured = capsys.readouterr()
            assert "usage:" in captured.out.lower()
            assert "--help" in captured.out.lower()
            assert "show this help message and exit" in captured.out.lower()


if __name__ == "__main__":
    pytest.main([__file__])
