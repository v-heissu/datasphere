"""
FastAPI main application for ADHD Thought Capture.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from config import API_HOST, API_PORT, DASHBOARD_URL
from database import (
    init_database,
    get_items_filtered,
    get_item_by_id,
    update_item_status,
    get_user_stats,
    get_config,
    save_config,
    get_all_config
)
from claude_service import generate_daily_picks, get_daily_picks_with_items
from telegram_bot import run_bot, create_bot_application
from scheduler import init_scheduler, start_scheduler, stop_scheduler
from models import ItemResponse, ItemUpdate, StatsResponse, EnrichmentData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting ADHD Thought Capture...")

    # Initialize database
    init_database()
    logger.info("Database initialized")

    # Initialize and start scheduler
    init_scheduler()
    start_scheduler()
    logger.info("Scheduler started")

    # Start Telegram bot in background
    bot_task = asyncio.create_task(run_bot())
    logger.info("Telegram bot task created")

    yield

    # Shutdown
    logger.info("Shutting down...")
    stop_scheduler()
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="ADHD Thought Capture",
    description="Personal system for capturing and managing ADHD thoughts",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Endpoints

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/items", response_model=List[ItemResponse])
async def get_items(
    status: str = Query("pending", description="Filter by status"),
    item_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, le=100, description="Max items to return")
):
    """Get items filtered by status and type."""
    items = await get_items_filtered(status, item_type, limit)

    # Convert to response model
    response = []
    for item in items:
        enrichment = item.get('enrichment', {})
        if not isinstance(enrichment, dict):
            enrichment = {'links': [], 'consumption_suggestion': None}

        response.append(ItemResponse(
            id=item['id'],
            telegram_message_id=item.get('telegram_message_id'),
            verbatim_input=item['verbatim_input'],
            item_type=item.get('item_type'),
            title=item.get('title'),
            description=item.get('description'),
            enrichment=EnrichmentData(**enrichment),
            priority=item.get('priority', 3),
            estimated_minutes=item.get('estimated_minutes'),
            tags=item.get('tags', []),
            status=item.get('status', 'pending'),
            created_at=datetime.fromisoformat(item['created_at']) if item.get('created_at') else datetime.now(),
            consumed_at=datetime.fromisoformat(item['consumed_at']) if item.get('consumed_at') else None,
            archived_at=datetime.fromisoformat(item['archived_at']) if item.get('archived_at') else None,
            snoozed_until=datetime.fromisoformat(item['snoozed_until']) if item.get('snoozed_until') else None,
            consumption_feedback=item.get('consumption_feedback'),
            notes=item.get('notes')
        ))

    return response


@app.get("/api/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int):
    """Get single item by ID."""
    item = await get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    enrichment = item.get('enrichment', {})
    if not isinstance(enrichment, dict):
        enrichment = {'links': [], 'consumption_suggestion': None}

    return ItemResponse(
        id=item['id'],
        telegram_message_id=item.get('telegram_message_id'),
        verbatim_input=item['verbatim_input'],
        item_type=item.get('item_type'),
        title=item.get('title'),
        description=item.get('description'),
        enrichment=EnrichmentData(**enrichment),
        priority=item.get('priority', 3),
        estimated_minutes=item.get('estimated_minutes'),
        tags=item.get('tags', []),
        status=item.get('status', 'pending'),
        created_at=datetime.fromisoformat(item['created_at']) if item.get('created_at') else datetime.now(),
        consumed_at=datetime.fromisoformat(item['consumed_at']) if item.get('consumed_at') else None,
        archived_at=datetime.fromisoformat(item['archived_at']) if item.get('archived_at') else None,
        snoozed_until=datetime.fromisoformat(item['snoozed_until']) if item.get('snoozed_until') else None,
        consumption_feedback=item.get('consumption_feedback'),
        notes=item.get('notes')
    )


@app.patch("/api/items/{item_id}")
async def update_item(item_id: int, update: ItemUpdate):
    """Update item status/feedback."""
    # Check item exists
    item = await get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    success = await update_item_status(
        item_id,
        status=update.status or item['status'],
        feedback=update.feedback,
        notes=update.notes
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update item")

    return {"success": True}


@app.delete("/api/items/{item_id}")
async def delete_item(item_id: int):
    """Delete an item permanently."""
    from database import delete_item as db_delete_item

    # Check item exists
    item = await get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    success = await db_delete_item(item_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete item")

    return {"success": True}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get user statistics."""
    stats = await get_user_stats()

    return StatsResponse(
        total_captured=stats['total_captured'],
        total_consumed=stats['total_consumed'],
        pending=stats['pending'],
        archived=stats['archived'],
        streak_days=stats['streak_days'],
        consumption_rate=stats['consumption_rate'],
        dashboard_url=DASHBOARD_URL
    )


@app.get("/api/daily-picks")
async def get_today_picks():
    """Get or generate daily picks."""
    today = datetime.now().strftime('%Y-%m-%d')

    # Try to get existing picks
    picks_data = await get_daily_picks_with_items(today)

    if not picks_data:
        # Generate new picks
        picks_data = await generate_daily_picks()

    if not picks_data:
        return {"date": today, "picks": [], "total_estimated_time": 0, "message": ""}

    return picks_data


@app.post("/api/daily-picks/regenerate")
async def regenerate_picks():
    """Force regenerate daily picks."""
    picks_data = await generate_daily_picks()

    if not picks_data:
        raise HTTPException(status_code=500, detail="Failed to generate picks")

    return picks_data


@app.get("/api/config/{key}")
async def get_config_value(key: str):
    """Get config value."""
    value = await get_config(key, '')
    return {"key": key, "value": value}


@app.post("/api/config/{key}")
async def set_config_value(key: str, value: str):
    """Set config value."""
    await save_config(key, value)
    return {"success": True}


@app.get("/api/config")
async def get_all_config_values():
    """Get all config values."""
    config = await get_all_config()
    return config


@app.post("/api/email/test")
async def send_test_email():
    """Send a test weekly digest email."""
    from email_service import send_weekly_digest
    from config import EMAIL_ENABLED

    if not EMAIL_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="Email not enabled. Set EMAIL_ENABLED=true and configure SMTP settings."
        )

    success = await send_weekly_digest()

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email. Check logs.")

    return {"success": True, "message": "Digest email sent!"}


# Serve frontend static files
import os
frontend_build_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')

# Check if frontend build exists
if os.path.exists(frontend_build_path):
    app.mount("/", StaticFiles(directory=frontend_build_path, html=True), name="frontend")
else:
    # Fallback: serve a simple HTML page
    @app.get("/")
    async def root():
        return {
            "message": "ADHD Thought Capture API",
            "docs": "/docs",
            "note": "Frontend not built. Run 'npm run build' in frontend directory."
        }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info"
    )
