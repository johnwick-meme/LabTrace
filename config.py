"""
config.py — Project-wide configuration for LabTrace.

Change settings here rather than editing them throughout the codebase.
"""

import os

# ---------------------------------------------------------------------------
# Gemma / Ollama configuration
# ---------------------------------------------------------------------------

# The Ollama model to use.  Change this if you pull a different model.
# Examples: "gemma3:4b", "gemma3:1b", "gemma3:12b"
OLLAMA_MODEL = os.environ.get("LABTRACE_MODEL", "gemma3:4b")

# Base URL for the Ollama HTTP API (default: local)
OLLAMA_BASE_URL = os.environ.get("LABTRACE_OLLAMA_URL", "http://localhost:11434")

# Timeout in seconds for a single Ollama request
OLLAMA_TIMEOUT = int(os.environ.get("LABTRACE_OLLAMA_TIMEOUT", "120"))

# ---------------------------------------------------------------------------
# File paths (relative to project root)
# ---------------------------------------------------------------------------

# Where to find the agent skill file
SKILL_PATH = os.path.join("skills", "lab-investigator", "SKILL.md")

# Where to find reference documents
REFERENCES_DIR = os.path.join("skills", "lab-investigator", "references")
