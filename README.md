# NixWhisper

![NixWhisper Logo](data/icons/hicolor/scalable/apps/nixwhisper.svg)

A privacy-focused, offline speech-to-text dictation system for Linux with Qt-based GUI.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🌟 Features

### Universal Typing
NixWhisper includes a robust universal typing system that works across different Linux desktop environments:
- **Multiple Backend Support**: Automatically tries the best available method for your system
  - `pynput`: Direct input simulation (works in most cases)
  - `xdotool`: X11-compatible typing (great for X11 environments)
  - `GTK`: Native typing for Wayland desktops
  - `Clipboard`: Fallback method that works everywhere
- **Automatic Fallback**: If one method fails, it will automatically try the next best option
- **Seamless Integration**: Works in any application's text input field

- 🎙️ **Real-time, accurate speech-to-text transcription** using OpenWhisper models
- 🔒 **100% offline processing** - no data leaves your computer
- 🖥️ **Modern Qt-based GUI** with visual feedback
- ⌨️ **Keyboard shortcut activation** for quick dictation
- 🌐 **Universal typing integration** works in any text input field with multiple fallback methods (pynput, xdotool, GTK, clipboard)
- ⚙️ **Customizable** commands and macros
- 🐍 **Python-based** for easy extension and modification
- 🚀 **Optimized for performance** with support for GPU acceleration

## 📋 Requirements

- **OS**: Linux (x86_64)
- **Python**: 3.8 or higher
- **Audio**: Microphone with working drivers
- **System Dependencies**:
  - PortAudio (for audio input)
  - FFmpeg (for audio processing)
  - Qt 6 (for the modern GUI)
- **Hardware**:
  - CUDA-capable GPU (recommended for better performance)
  - At least 2GB RAM (4GB+ recommended)
  - At least 1GB free disk space for models

## 📋 Dependencies

### System Dependencies
- **For X11 users**: `xdotool` (for X11 typing support)
  ```bash
  # Ubuntu/Debian
  sudo apt install xdotool
  
  # Fedora
  sudo dnf install xdotool
  
  # Arch Linux
  sudo pacman -S xdotool
  ```

- **For Wayland users**: GTK and related libraries should already be installed

## 🚀 Installation

### Using pip (Recommended)

```bash
# Install from PyPI (when available)
pip install nixwhisper

# Or install directly from GitHub
pip install git+https://github.com/yourusername/nixwhisper.git

# Run the application
nixwhisper
```

### From Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/nixwhisper.git
   cd nixwhisper
   ```

2. **Install system dependencies**:
   ```bash
   # On Ubuntu/Debian
   sudo apt update
   sudo apt install -y \
       portaudio19-dev \
       ffmpeg \
       python3-pip \
       python3-venv \
       gcc \
       python3-dev \
       python3-pyqt6 \
       python3-pyqt6.qtmultimedia \
       libportaudio2 \
       pkg-config \
       xclip  # For clipboard integration
   
   # On Fedora
   sudo dnf install -y \
       portaudio-devel \
       ffmpeg \
       python3-pip \
       python3-virtualenv \
       gcc \
       python3-devel \
       python3-qt6 \
       python3-qt6-qtmultimedia \
       portaudio \
       pkg-config \
       xclip  # For clipboard integration
   ```

3. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Install in development mode**:
   ```bash
   pip install -e .
   ```

## 🎯 Usage

### Command Line Interface (CLI)

```bash
# Start NixWhisper in GUI mode (default)
nixwhisper

# Or use the command-line interface
nixwhisper --cli

# Specify a different model (tiny, base, small, medium, large)
nixwhisper --model small

# Show help
nixwhisper --help
```

### GUI Mode

The GUI provides a user-friendly interface with the following features:

- **Record Button**: Click to start/stop recording
- **Text Display**: Shows transcribed text
- **Audio Level Meter**: Visual feedback for audio input
- **Copy to Clipboard**: Copy the transcribed text
- **Clear**: Clear the text display
- **Settings**: Configure application settings

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Alt+Space` | Toggle dictation mode |
| `Ctrl+Alt+C` | Copy last recognized text to clipboard |
| `Ctrl+Q` | Exit application |
| `Escape` | Stop current recording |

## ⚙️ Configuration

NixWhisper stores its configuration in `~/.config/nixwhisper/config.json`. You can edit this file directly or use the settings UI.

### Example Configuration

```json
{
  "audio": {
    "sample_rate": 16000,
    "channels": 1,
    "device": null,
    "silence_threshold": 0.01,
    "silence_duration": 2.0,
    "blocksize": 1024
  },
  "model": {
    "name": "base",
    "device": "auto",
    "compute_type": "int8",
    "language": "en",
    "task": "transcribe",
    "beam_size": 5,
    "best_of": 5,
    "temperature": 0.0,
    "word_timestamps": false
  },
  "hotkeys": {
    "toggle_listening": "<ctrl>+<alt>+space",
    "copy_last": "<ctrl>+<alt>+c",
    "exit_app": "<ctrl>+<alt>+x"
  },
  "ui": {
    "theme": "system",
    "show_spectrogram": true,
    "show_confidence": true,
    "font_family": "Sans",
    "font_size": 12
  }
}
```

## 🛠️ Development

### Project Structure

```
nixwhisper/
├── data/                    # Application data files
│   ├── config.json          # Default configuration
│   ├── icons/               # Application icons
│   └── nixwhisper.desktop   # Desktop entry
├── src/
│   └── nixwhisper/        # Python package
│       ├── __init__.py      # Package initialization
│       ├── __main__.py      # Main entry point
│       ├── audio.py         # Audio capture and processing
│       ├── cli.py           # Command-line interface
│       ├── config.py        # Configuration management
│       ├── qt_gui.py        # Qt-based GUI
│       ├── input.py         # System input simulation
│       └── whisper_model.py # Whisper model integration
├── tests/                   # Unit tests
├── .gitignore
├── LICENSE
├── pyproject.toml
├── README.md
└── setup.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=nixwhisper --cov-report=term-missing
```

### Building Packages

```bash
# Build source distribution and wheel
python -m build

# Install build dependencies if needed
pip install build
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to contribute to this project.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - The speech recognition model
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Faster Whisper implementation
- [GTK](https://www.gtk.org/) - The GIMP Toolkit for the GUI
- [PyGObject](https://pygobject.readthedocs.io/) - Python bindings for GObject

---

Made with ❤️ and Python
