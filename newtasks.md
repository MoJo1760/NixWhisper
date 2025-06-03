# Prioritized Task List: Offline Real-Time Dictation System

## 1. Project Initialization & Architecture

- Set up GitHub repository with open-source license, README, and contributing guidelines.
- Establish modular Python 3.10+ project structure (core, GUI abstraction, input integration, model management, customization, utilities).
- Prepare build scripts for standalone binaries and PyPI distribution.
- Define interfaces for all major modules and document them for contributors.

---

## 2. Core Speech-to-Text Engine

- Integrate OpenWhisper models using a Python-compatible library.
- Implement local model loader, supporting multiple model sizes and user selection.
- Provide model download/installation script and robust error handling for device/model issues.
- Build audio input pipeline using PyAudio or sounddevice, with device selection.
- Stream audio to the model for real-time transcription with low latency.
- Output transcription events to the rest of the application.

---

## 3. Universal Typing Integration

- Implement system-level input injection for X11 (using xdotool, python-xlib, or similar).
- Ensure dictated text appears in any focused application.
- Handle input context, focus changes, and edge cases.
- Prototype Wayland support as a stretch goal.

---

## 4. GUI Abstraction Layer (Default GTK)

- Define a GUI abstraction interface to support both GTK and Qt backends, but default to GTK if available.
- Implement GTK GUI module:
  - Modal window with spectrograph/visual indicator
  - Activation/deactivation feedback
  - Settings dialog (hotkey, model selection, formatting commands, silence detection)
- Implement Qt GUI module for future extensibility, ensuring it can be swapped in if GTK is unavailable.
- Ensure GUI modules are swappable via the abstraction layer, but auto-select GTK by default.

---

## 5. Global Hotkey Activation

- Implement global hotkey listener for X11 (using python-xlib or pynput).
- Ensure hotkey works when UI is in the background.
- Allow user configuration of activation hotkey through the settings dialog in the GUI.
- Connect hotkey events to GUI and dictation engine.
- Prototype and document Wayland hotkey support as a stretch goal.

---

## 6. Automatic Silence Detection

- Develop a silence detection algorithm that monitors microphone input and stops dictation after a configurable period of silence.
- Integrate silence detection with the dictation engine to automatically stop recording.
- Expose silence detection settings (duration, sensitivity) in the GUI settings dialog.
- Ensure settings are saved and loaded from the JSON config file.

---

## 7. Model Management

- Build model manager module to list, add, remove, and select models.
- Support user selection of larger/more accurate models.
- Store model metadata and user preferences in local JSON config files.
- Add GUI for model management in both GTK and Qt modules.

---

## 8. Customization Features

- Implement formatting command recognition (e.g., “new paragraph”, “bullet point”).
- Develop GUI for managing formatting commands.
- Store all user settings and formatting customizations in JSON config files.

---

## 9. Stretch/Bonus Features

- Define and document plugin/API interface for future integrations (VS Code, office suites, etc.).
- Add support for pre-recorded audio transcription.
- Implement clipboard integration for dictated text.

---

## 10. Testing & Documentation

- Write unit and integration tests for all modules.
- Test on major Linux desktop environments (GNOME, KDE, XFCE) under X11.
- Document installation, configuration, usage, and contribution process for GitHub and PyPI.
- Prepare developer and user guides, emphasizing JSON config usage and Python 3.10+ requirement.
