# Step-by-Step TODO List: Offline Real-Time Dictation System for Linux

---

## 1. Project Setup 

- [x] Create project repository and initialize version control
- [x] Set up project structure (src, docs, tests, etc.)
- [x] Choose primary programming language and GUI framework (Python with PyGObject/GTK)
- [x] Document build and contribution guidelines

---

## 2. Core Speech-to-Text Engine 

- [x] Evaluate and select local speech-to-text backend (e.g., Whisper.cpp, faster-whisper)[2][8]
- [x] Integrate backend for real-time microphone input[2][8]
- [x] Implement basic audio capture and streaming to the model
- [x] Parse and output recognized text in real time
- [x] Add proper error handling for audio device access
- [x] Implement audio level monitoring for VU meter
- [x] Add silence detection for better transcription accuracy (automatically stops recording after a period of silence)
- [x] Update Pydantic validators to V2 for better type safety and future compatibility
- [x] Make GUI dependencies (PyGObject, pycairo) optional
- [x] Implement graceful fallback to CLI when GUI dependencies are missing
- [x] Add command-line arguments for controlling UI mode and debug output
- [x] Create a robust CLI interface for non-GUI usage
- [x] Add proper logging configuration for both CLI and GUI modes

---

## 3. Model Management 

- [x] Bundle the default OpenWhisper English model with the application for a seamless first-run experience
  - Added automatic model download during installation
  - Implemented fallback to bundled model if available
  - Added command-line tool for manual model management
- [x] Implement model swapping/importing functionality
  - [x] Add model selection via configuration
  - [x] Allow loading models from custom paths
  - [x] Basic model validation
- [ ] Improve model management
  - [ ] Add UI for model selection (when GUI is available)
  - [ ] Add model validation and compatibility checks
  - [ ] Implement model caching and versioning

---

## 4. Qt GUI Development 

- [x] Design wireframes for modal GUI (spectrograph, status indicators)
- [x] Implement basic Qt GUI framework
- [x] Add system tray integration
- [x] Implement recording controls (start/stop)
- [x] Add audio level visualization
- [x] Implement global hotkey support (Ctrl+Space)
  - [x] Basic hotkey registration
  - [x] Toggle recording with hotkey
  - [x] Visual feedback for hotkey activation
  - [x] Error handling for hotkey conflicts
- [ ] Add settings dialog for hotkey configuration
- [x] Implement modal GUI overlay with clear “active/listening” feedback
- [x] Add visual indicator (e.g., spectrograph) when dictation is active
- [] Ensure GUI can be toggled via keyboard shortcut
- [ ] Add configuration UI for keyboard shortcuts to toggle transcription
  - [ ] Allow users to set custom key combinations
  - [ ] Add validation for key combinations
  - [ ] Provide visual feedback for shortcut changes
  - [ ] Ensure shortcuts work globally when application is in background

---

## 5. Keyboard Shortcut Activation

- [x] Implement global hotkey listener to activate/deactivate dictation
- [x] Add option to automatically type after transcription
- [x] Add hotkey transcription with default SUPER+SPACE
- [x] Add validation for keyboard shortcut combinations
- [x] Ensure positive feedback (visual/audio) when system is listening
- [x] Allow dynamic reconfiguration of keyboard shortcuts through the GUI
- [x] Add UI for configuring hotkey dynamically

---

## 6. Universal Typing Integration 

- [x] Implement system-level text injection with multiple methods (pynput, xdotool, GTK, clipboard)
- [x] Add automatic fallback between typing methods
- [x] Integrate with both CLI and Qt GUI
- [x] Test integration with editors, browsers, IDEs, and office suites
- [x] Add clipboard fallback when direct typing is not possible
- [x] Document system dependencies and installation instructions
- [x] Fix PyLint issues and improve code quality to 10.0/10
- [x] Enhance window focus management for more reliable typing
- [x] Improve error handling and debugging for typing methods

### Next Steps for Typing Integration:
- [ ] Add user preferences for typing method priority
- [ ] Add visual feedback when typing is in progress
- [ ] Add support for more typing methods (e.g., wtype for Wayland)

---

## 7. Customization and Commands

- [ ] Implement command parsing for formatting (e.g., “new paragraph”, “bullet point”)
- [ ] Allow users to define custom macros and key-phrases
- [ ] Provide configuration UI or file for managing commands/macros

---

## 8. Privacy and Security

- [ ] Ensure all audio and text data remain local; no network calls
- [ ] Review code for privacy and security best practices

---

## 9. Testing and QA

- [x] Write unit and integration tests for core features
- [x] Fix threading issues in microphone input
- [x] Add end-to-end tests for CLI workflow
- [x] Test basic GUI functionality
- [ ] Add more comprehensive GUI tests
- [ ] Test on major Linux distributions (Ubuntu, Fedora, Mint, etc.)
- [ ] Validate performance on typical consumer hardware

---

## 10. Documentation and Distribution

- [ ] Write user guide and setup instructions
- [ ] Document model management and customization features
- [ ] Prepare standalone binary release and open-source repository
- [ ] Announce and invite community contributions

---

## 11. Stretch Goals (Optional)

- [ ] Develop API/plugins for VS Code, Windsurf, Cursor, and office suites
- [ ] Add support for pre-recorded audio transcription
- [ ] Implement clipboard integration as an alternative input method

---