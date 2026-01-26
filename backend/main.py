"""
FastAPI main application for ADHD Thought Capture.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from config import API_HOST, API_PORT, DASHBOARD_URL, VAPID_PUBLIC_KEY
from database import (
    init_database,
    get_items_filtered,
    get_item_by_id,
    update_item_status,
    get_user_stats,
    get_config,
    save_config,
    get_all_config,
    search_items,
    search_items_simple,
    search_suggestions,
    rebuild_fts_index
)
from llm_service import generate_daily_picks, get_daily_picks_with_items, classify_and_enrich, classify_and_enrich_image
from telegram_bot import run_bot, create_bot_application
from scheduler import init_scheduler, start_scheduler, stop_scheduler
from models import ItemResponse, ItemUpdate, StatsResponse, EnrichmentData, SearchResponse, SearchResultItem
from auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse, RefreshTokenRequest,
    create_user, authenticate_user, get_user_by_username, get_user_by_id,
    create_tokens, decode_token, require_auth, get_current_user, user_to_response,
    save_push_subscription, get_push_subscriptions, delete_push_subscription
)
from database import save_item

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

    # Rebuild FTS index for existing items
    try:
        await rebuild_fts_index()
        logger.info("FTS search index rebuilt")
    except Exception as e:
        logger.warning(f"Failed to rebuild FTS index: {e}")

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


# ==================== Authentication Endpoints ====================

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    """Register a new user."""
    # Check if username exists
    existing = await get_user_by_username(user_data.username)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )

    # Create user
    user_id = await create_user(
        username=user_data.username,
        password=user_data.password,
        display_name=user_data.display_name
    )

    if not user_id:
        raise HTTPException(
            status_code=500,
            detail="Failed to create user"
        )

    # Get created user
    user = await get_user_by_id(user_id)

    # Generate tokens
    tokens = create_tokens(user_id, user['username'])

    return TokenResponse(
        **tokens,
        user=user_to_response(user)
    )


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login with username and password."""
    user = await authenticate_user(credentials.username, credentials.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Generate tokens
    tokens = create_tokens(user['id'], user['username'])

    return TokenResponse(
        **tokens,
        user=user_to_response(user)
    )


@app.post("/api/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    payload = decode_token(request.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Invalid token type"
        )

    user_id = int(payload.get("sub", 0))
    user = await get_user_by_id(user_id)

    if not user or not user.get('is_active', True):
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive"
        )

    # Generate new tokens
    tokens = create_tokens(user['id'], user['username'])

    return TokenResponse(
        **tokens,
        user=user_to_response(user)
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(require_auth)):
    """Get current authenticated user."""
    return user_to_response(current_user)


# ==================== Direct Messaging Endpoints ====================

@app.post("/api/messages")
async def send_message(
    request: Request,
    current_user: dict = Depends(require_auth)
):
    """
    Send a text message directly (replaces Telegram).
    This endpoint processes the message through the LLM and saves it.
    """
    try:
        body = await request.json()
        text = body.get("text", "").strip()

        if not text:
            raise HTTPException(status_code=400, detail="Message text required")

        logger.info(f"Processing message from user {current_user['username']}: {text[:50]}...")

        # Process through LLM (same as Telegram)
        result = await classify_and_enrich(text, msg_id=None, user_id=current_user['id'])

        return {
            "success": True,
            "item": result
        }

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/messages/image")
async def send_image(
    image: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    current_user: dict = Depends(require_auth)
):
    """
    Send an image message directly (replaces Telegram photo).
    Processes the image through the LLM and saves it.
    """
    try:
        # Validate file type
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read image bytes
        image_bytes = await image.read()

        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

        logger.info(f"Processing image from user {current_user['username']}: {image.filename}")

        # Process through LLM
        result = await classify_and_enrich_image(
            image_bytes=image_bytes,
            mime_type=image.content_type,
            caption=caption,
            msg_id=None,
            user_id=current_user['id']
        )

        return {
            "success": True,
            "item": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Push Notifications Endpoints ====================

@app.get("/api/push/vapid-public-key")
async def get_vapid_key():
    """Get VAPID public key for push notifications."""
    return {"publicKey": VAPID_PUBLIC_KEY}


@app.post("/api/push/subscribe")
async def subscribe_push(
    request: Request,
    current_user: dict = Depends(require_auth)
):
    """Subscribe to push notifications."""
    try:
        subscription = await request.json()

        if not subscription.get('endpoint'):
            raise HTTPException(status_code=400, detail="Invalid subscription")

        success = await save_push_subscription(current_user['id'], subscription)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save subscription")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to push: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/push/unsubscribe")
async def unsubscribe_push(
    request: Request,
    current_user: dict = Depends(require_auth)
):
    """Unsubscribe from push notifications."""
    try:
        body = await request.json()
        endpoint = body.get('endpoint')

        if not endpoint:
            raise HTTPException(status_code=400, detail="Endpoint required")

        success = await delete_push_subscription(current_user['id'], endpoint)

        return {"success": success}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsubscribing from push: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Items Endpoints ====================

@app.get("/api/items", response_model=List[ItemResponse])
async def get_items(
    status: str = Query("pending", description="Filter by status"),
    item_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, le=100, description="Max items to return"),
    current_user: dict = Depends(require_auth)
):
    """Get items filtered by status and type for current user."""
    items = await get_items_filtered(status, item_type, limit, user_id=current_user['id'])

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


@app.get("/api/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    status: Optional[str] = Query(None, description="Filter by status"),
    item_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, le=100, description="Max results to return"),
    current_user: dict = Depends(require_auth)
):
    """
    Full-text search across all item fields for current user.
    Searches in: title, description, verbatim_input, tags, notes, item_type.
    """
    try:
        # Try FTS5 search first
        items = await search_items(q, status, item_type, limit, user_id=current_user['id'])
    except Exception as e:
        # Fallback to simple LIKE search if FTS fails
        logger.warning(f"FTS search failed, using fallback: {e}")
        items = await search_items_simple(q, status, item_type, limit, user_id=current_user['id'])

    # Convert to response model
    results = []
    for item in items:
        enrichment = item.get('enrichment', {})
        if not isinstance(enrichment, dict):
            enrichment = {'links': [], 'consumption_suggestion': None}

        results.append(SearchResultItem(
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
            notes=item.get('notes'),
            search_rank=item.get('search_rank')
        ))

    return SearchResponse(
        query=q,
        total=len(results),
        results=results
    )


@app.post("/api/search/rebuild-index")
async def rebuild_search_index():
    """Rebuild the full-text search index from existing items."""
    try:
        await rebuild_fts_index()
        return {"success": True, "message": "FTS index rebuilt successfully"}
    except Exception as e:
        logger.error(f"Failed to rebuild FTS index: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rebuild index: {str(e)}")


@app.get("/api/search/suggest")
async def get_search_suggestions(
    q: str = Query(..., min_length=2, description="Search query for suggestions"),
    limit: int = Query(8, le=20, description="Max suggestions to return"),
    current_user: dict = Depends(require_auth)
):
    """
    Get search suggestions for autocomplete for current user.
    Returns matching titles and description snippets.
    """
    try:
        suggestions = await search_suggestions(q, limit, user_id=current_user['id'])
        return {"query": q, "suggestions": suggestions}
    except Exception as e:
        logger.warning(f"Suggestions failed: {e}")
        return {"query": q, "suggestions": []}


@app.get("/api/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int, current_user: dict = Depends(require_auth)):
    """Get single item by ID (only if owned by current user)."""
    item = await get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Check ownership
    if item.get('user_id') is not None and item['user_id'] != current_user['id']:
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
async def update_item_endpoint(item_id: int, update: ItemUpdate, current_user: dict = Depends(require_auth)):
    """Update item status/feedback (only if owned by current user)."""
    # Check item exists
    item = await get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Check ownership
    if item.get('user_id') is not None and item['user_id'] != current_user['id']:
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
async def delete_item_endpoint(item_id: int, current_user: dict = Depends(require_auth)):
    """Delete an item permanently (only if owned by current user)."""
    from database import delete_item as db_delete_item

    # Check item exists
    item = await get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Check ownership
    if item.get('user_id') is not None and item['user_id'] != current_user['id']:
        raise HTTPException(status_code=404, detail="Item not found")

    success = await db_delete_item(item_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete item")

    return {"success": True}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(current_user: dict = Depends(require_auth)):
    """Get user statistics for current user."""
    stats = await get_user_stats(user_id=current_user['id'])

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
async def get_today_picks(current_user: dict = Depends(require_auth)):
    """Get or generate daily picks for current user."""
    today = datetime.now().strftime('%Y-%m-%d')
    user_id = current_user['id']

    # Try to get existing picks for this user
    picks_data = await get_daily_picks_with_items(today, user_id=user_id)

    if not picks_data:
        # Generate new picks for this user
        picks_data = await generate_daily_picks(user_id=user_id)

    if not picks_data:
        return {"date": today, "picks": [], "total_estimated_time": 0, "message": ""}

    return picks_data


@app.post("/api/daily-picks/regenerate")
async def regenerate_picks(current_user: dict = Depends(require_auth)):
    """Force regenerate daily picks for current user."""
    picks_data = await generate_daily_picks(user_id=current_user['id'])

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


@app.post("/api/debug/test-classify")
async def debug_test_classify(request: dict):
    """
    Debug endpoint to test LLM classification.
    Returns raw response, parsed JSON, and debug info.
    """
    from llm_service import debug_classify
    from config import LLM_PROVIDER

    input_text = request.get("input", "").strip()
    if not input_text:
        raise HTTPException(status_code=400, detail="Input text required")

    try:
        result = await debug_classify(input_text)
        return {
            "success": True,
            "provider": LLM_PROVIDER,
            **result
        }
    except Exception as e:
        logger.error(f"Debug classify error: {e}")
        return {
            "success": False,
            "provider": LLM_PROVIDER,
            "error": str(e),
            "error_type": type(e).__name__
        }


# Serve frontend static files
import os
# Try multiple possible paths for frontend build
possible_paths = [
    '/app/frontend/build',  # Docker absolute path
    os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build'),  # Relative path
]

frontend_build_path = None
for path in possible_paths:
    if os.path.exists(path) and os.path.isdir(path):
        frontend_build_path = path
        break

logger.info(f"Frontend build path: {frontend_build_path}")
logger.info(f"Checked paths: {possible_paths}")

# Check if frontend build exists
if frontend_build_path:
    logger.info(f"Mounting frontend from: {frontend_build_path}")
    app.mount("/", StaticFiles(directory=frontend_build_path, html=True), name="frontend")
else:
    logger.warning("Frontend build not found!")
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
