"""
Configuration management for ADHD Thought Capture system.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("DATABASE_PATH", "/data")).parent

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Claude API
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL_CLASSIFY = os.getenv("CLAUDE_MODEL_CLASSIFY", "claude-sonnet-4-20250514")
CLAUDE_MODEL_PICKS = os.getenv("CLAUDE_MODEL_PICKS", "claude-3-5-haiku-20241022")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "adhd.db"))

# Scheduler defaults
DAILY_PICKS_TIME = os.getenv("DAILY_PICKS_TIME", "08:00")
DECAY_DAYS = int(os.getenv("DECAY_DAYS", "30"))
NOTIFICATION_ENABLED = os.getenv("NOTIFICATION_ENABLED", "true").lower() == "true"

# Dashboard
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8000")

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
