"""GTK-based GUI for NixWhisper."""

import gi
import logging
import os
from pathlib import Path
from typing import Callable, Optional

gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

from .audio import AudioRecorder
from .config import Config, load_config
from .input import TextInput
from .whisper_model import WhisperTranscriber, TranscriptionResult


class NixWhisperWindow(Gtk.ApplicationWindow):
    """Main application window for NixWhisper."""

    def __init__(self, app, config_path: Optional[str] = None):
        """Initialize the main window.
        
        Args:
            app: The Gtk.Application instance
            config_path: Optional path to config file
        """
        super().__init__(
            application=app,
            title="NixWhisper",
            default_width=400,
            default_height=300
        )
        
        self.app = app
        self.config_path = config_path or os.path.expanduser("~/.config/nixwhisper/config.json")
        self.config = load_config(self.config_path)
        self.recording = False
        self.audio_recorder = None
        self.transcriber = None
        self.text_input = TextInput()
        
        self._setup_ui()
        self._setup_audio()
        self._setup_transcriber()
        
        # Connect signals
        self.connect("delete-event", self.on_delete_event)
        self.connect("key-press-event", self.on_key_press)
        
        # Register global hotkeys
        self._setup_global_hotkeys()
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.set_border_width(10)
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_box)
        
        # Status bar
        self.status_bar = Gtk.Statusbar()
        self.status_bar.set_halign(Gtk.Align.START)
        self.status_bar.set_valign(Gtk.Align.END)
        main_box.pack_end(self.status_bar, False, False, 0)
        
        # Transcription text view
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        scrolled_window.add(self.text_view)
        main_box.pack_start(scrolled_window, True, True, 0)
        
        # Controls
        controls_box = Gtk.Box(spacing=6)
        main_box.pack_start(controls_box, False, False, 0)
        
        # Record button
        self.record_button = Gtk.ToggleButton(label="Start Listening")
        self.record_button.connect("toggled", self.on_record_toggled)
        controls_box.pack_start(self.record_button, False, False, 0)
        
        # Copy button
        copy_button = Gtk.Button(label="Copy to Clipboard")
        copy_button.connect("clicked", self.on_copy_clicked)
        controls_box.pack_start(copy_button, False, False, 0)
        
        # Clear button
        clear_button = Gtk.Button(label="Clear")
        clear_button.connect("clicked", self.on_clear_clicked)
        controls_box.pack_start(clear_button, False, False, 0)
        
        # Settings button
        settings_button = Gtk.Button(label="Settings")
        settings_button.connect("clicked", self.on_settings_clicked)
        controls_box.pack_end(settings_button, False, False, 0)
        
        # Audio level meter
        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0)
        self.level_bar.set_max_value(1.0)
        self.level_bar.set_value(0)
        main_box.pack_start(self.level_bar, False, False, 0)
        
        # Show all widgets
        self.show_all()
        
        # Update status
        self.update_status("Ready")
    
    def _setup_audio(self):
        """Set up the audio recorder."""
        self.audio_recorder = AudioRecorder(
            sample_rate=self.config.audio.sample_rate,
            channels=self.config.audio.channels,
            device=self.config.audio.device,
            blocksize=self.config.audio.blocksize,
            silence_threshold=self.config.audio.silence_threshold,
            silence_duration=self.config.audio.silence_duration,
        )
    
    def _setup_transcriber(self):
        """Set up the Whisper transcriber."""
        model_dir = os.path.expanduser("~/.cache/nixwhisper/models")
        os.makedirs(model_dir, exist_ok=True)
        
        self.transcriber = WhisperTranscriber(
            model_size=self.config.model.name,
            device=self.config.model.device,
            compute_type=self.config.model.compute_type,
            model_dir=model_dir,
        )
    
    def _setup_global_hotkeys(self):
        """Set up global hotkeys."""
        # This is a placeholder. In a real implementation, you would use a library
        # like python-xlib or dbus to register global hotkeys.
        self.update_status("Press Ctrl+Alt+Space to toggle listening")
    
    def update_status(self, message: str):
        """Update the status bar.
        
        Args:
            message: Status message to display
        """
        context_id = self.status_bar.get_context_id("status")
        self.status_bar.push(context_id, message)
    
    def on_record_toggled(self, button):
        """Handle record button toggle."""
        if button.get_active():
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start recording audio."""
        if not self.audio_recorder:
            self._setup_audio()
        
        self.recording = True
        self.record_button.set_label("Listening...")
        self.update_status("Listening...")
        
        def audio_callback(audio_data, rms, is_silent):
            # Update level meter
            GLib.idle_add(self.level_bar.set_value, float(rms))
            
            # Handle silence detection
            if is_silent:
                GLib.idle_add(self.stop_recording)
        
        self.audio_recorder.start_recording(callback=audio_callback)
    
    def stop_recording(self):
        """Stop recording and transcribe the audio."""
        if not self.recording or not self.audio_recorder:
            return
        
        self.recording = False
        self.record_button.set_active(False)
        self.record_button.set_label("Start Listening")
        self.update_status("Processing...")
        
        # Get the recorded audio
        audio_data = self.audio_recorder.stop_recording()
        
        if len(audio_data) == 0:
            self.update_status("No audio recorded")
            return
        
        # Transcribe in a separate thread to keep the UI responsive
        import threading
        
        def transcribe():
            try:
                result = self.transcriber.transcribe(
                    audio=audio_data,
                    language=self.config.model.language,
                    task=self.config.model.task,
                    beam_size=self.config.model.beam_size,
                    best_of=self.config.model.best_of,
                    temperature=self.config.model.temperature,
                    word_timestamps=self.config.model.word_timestamps,
                )
                
                GLib.idle_add(self.on_transcription_complete, result)
                
            except Exception as e:
                GLib.idle_add(
                    self.update_status,
                    f"Error: {str(e)}"
                )
                logging.error("Transcription failed", exc_info=True)
        
        thread = threading.Thread(target=transcribe, daemon=True)
        thread.start()
    
    def on_transcription_complete(self, result: TranscriptionResult):
        """Handle completed transcription.
        
        Args:
            result: Transcription result
        """
        # Update the text view
        buffer = self.text_view.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, result.text + " ")
        
        # Auto-scroll to the end
        mark = buffer.create_mark(
            "end",
            buffer.get_end_iter(),
            left_gravity=False
        )
        self.text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        
        # Type the text if we're not in the middle of a word
        if not result.text.strip().endswith((',', '.', '!', '?', ';', ':')):
            self.text_input.type_text(result.text + " ")
        
        # Update status
        self.update_status(
            f"Transcribed {len(result.text)} characters in {result.duration:.1f}s"
        )
    
    def on_copy_clicked(self, button):
        """Handle copy to clipboard button click."""
        buffer = self.text_view.get_buffer()
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        text = buffer.get_text(start_iter, end_iter, False)
        
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        
        self.update_status("Copied to clipboard")
    
    def on_clear_clicked(self, button):
        """Handle clear button click."""
        buffer = self.text_view.get_buffer()
        buffer.set_text("")
        self.update_status("Cleared text")
    
    def on_settings_clicked(self, button):
        """Handle settings button click."""
        # TODO: Implement settings dialog
        self.update_status("Settings dialog not yet implemented")
    
    def on_key_press(self, widget, event):
        """Handle key press events."""
        # Check for Escape key to stop recording
        if event.keyval == Gdk.KEY_Escape and self.recording:
            self.stop_recording()
            return True
        
        # Check for Ctrl+Q to quit
        if (event.state & Gdk.ModifierType.CONTROL_MASK and
                event.keyval == Gdk.KEY_q):
            self.close()
            return True
            
        return False
    
    def on_delete_event(self, widget, event):
        """Handle window close event."""
        if self.recording:
            self.stop_recording()
        
        # Save window position/size
        width, height = self.get_size()
        self.config.window_width = width
        self.config.window_height = height
        
        # Save config
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            self.config.save(self.config_path)
        except Exception as e:
            logging.error(f"Failed to save config: {e}")
        
        return False


class NixWhisperApp(Gtk.Application):
    """Main application class."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the application.
        
        Args:
            config_path: Optional path to config file
        """
        super().__init__(
            application_id="com.github.nixwhisper.app",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.config_path = config_path
        self.window = None
    
    def do_activate(self):
        """Activate the application."""
        if not self.window:
            self.window = NixWhisperWindow(self, self.config_path)
        
        self.window.present()
    
    def do_startup(self):
        """Startup the application."""
        Gtk.Application.do_startup(self)
        
        # Set up application menu
        self._setup_app_menu()
    
    def _setup_app_menu(self):
        """Set up the application menu."""
        # Create actions
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit)
        self.add_action(quit_action)
        
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)
        
        # Create menu
        menu = Gio.Menu()
        menu.append("_About", "app.about")
        menu.append("_Quit", "app.quit")
        
        self.set_app_menu(menu)
    
    def on_quit(self, action, param):
        """Handle quit action."""
        if self.window:
            self.window.destroy()
    
    def on_about(self, action, param):
        """Show about dialog."""
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(self.window)
        about_dialog.set_modal(True)
        about_dialog.set_program_name("NixWhisper")
        about_dialog.set_version("0.1.0")
        about_dialog.set_copyright("© 2025 NixWhisper Contributors")
        about_dialog.set_license_type(Gtk.License.MIT_X11)
        about_dialog.set_website("https://github.com/yourusername/nixwhisper")
        about_dialog.set_website_label("GitHub")
        about_dialog.set_authors(["Your Name"])
        about_dialog.set_comments("A privacy-focused, offline speech-to-text dictation system for Linux")
        
        about_dialog.run()
        about_dialog.destroy()


def main(config_path: Optional[str] = None):
    """Run the NixWhisper application.
    
    Args:
        config_path: Optional path to config file
    """
    import logging
    logging.basicConfig(level=logging.INFO)
    
    app = NixWhisperApp(config_path)
    return app.run(None)


if __name__ == "__main__":
    import sys
    sys.exit(main())
