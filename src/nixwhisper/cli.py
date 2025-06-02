"""Command-line interface for NixWhisper."""

import argparse
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from .audio import AudioRecorder
from .config import Config, load_config
from .universal_typing import UniversalTyping
from .whisper_model import WhisperTranscriber, TranscriptionResult


class NixWhisperCLI:
    """Command-line interface for NixWhisper."""
    
    def __init__(self, config: Config):
        """Initialize the CLI.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.running = True
        self.audio_recorder = None
        self.transcriber = None
        # Initialize universal typing with default preferred methods
        self.typer = UniversalTyping()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle termination signals."""
        print("\nShutting down...")
        self.running = False
        
        if self.audio_recorder and self.audio_recorder.is_recording():
            self.audio_recorder.stop_recording()
    
    def setup(self):
        """Set up the application."""
        print("Setting up NixWhisper...")
        
        # Set up audio
        self.audio_recorder = AudioRecorder(
            sample_rate=self.config.audio.sample_rate,
            channels=self.config.audio.channels,
            device=self.config.audio.device,
            blocksize=self.config.audio.blocksize,
            silence_threshold=self.config.audio.silence_threshold,
            silence_duration=self.config.audio.silence_duration,
        )
        
        # Set up Whisper
        model_dir = os.path.expanduser("~/.cache/nixwhisper/models")
        os.makedirs(model_dir, exist_ok=True)
        
        print(f"Loading Whisper model: {self.config.model.name}...")
        self.transcriber = WhisperTranscriber(
            model_size=self.config.model.name,
            device=self.config.model.device,
            compute_type=self.config.model.compute_type,
            model_dir=model_dir,
        )
        
        print("Ready! Press Ctrl+C to exit.")
    
    def run(self):
        """Run the CLI application."""
        self.setup()
        
        print("\nPress Enter to start/stop recording, or 'q' to quit")
        
        try:
            while self.running:
                # Wait for user input
                user_input = input("\nPress Enter to record (or 'q' to quit): ")
                
                if user_input.lower() == 'q':
                    self.running = False
                    continue
                
                if self.audio_recorder.is_recording():
                    continue
                
                # Start recording
                print("\nRecording... Press Enter to stop")
                self.audio_recorder.start_recording(self.audio_callback)
                
                # Wait for Enter to stop
                input()
                
                if self.audio_recorder.is_recording():
                    self.stop_recording()
        
        except (KeyboardInterrupt, EOFError):
            print("\nShutting down...")
        
        finally:
            if self.audio_recorder and self.audio_recorder.is_recording():
                self.audio_recorder.stop_recording()
    
    def audio_callback(self, audio_data, rms, is_silent):
        """Callback for audio data during recording."""
        # Show audio level
        level = "#" * int(rms * 50)
        print(f"\rLevel: [{level:<50}] {rms:.2f}", end="", flush=True)
        
        # Auto-stop on silence if enabled
        if is_silent and self.config.audio.silence_duration > 0:
            print("\nSilence detected, stopping recording...")
            self.stop_recording()
    
    def stop_recording(self):
        """Stop recording and transcribe the audio."""
        if not self.audio_recorder or not self.audio_recorder.is_recording():
            return
        
        print("\nProcessing...")
        
        # Get the recorded audio
        audio_data = self.audio_recorder.stop_recording()
        
        if len(audio_data) == 0:
            print("No audio recorded")
            return
        
        try:
            # Transcribe the audio
            result = self.transcriber.transcribe(
                audio=audio_data,
                language=self.config.model.language,
                task=self.config.model.task,
                beam_size=self.config.model.beam_size,
                best_of=self.config.model.best_of,
                temperature=self.config.model.temperature,
                word_timestamps=self.config.model.word_timestamps,
            )
            
            # Print the result
            print("\nTranscription:")
            print("-" * 80)
            print(result.text)
            print("-" * 80)
            
            # Type the text if requested
            if input("\nType this text? (y/N): ").lower() == 'y':
                self.typer.type_text(result.text)
                print("Text typed.")
            
            print(f"\nTranscribed {len(result.text)} characters in {result.duration:.1f}s")
            
        except Exception as e:
            print(f"Error during transcription: {e}", file=sys.stderr)
            logging.error("Transcription failed", exc_info=True)


def parse_args(args=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="NixWhisper - Offline Speech-to-Text")
    
    # Add version
    parser.add_argument(
        "--version",
        action="version",
        version="NixWhisper 0.1.0"
    )
    
    # Global options
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.expanduser("~/.config/nixwhisper/config.json"),
        help="Path to config file"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Run with GUI (default: auto-detect)"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Force command-line interface"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    # Add list-devices command
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit"
    )
    
    # Model options
    model_group = parser.add_argument_group("Model options")
    model_group.add_argument(
        "--model",
        type=str,
        choices=["tiny", "base", "small", "medium", "large"],
        help="Model to use (default: base)"
    )
    model_group.add_argument(
        "--device",
        type=str,
        choices=["auto", "cpu", "cuda"],
        help="Device to use (default: auto)"
    )
    model_group.add_argument(
        "--compute-type",
        type=str,
        choices=["int8", "float16", "float32"],
        help="Compute type (default: int8)"
    )
    
    # Audio options
    audio_group = parser.add_argument_group("Audio options")
    audio_group.add_argument(
        "--device-id",
        type=int,
        help="Audio device ID (default: auto)"
    )
    audio_group.add_argument(
        "--sample-rate",
        type=int,
        help=f"Sample rate in Hz (default: 16000)"
    )
    
    # Transcription options
    transcribe_group = parser.add_argument_group("Transcription options")
    transcribe_group.add_argument(
        "--language",
        type=str,
        help="Language code (e.g., 'en', 'es', 'fr')"
    )
    transcribe_group.add_argument(
        "--task",
        type=str,
        choices=["transcribe", "translate"],
        help="Task type (transcribe or translate)"
    )
    
    return parser.parse_args(args)


def list_audio_devices():
    """List available audio devices."""
    import sounddevice as sd
    
    print("\nAvailable audio input devices:")
    print("-" * 50)
    
    try:
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Only show input devices
                print(f"Device {i}: {device['name']}")
                print(f"  Input channels: {device['max_input_channels']}")
                print(f"  Default sample rate: {device['default_samplerate']} Hz")
                print()
    except Exception as e:
        print(f"Error listing audio devices: {e}")
        return 1
    
    return 0


def main(args=None):
    """Main entry point for the CLI."""
    # Parse command-line arguments
    args = parse_args(args)
    
    # Handle version flag
    if hasattr(args, 'version') and args.version:
        print("NixWhisper 0.1.0")
        return 0
    
    # Handle list-devices flag
    if hasattr(args, 'list_devices') and args.list_devices:
        return list_audio_devices()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1
    
    # Apply command-line overrides
    if args.model:
        config.model.name = args.model
    if args.device:
        config.model.device = args.device
    if args.compute_type:
        config.model.compute_type = args.compute_type
    if args.device_id is not None:
        config.audio.device = args.device_id
    if args.sample_rate:
        config.audio.sample_rate = args.sample_rate
    if args.language:
        config.model.language = args.language
    if args.task:
        config.model.task = args.task
    
    # Determine if we should use GUI
    use_gui = args.gui or (not args.cli and os.getenv('DISPLAY') and not os.getenv('SSH_TTY'))
    
    if use_gui:
        try:
            from .gui import NixWhisperApp
            app = NixWhisperApp(config_path=args.config)
            return app.run(None)
        except ImportError as e:
            print(f"GUI not available: {e}", file=sys.stderr)
            print("Falling back to CLI mode.")
    
    # Run in CLI mode
    try:
        cli = NixWhisperCLI(config)
        cli.run()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        logging.exception("CLI error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
