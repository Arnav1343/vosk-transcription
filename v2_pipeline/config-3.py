"""config.py - Configuration for Voice Analytics Pipeline
Centralized settings for Backboard.io integration and LLM analysis."""

import os

# API key for analysis
BACKBOARD_API_KEY = os.environ.get("BACKBOARD_API_KEY", "espr_1XhsRxsk90LV7JC29dOoNf-vYCfPGkLKQp2osRigjT0")

# API key for translation (can be different from analysis key)
TRANSLATION_API_KEY = os.environ.get("TRANSLATION_API_KEY", "espr_-xJfRq2-EDhWYk0SvlNpZJjvZ-HJOU9HB5VriVdz1OY")

# Default LLM model for analysis (Backboard ID)
DEFAULT_MODEL = "gpt-4o"

# Assistant configuration
ASSISTANT_NAME = "VoiceAnalyticsAssistant"
ASSISTANT_INSTRUCTIONS = """You are an expert call center analyst specializing in financial compliance and customer behavior analysis.

Your role is to analyze detected events from voice call transcriptions and provide:
1. Clear, human-readable explanations of what happened
2. Risk assessment (low/medium/high)
3. Recommended actions for compliance or customer service teams

Be concise but thorough. Focus on actionable insights. When analyzing behavioral signals like hesitation or speech changes, explain what they might indicate about customer sentiment or intent.

Always maintain a professional, objective tone suitable for compliance documentation."""

# === Whisper Configuration ===
WHISPER_MODEL = "base"         # options: base, small, medium, large
WHISPER_LANGUAGE = None        # e.g., "hi", "en", "es" (None for auto-detect)
WHISPER_TASK = "transcribe"    # "transcribe" or "translate"
WHISPER_DEVICE = "cpu"         # "cpu" or "cuda"

# === Feature Flags ===
ENABLE_LLM_INTERPRETATION = True  # Master toggle for LLM features
