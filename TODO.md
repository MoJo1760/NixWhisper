# Step-by-Step TODO List: Offline Real-Time Dictation System for Linux

---

## 1. Project Setup ✅

- [x] Create project repository and initialize version control
- [x] Set up project structure (src, docs, tests, etc.)
- [x] Choose primary programming language and GUI framework (Python with PyGObject/GTK)
- [x] Document build and contribution guidelines

---

## 2. Core Speech-to-Text Engine ✅

- [x] Evaluate and select local speech-to-text backend (e.g., Whisper.cpp, faster-whisper)[2][8]
- [x] Integrate backend for real-time microphone input[2][8]
- [x] Implement basic audio capture and streaming to the model
- [x] Parse and output recognized text in real time
- [x] Add proper error handling for audio device access
- [x] Implement audio level monitoring for VU meter
- [x] Add silence detection for better transcription accuracy
- [x] Update Pydantic validators to V2 for better type safety and future compatibility

---

## 3. Model Management

- [ ] Bundle default OpenWhisper English model
- [ ] Implement user interface for swapping/importing models
- [ ] Ensure model files are managed securely and efficiently

---

## 4. Modal GUI Development

- [ ] Design wireframes for modal GUI (spectrograph, status indicators)
- [ ] Implement modal GUI overlay with clear “active/listening” feedback
- [ ] Add visual indicator (e.g., spectrograph) when dictation is active
- [ ] Ensure GUI can be toggled via keyboard shortcut
- [ ] Add configuration UI for keyboard shortcuts to toggle transcription
  - [ ] Allow users to set custom key combinations
  - [ ] Add validation for key combinations
  - [ ] Provide visual feedback for shortcut changes
  - [ ] Ensure shortcuts work globally when application is in background

---

## 5. Keyboard Shortcut Activation

- [x] Implement global hotkey listener to activate/deactivate dictation
- [ ] Ensure positive feedback (visual/audio) when system is listening
- [ ] Allow dynamic reconfiguration of keyboard shortcuts through the GUI
- [x] Add validation for keyboard shortcut combinations

---

## 6. Universal Typing Integration

- [ ] Implement system-level text injection (simulate typing in any focused input field)
- [ ] Test integration with editors, browsers, IDEs, and office suites[7]
- [ ] Add fallback to clipboard copy/paste if direct typing is not possible

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