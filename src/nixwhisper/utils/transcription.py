"""Common utilities for transcription handling."""

from typing import List, Optional, Dict, Any

from ..transcriber.base import TranscriptionSegment


def process_whisper_segments(segments: List[Any], include_speaker: bool = False) -> tuple[List[TranscriptionSegment], List[str]]:
    """Process Whisper model segments into our format.

    Args:
        segments: List of segments from Whisper model
        include_speaker: Whether to include speaker information

    Returns:
        Tuple of (list of TranscriptionSegment, list of text strings)
    """
    transcription_segments = []
    full_text = []

    for segment in segments:
        # Create word-level timestamps if available
        words = None
        if hasattr(segment, 'words') and segment.words:
            words = [
                {
                    'word': word.word,
                    'start': word.start,
                    'end': word.end,
                    'confidence': word.probability
                }
                for word in segment.words
            ]

        # Create segment
        seg = TranscriptionSegment(
            start=segment.start,
            end=segment.end,
            text=segment.text.strip(),
            words=words,
            speaker=None if not include_speaker else getattr(segment, 'speaker', None),
            confidence=segment.avg_logprob if hasattr(segment, 'avg_logprob') else None
        )

        transcription_segments.append(seg)
        full_text.append(segment.text.strip())

    return transcription_segments, full_text
