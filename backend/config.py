"""
Configuration management for ADHD Thought Capture system.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Claude API
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL_CLASSIFY = os.getenv("CLAUDE_MODEL_CLASSIFY", "claude-sonnet-4-20250514")
CLAUDE_MODEL_PICKS = os.getenv("CLAUDE_MODEL_PICKS", "claude-3-5-haiku-20241022")

# Database - use /tmp for writable storage in containers
DATABASE_PATH = os.getenv("DATABASE_PATH", "/tmp/adhd.db")

# Scheduler defaults
DAILY_PICKS_TIME = os.getenv("DAILY_PICKS_TIME", "08:00")
DECAY_DAYS = int(os.getenv("DECAY_DAYS", "30"))
NOTIFICATION_ENABLED = os.getenv("NOTIFICATION_ENABLED", "true").lower() == "true"

# Dashboard
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8000")

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))  # Railway uses PORT

# Email Settings
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")
WEEKLY_DIGEST_TIME = os.getenv("WEEKLY_DIGEST_TIME", "08:00")
WEEKLY_DIGEST_DAY = os.getenv("WEEKLY_DIGEST_DAY", "sat")  # mon, tue, wed, thu, fri, sat, sun

# Resend API (recommended for Railway)
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
