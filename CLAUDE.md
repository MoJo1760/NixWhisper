# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Testing
```bash
# Run all tests
pytest

# Run with coverage report  
pytest --cov=nixwhisper --cov-report=term-missing

# Run specific test file
pytest tests/test_qt_gui.py

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run end-to-end tests
pytest tests/e2e/
```

### Code Quality
```bash
# Format code with Black
black src/ tests/

# Check imports with isort
isort src/ tests/

# Run flake8 linting
flake8 src/ tests/

# Type checking with mypy
mypy src/

# Run all quality checks (if available)
python -m tox
```

### Development Installation
```bash
# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Install with GUI dependencies
pip install -e ".[gui]"
```

### Running the Application
```bash
# Run GUI mode (default)
nixwhisper

# Force CLI mode
nixwhisper --cli

# Enable debug logging
nixwhisper --debug

# Run specific model
nixwhisper --model small
```

## Architecture Overview

### Core Components

- **Entry Points**: `__main__.py` handles argument parsing and determines whether to launch GUI or CLI mode
- **GUI Layer**: `qt_gui.py` provides Qt6-based interface with overlay window for cursor-positioned transcription
- **CLI Interface**: `cli.py` provides command-line interface for headless operation
- **Audio Pipeline**: `audio.py` handles microphone input and audio processing
- **Transcription**: `transcriber/` directory contains Whisper model integration with faster-whisper backend
- **Universal Typing**: `universal_typing.py` provides cross-platform text input simulation with multiple fallback methods
- **Configuration**: `config.py` manages application settings and user preferences
- **Model Management**: `model_manager.py` handles Whisper model downloading and caching

### Key Features

- **Cursor-Positioned Dialog**: X11 cursor tracking (`x11_cursor.py`) enables showing transcription overlay at cursor position
- **Multi-Backend Typing**: Universal typing system supports pynput, xdotool, GTK, and clipboard fallback methods
- **Offline Processing**: All speech-to-text processing happens locally using Whisper models
- **Qt6 Modern GUI**: Full-featured desktop application with system tray integration
- **Global Hotkeys**: System-wide keyboard shortcuts for activation

### Module Structure

```
src/nixwhisper/
├── __main__.py          # Entry point and argument parsing
├── main.py              # Legacy entry point (placeholder)
├── qt_gui.py            # Qt6 GUI implementation with overlay
├── cli.py               # Command-line interface
├── audio.py             # Audio capture and processing
├── config.py            # Configuration management
├── universal_typing.py  # Cross-platform text input
├── x11_cursor.py        # X11 cursor position tracking
├── model_manager.py     # Whisper model management
├── transcriber/         # Transcription backends
│   ├── base.py          # Base transcriber interface
│   └── faster_whisper_backend.py
├── utils/               # Utility modules
└── scripts/             # Utility scripts
```

### Testing Structure

- **Unit Tests**: `tests/unit/` - Test individual components in isolation
- **Integration Tests**: `tests/integration/` - Test component interactions
- **E2E Tests**: `tests/e2e/` - Test complete workflows
- **Qt Tests**: Use `pytest-qt` for GUI testing

## Development Patterns

### Configuration Management
- Settings stored in `~/.config/nixwhisper/config.json`
- Config schema defined with Pydantic models
- Environment-specific overrides supported

### Error Handling
- Graceful degradation for missing dependencies (Qt, X11 tools)
- Fallback typing methods when preferred method fails
- Comprehensive logging with configurable levels

### Qt GUI Patterns
- Signal/slot pattern for async operations
- Custom overlay windows with transparency
- System tray integration for background operation
- Global hotkey handling with X11 integration

### Audio Processing
- Continuous audio capture with silence detection
- Real-time audio level monitoring for GUI feedback
- Configurable audio parameters (sample rate, channels, etc.)

## Important Notes

### Dependencies
- PyQt6 required for GUI mode, graceful fallback to CLI if unavailable
- X11 dependencies (`python-xlib`, `xdotool`) for Linux cursor tracking and typing
- `faster-whisper` for optimized Whisper model inference
- Multiple typing backends with automatic fallback chain

### Platform Support
- Primary target: Linux (X11 and Wayland with fallbacks)
- Universal typing handles different desktop environments
- X11-specific features (cursor tracking) with Wayland compatibility planned

### Code Style
- Black formatter with 88-character line length
- isort for import organization
- Type hints required for all public APIs
- Comprehensive docstrings for classes and functions

### Cursor Rules Integration
The project uses Cursor rules for AI-assisted development. Key rules include:
- Task-driven development workflow with MCP server integration
- Comprehensive testing requirements
- Code quality standards and formatting
- Self-improvement through rule updates based on implementation learnings