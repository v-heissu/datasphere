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

# LLM Provider Selection ("gemini" or "claude")
# Gemini 2.0 Flash is FREE (1500 req/day) with native Google Search
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

# Gemini API (recommended - FREE tier available)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL_CLASSIFY = os.getenv("GEMINI_MODEL_CLASSIFY", "gemini-2.0-flash")
GEMINI_MODEL_IMAGE = os.getenv("GEMINI_MODEL_IMAGE", "gemini-2.5-flash-image")  # Dedicated model for images
GEMINI_MODEL_PICKS = os.getenv("GEMINI_MODEL_PICKS", "gemini-2.0-flash")

# Claude API (fallback option)
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL_CLASSIFY = os.getenv("CLAUDE_MODEL_CLASSIFY", "claude-sonnet-4-20250514")
CLAUDE_MODEL_PICKS = os.getenv("CLAUDE_MODEL_PICKS", "claude-3-5-haiku-20241022")

# Database - use /data for persistent storage with Railway Volume
# IMPORTANT: On Railway, create a volume and mount it to /data
DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/adhd.db")

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

# JWT Authentication
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-min-32-chars!")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Push Notifications (Web Push / VAPID)
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "mailto:admin@example.com")
