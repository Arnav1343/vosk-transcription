"""config.example.py - Template for Voice Analytics Pipeline settings.
Copy this file to config.py and fill in your actual API keys."""

import os

# API key for analysis
BACKBOARD_API_KEY = os.environ.get("BACKBOARD_API_KEY", "YOUR_BACKBOARD_KEY_HERE")

# API key for translation
TRANSLATION_API_KEY = os.environ.get("TRANSLATION_API_KEY", "YOUR_TRANSLATION_KEY_HERE")

# Default LLM model for analysis
DEFAULT_MODEL = "gpt-4o"

# Assistant configuration
ASSISTANT_NAME = "VoiceAnalyticsAssistant"
ASSISTANT_INSTRUCTIONS = """You are an expert call center analyst..."""

# === Whisper Configuration ===
WHISPER_MODEL = "base"
WHISPER_LANGUAGE = None
WHISPER_TASK = "transcribe"
WHISPER_DEVICE = "cpu"

# === Feature Flags ===
ENABLE_LLM_INTERPRETATION = True
