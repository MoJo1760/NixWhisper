# NixWhisper

A privacy-focused, offline speech-to-text dictation system for Linux.

## Features

- Real-time, accurate speech-to-text transcription
- 100% offline processing - no data leaves your computer
- Modal GUI with visual feedback
- Keyboard shortcut activation
- Universal typing integration (works in any text input field)
- Customizable commands and macros

## Requirements

- Linux (x86_64)
- Python 3.8+
- PortAudio (for audio input)
- FFmpeg (for audio processing)
- CUDA-capable GPU (recommended) or CPU

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nixwhisper.git
   cd nixwhisper
   ```

2. Install system dependencies:
   ```bash
   # On Ubuntu/Debian
   sudo apt update
   sudo apt install portaudio19-dev ffmpeg python3-pip
   
   # On Fedora
   sudo dnf install portaudio-devel ffmpeg python3-pip
   ```

3. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

```bash
python -m nixwhisper
```

### Keyboard Shortcuts

- `Ctrl+Alt+Space`: Toggle dictation mode
- `Ctrl+Alt+C`: Copy last recognized text to clipboard
- `Ctrl+Alt+X`: Exit application

## Configuration

Configuration can be done via the `config/config.json` file or through the settings UI.

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
