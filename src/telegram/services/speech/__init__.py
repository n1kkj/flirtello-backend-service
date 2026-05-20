"""
Speech services for voice message processing.

This package provides STT (Speech-to-Text) and TTS (Text-to-Speech) services
for converting voice messages to text and text responses to voice.
"""
from .stt_service import transcribe
from .tts_service import synthesize

__all__ = ["transcribe", "synthesize"]
