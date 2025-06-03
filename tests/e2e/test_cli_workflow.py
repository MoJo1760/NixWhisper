"""End-to-end tests for the command-line interface."""
from unittest.mock import MagicMock, patch

import pytest

from nixwhisper.cli import main as cli_main
from nixwhisper.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Config()
    config.model_size = "tiny"
    config.device = "cpu"
    config.compute_type = "int8"
    config.model_dir = "/tmp/models"
    return config


@pytest.fixture
def mock_audio_file(tmp_path):
    """Create a mock audio file."""
    return str(tmp_path / "test.wav")


@pytest.fixture
def mock_whisper_transcriber():
    """Create a mock Whisper transcriber."""
    # Create a mock transcriber
    mock_transcriber = MagicMock()

    # Set up the mock transcribe method
    mock_transcriber.transcribe.return_value = MagicMock(
        text="Test transcription",
        segments=[],
        language="en",
        language_probability=0.99
    )

    return mock_transcriber


@pytest.fixture
def mock_mic():
    """Mock microphone instance."""
    with patch('nixwhisper.microphone.MicrophoneInput') as mock_mic_class:
        mock_mic_instance = MagicMock()
        mock_mic_class.return_value = mock_mic_instance
        yield mock_mic_instance


@pytest.fixture
def mock_audio_recorder():
    """Create a mock audio recorder."""
    # Create a mock recorder
    mock_recorder = MagicMock()

    # Set up the mock recorder
    def mock_audio_callback(frames, *_):
        """Mock audio callback.

        Args:
            frames: Audio frames
            *_: Ignored arguments (time_info, status)
        """
        return frames, 0  # 0 = continue

    mock_recorder.audio_callback = mock_audio_callback

    # Return the mock recorder
    return mock_recorder


@pytest.mark.e2e
class TestCLIWorkflow:
    """End-to-end tests for the command-line interface."""
    def test_cli_record_and_transcribe(self):
        """Test the CLI record and transcribe workflow."""
        config = Config()
        config.model_size = "tiny"
        config.device = "cpu"
        config.compute_type = "int8"

        with patch('sys.argv', ["nixwhisper", "--cli"]), \
             patch('nixwhisper.cli.CLI') as mock_cli_class:
            mock_cli_instance = MagicMock()
            mock_cli_instance.run.return_value = 0
            mock_cli_class.return_value = mock_cli_instance

            assert cli_main() == 0
            mock_cli_class.assert_called_once_with(config)
            mock_cli_instance.run.assert_called_once()

    def test_list_devices(self):
        """Test listing available audio devices."""
        with patch('sys.argv', ["nixwhisper", "--list-devices"]), \
             patch('nixwhisper.cli.list_audio_devices',
                   return_value=["device1", "device2"]) as mock_list_devices:
            assert cli_main() == 0
            mock_list_devices.assert_called_once()

    def test_cli_transcribe_file(self):
        """Test transcribing an audio file using the CLI."""
        config = Config()
        config.model_size = "tiny"
        config.device = "cpu"
        config.compute_type = "int8"

        with patch('sys.argv', ["nixwhisper", "--transcribe", "test.wav"]), \
             patch('nixwhisper.cli.load_config', return_value=config), \
             patch('nixwhisper.cli.transcribe_file',
                   return_value="Transcription result"), \
             patch('builtins.print') as mock_print:
            assert cli_main() == 0
            mock_print.assert_called_once_with("Transcription result")

    def test_cli_list_devices(self):
        """Test listing available audio devices."""
        with patch('sys.argv', ["nixwhisper", "--list-devices"]), \
             patch('nixwhisper.cli.list_audio_devices', return_value=["device1", "device2"]):
            assert cli_main() == 0

    def test_cli_show_version(self, capsys):
        """Test showing the version information."""
        version_info = "NixWhisper v1.0.0"
        with patch('sys.argv', ["nixwhisper", "--version"]), \
             patch('nixwhisper.cli.VERSION', version_info):
            assert cli_main() == 0
            assert version_info in capsys.readouterr().out

    def test_cli_show_help(self, capsys):
        """Test showing the help message."""
        with patch('sys.argv', ["nixwhisper", "--help"]):
            assert cli_main() == 0
            assert "Usage: nixwhisper" in capsys.readouterr().out

    def test_cli_invalid_command(self, capsys):
        """Test handling of invalid commands."""
        with patch('sys.argv', ["nixwhisper", "--invalid"]):
            with pytest.raises(SystemExit) as exc_info:
                cli_main()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Unknown command" in captured.err.lower()
            assert "--help" in captured.out.lower()
            assert "show this help message and exit" in captured.out.lower()


if __name__ == "__main__":
    pytest.main([__file__])
