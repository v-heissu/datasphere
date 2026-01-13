"""
SQLite database operations for ADHD Thought Capture system.
"""

import sqlite3
import json
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from config import DATABASE_PATH


# SQL Schema (base tables only)
SCHEMA = """
-- Core items table
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_message_id INTEGER UNIQUE,
    verbatim_input TEXT NOT NULL,

    -- Classification (da Claude)
    item_type TEXT,
    title TEXT,
    description TEXT,

    -- Enrichment (JSON flessibile)
    enrichment JSON,

    -- Metadata
    priority INTEGER DEFAULT 3,
    estimated_minutes INTEGER,
    tags TEXT,

    -- Status
    status TEXT DEFAULT 'pending',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    consumed_at TIMESTAMP,
    archived_at TIMESTAMP,
    snoozed_until TIMESTAMP,

    -- Feedback
    consumption_feedback TEXT,
    notes TEXT
);

-- User configuration
CREATE TABLE IF NOT EXISTS user_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily picks history
CREATE TABLE IF NOT EXISTS daily_picks (
    date TEXT PRIMARY KEY,
    picks_json TEXT,
    total_estimated_time INTEGER DEFAULT 0,
    message TEXT,
    consumed_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User stats (denormalized for performance)
CREATE TABLE IF NOT EXISTS stats (
    date TEXT PRIMARY KEY,
    items_captured INTEGER DEFAULT 0,
    items_consumed INTEGER DEFAULT 0,
    items_archived INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_type ON items(item_type);
CREATE INDEX IF NOT EXISTS idx_items_created ON items(created_at);
"""

# FTS5 Schema (separate for robustness)
FTS_SCHEMA = """
-- Full-text search virtual table (FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
    title,
    description,
    verbatim_input,
    tags,
    notes,
    item_type,
    content='items',
    content_rowid='id'
);

-- Triggers to keep FTS index synchronized with items table
CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
    INSERT INTO items_fts(rowid, title, description, verbatim_input, tags, notes, item_type)
    VALUES (new.id, new.title, new.description, new.verbatim_input, new.tags, new.notes, new.item_type);
END;

CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, title, description, verbatim_input, tags, notes, item_type)
    VALUES ('delete', old.id, old.title, old.description, old.verbatim_input, old.tags, old.notes, old.item_type);
END;

CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, title, description, verbatim_input, tags, notes, item_type)
    VALUES ('delete', old.id, old.title, old.description, old.verbatim_input, old.tags, old.notes, old.item_type);
    INSERT INTO items_fts(rowid, title, description, verbatim_input, tags, notes, item_type)
    VALUES (new.id, new.title, new.description, new.verbatim_input, new.tags, new.notes, new.item_type);
END;
"""

# Default config values
DEFAULT_CONFIG = {
    'user_background': '',
    'telegram_chat_id': '',
    'daily_picks_time': '08:00',
    'decay_days': '30',
    'notification_enabled': 'true'
}


def init_database():
    """Initialize database with schema (synchronous, for startup)."""
    import logging
    from pathlib import Path
    logger = logging.getLogger(__name__)

    # Ensure parent directory exists (important for Railway volumes)
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initializing database at: {DATABASE_PATH}")
    conn = sqlite3.connect(DATABASE_PATH)
    conn.executescript(SCHEMA)

    # Insert default config
    for key, value in DEFAULT_CONFIG.items():
        conn.execute(
            "INSERT OR IGNORE INTO user_config (key, value) VALUES (?, ?)",
            (key, value)
        )

    conn.commit()
    conn.close()

    # Initialize FTS separately (more robust)
    init_fts()


def init_fts():
    """Initialize FTS5 full-text search (separate for robustness)."""
    import logging
    logger = logging.getLogger(__name__)

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.executescript(FTS_SCHEMA)
        conn.commit()
        logger.info("FTS5 search initialized successfully")
    except Exception as e:
        logger.warning(f"FTS5 init failed (will use fallback search): {e}")
    finally:
        conn.close()


def rebuild_fts_sync():
    """Rebuild FTS index synchronously (for use after init or repair)."""
    import logging
    logger = logging.getLogger(__name__)

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # Drop existing FTS table and triggers if corrupted
        conn.execute("DROP TRIGGER IF EXISTS items_ai")
        conn.execute("DROP TRIGGER IF EXISTS items_ad")
        conn.execute("DROP TRIGGER IF EXISTS items_au")
        conn.execute("DROP TABLE IF EXISTS items_fts")
        conn.commit()

        # Recreate FTS schema
        conn.executescript(FTS_SCHEMA)
        conn.commit()

        # Populate FTS from existing items
        conn.execute("""
            INSERT INTO items_fts(rowid, title, description, verbatim_input, tags, notes, item_type)
            SELECT id, title, description, verbatim_input, tags, notes, item_type FROM items
        """)
        conn.commit()
        logger.info("FTS index rebuilt successfully")
        return True
    except Exception as e:
        logger.error(f"FTS rebuild failed: {e}")
        return False
    finally:
        conn.close()


@asynccontextmanager
async def get_db():
    """Async context manager for database connections."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


# Configuration operations

async def get_config(key: str, default: str = '') -> str:
    """Get a configuration value."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT value FROM user_config WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row['value'] if row else default


async def save_config(key: str, value: str):
    """Save a configuration value."""
    async with get_db() as db:
        await db.execute(
            """INSERT INTO user_config (key, value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP""",
            (key, value, value)
        )
        await db.commit()


async def get_all_config() -> Dict[str, str]:
    """Get all configuration values."""
    async with get_db() as db:
        cursor = await db.execute("SELECT key, value FROM user_config")
        rows = await cursor.fetchall()
        return {row['key']: row['value'] for row in rows}


# Item operations

def row_to_dict(row: aiosqlite.Row) -> Dict[str, Any]:
    """Convert a database row to a dictionary with parsed JSON fields."""
    if row is None:
        return None

    d = dict(row)

    # Parse JSON fields
    if 'enrichment' in d and d['enrichment']:
        try:
            d['enrichment'] = json.loads(d['enrichment'])
        except (json.JSONDecodeError, TypeError):
            d['enrichment'] = {'links': [], 'consumption_suggestion': None}
    else:
        d['enrichment'] = {'links': [], 'consumption_suggestion': None}

    if 'tags' in d and d['tags']:
        try:
            d['tags'] = json.loads(d['tags'])
        except (json.JSONDecodeError, TypeError):
            d['tags'] = []
    else:
        d['tags'] = []

    return d


async def save_item(
    verbatim_input: str,
    telegram_message_id: Optional[int] = None,
    item_type: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    enrichment: Optional[Dict] = None,
    priority: int = 3,
    estimated_minutes: Optional[int] = None,
    tags: Optional[List[str]] = None
) -> int:
    """Save a new item to the database."""
    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO items (
                telegram_message_id, verbatim_input, item_type, title,
                description, enrichment, priority, estimated_minutes, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                telegram_message_id,
                verbatim_input,
                item_type,
                title,
                description,
                json.dumps(enrichment) if enrichment else None,
                priority,
                estimated_minutes,
                json.dumps(tags) if tags else None
            )
        )
        await db.commit()

        # Update daily stats
        await update_daily_stats('captured')

        return cursor.lastrowid


async def update_item(item_id: int, **kwargs) -> bool:
    """Update an item in the database."""
    async with get_db() as db:
        # Build update query dynamically
        updates = []
        values = []

        for key, value in kwargs.items():
            if key == 'enrichment' and value is not None:
                value = json.dumps(value)
            elif key == 'tags' and value is not None:
                value = json.dumps(value)

            updates.append(f"{key} = ?")
            values.append(value)

        if not updates:
            return False

        values.append(item_id)

        query = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
        cursor = await db.execute(query, values)
        await db.commit()

        return cursor.rowcount > 0


async def update_item_status(item_id: int, status: str, feedback: Optional[str] = None, notes: Optional[str] = None) -> bool:
    """Update item status with optional feedback."""
    async with get_db() as db:
        updates = {'status': status}

        if status == 'consumed':
            updates['consumed_at'] = datetime.now().isoformat()
        elif status == 'archived':
            updates['archived_at'] = datetime.now().isoformat()

        if feedback:
            updates['consumption_feedback'] = feedback
        if notes:
            updates['notes'] = notes

        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [item_id]

        cursor = await db.execute(
            f"UPDATE items SET {set_clause} WHERE id = ?",
            values
        )
        await db.commit()

        # Update stats if consumed or archived
        if status == 'consumed':
            await update_daily_stats('consumed')
        elif status == 'archived':
            await update_daily_stats('archived')

        return cursor.rowcount > 0


async def get_item_by_id(item_id: int) -> Optional[Dict[str, Any]]:
    """Get a single item by ID."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM items WHERE id = ?", (item_id,)
        )
        row = await cursor.fetchone()
        return row_to_dict(row)


async def delete_item(item_id: int) -> bool:
    """Delete an item permanently from the database."""
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM items WHERE id = ?", (item_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_items_filtered(
    status: Optional[str] = None,
    item_type: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get items filtered by status and type."""
    async with get_db() as db:
        query = "SELECT * FROM items WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if item_type:
            query += " AND item_type = ?"
            params.append(item_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        return [row_to_dict(row) for row in rows]


async def get_recent_items(limit: int = 5) -> List[Dict[str, Any]]:
    """Get most recent items for context."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT item_type, title, description FROM items ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_items_older_than(days: int, status: str = 'pending') -> List[Dict[str, Any]]:
    """Get items older than N days with given status."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM items WHERE status = ? AND created_at < ?",
            (status, cutoff)
        )
        rows = await cursor.fetchall()
        return [row_to_dict(row) for row in rows]


async def get_pending_items_for_picks(limit: int = 50) -> List[Dict[str, Any]]:
    """Get pending items formatted for daily picks generation."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT id, item_type, title, estimated_minutes, priority, created_at
               FROM items WHERE status = 'pending'
               ORDER BY priority DESC, created_at ASC LIMIT ?""",
            (limit,)
        )
        rows = await cursor.fetchall()

        items = []
        for row in rows:
            d = dict(row)
            age_days = (datetime.now() - datetime.fromisoformat(d['created_at'])).days
            d['age_days'] = age_days
            items.append(d)

        return items


# Daily picks operations

async def get_daily_picks_for_date(date: str) -> Optional[Dict[str, Any]]:
    """Get daily picks for a specific date."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM daily_picks WHERE date = ?", (date,)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        d = dict(row)
        if d['picks_json']:
            d['picks'] = json.loads(d['picks_json'])
        else:
            d['picks'] = []

        return d


async def save_daily_picks(date: str, picks: List[Dict], total_time: int = 0, message: str = ''):
    """Save daily picks for a date."""
    async with get_db() as db:
        await db.execute(
            """INSERT INTO daily_picks (date, picks_json, total_estimated_time, message)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET
               picks_json = ?, total_estimated_time = ?, message = ?""",
            (date, json.dumps(picks), total_time, message,
             json.dumps(picks), total_time, message)
        )
        await db.commit()


# Stats operations

async def update_daily_stats(action: str):
    """Update daily stats for captured/consumed/archived actions."""
    today = datetime.now().strftime('%Y-%m-%d')

    column_map = {
        'captured': 'items_captured',
        'consumed': 'items_consumed',
        'archived': 'items_archived'
    }

    column = column_map.get(action)
    if not column:
        return

    async with get_db() as db:
        # Check if row exists
        cursor = await db.execute(
            "SELECT * FROM stats WHERE date = ?", (today,)
        )
        row = await cursor.fetchone()

        if row:
            await db.execute(
                f"UPDATE stats SET {column} = {column} + 1, updated_at = CURRENT_TIMESTAMP WHERE date = ?",
                (today,)
            )
        else:
            await db.execute(
                f"INSERT INTO stats (date, {column}) VALUES (?, 1)",
                (today,)
            )

        await db.commit()


async def get_user_stats() -> Dict[str, Any]:
    """Get aggregated user statistics."""
    async with get_db() as db:
        # Total counts
        cursor = await db.execute("SELECT COUNT(*) as count FROM items")
        total_captured = (await cursor.fetchone())['count']

        cursor = await db.execute("SELECT COUNT(*) as count FROM items WHERE status = 'consumed'")
        total_consumed = (await cursor.fetchone())['count']

        cursor = await db.execute("SELECT COUNT(*) as count FROM items WHERE status = 'pending'")
        pending = (await cursor.fetchone())['count']

        cursor = await db.execute("SELECT COUNT(*) as count FROM items WHERE status = 'archived'")
        archived = (await cursor.fetchone())['count']

        # Calculate streak
        streak_days = await calculate_streak()

        # Consumption rate
        consumption_rate = (total_consumed / total_captured * 100) if total_captured > 0 else 0

        return {
            'total_captured': total_captured,
            'total_consumed': total_consumed,
            'pending': pending,
            'archived': archived,
            'streak_days': streak_days,
            'consumption_rate': consumption_rate
        }


async def calculate_streak() -> int:
    """Calculate consecutive days streak of consumption."""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT date, items_consumed FROM stats
               WHERE items_consumed > 0
               ORDER BY date DESC LIMIT 30"""
        )
        rows = await cursor.fetchall()

        if not rows:
            return 0

        streak = 0
        expected_date = datetime.now().date()

        for row in rows:
            row_date = datetime.strptime(row['date'], '%Y-%m-%d').date()

            if row_date == expected_date:
                streak += 1
                expected_date -= timedelta(days=1)
            elif row_date == expected_date - timedelta(days=1):
                # Allow for today not having activity yet
                expected_date = row_date
                streak += 1
                expected_date -= timedelta(days=1)
            else:
                break

        return streak


async def get_stats_last_7_days() -> Dict[str, int]:
    """Get stats for the last 7 days."""
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    async with get_db() as db:
        cursor = await db.execute(
            """SELECT SUM(items_captured) as captured, SUM(items_consumed) as consumed
               FROM stats WHERE date >= ?""",
            (cutoff,)
        )
        row = await cursor.fetchone()

        return {
            'captured': row['captured'] or 0,
            'consumed': row['consumed'] or 0
        }


# Full-text search operations

async def rebuild_fts_index():
    """Rebuild the FTS index from existing items (drop and recreate if corrupted)."""
    async with get_db() as db:
        # Drop existing FTS table and triggers (handles corruption)
        await db.execute("DROP TRIGGER IF EXISTS items_ai")
        await db.execute("DROP TRIGGER IF EXISTS items_ad")
        await db.execute("DROP TRIGGER IF EXISTS items_au")
        await db.execute("DROP TABLE IF EXISTS items_fts")
        await db.commit()

        # Recreate FTS table
        await db.execute("""
            CREATE VIRTUAL TABLE items_fts USING fts5(
                title,
                description,
                verbatim_input,
                tags,
                notes,
                item_type,
                content='items',
                content_rowid='id'
            )
        """)

        # Recreate triggers
        await db.execute("""
            CREATE TRIGGER items_ai AFTER INSERT ON items BEGIN
                INSERT INTO items_fts(rowid, title, description, verbatim_input, tags, notes, item_type)
                VALUES (new.id, new.title, new.description, new.verbatim_input, new.tags, new.notes, new.item_type);
            END
        """)
        await db.execute("""
            CREATE TRIGGER items_ad AFTER DELETE ON items BEGIN
                INSERT INTO items_fts(items_fts, rowid, title, description, verbatim_input, tags, notes, item_type)
                VALUES ('delete', old.id, old.title, old.description, old.verbatim_input, old.tags, old.notes, old.item_type);
            END
        """)
        await db.execute("""
            CREATE TRIGGER items_au AFTER UPDATE ON items BEGIN
                INSERT INTO items_fts(items_fts, rowid, title, description, verbatim_input, tags, notes, item_type)
                VALUES ('delete', old.id, old.title, old.description, old.verbatim_input, old.tags, old.notes, old.item_type);
                INSERT INTO items_fts(rowid, title, description, verbatim_input, tags, notes, item_type)
                VALUES (new.id, new.title, new.description, new.verbatim_input, new.tags, new.notes, new.item_type);
            END
        """)

        # Populate FTS from existing items
        await db.execute("""
            INSERT INTO items_fts(rowid, title, description, verbatim_input, tags, notes, item_type)
            SELECT id, title, description, verbatim_input, tags, notes, item_type FROM items
        """)
        await db.commit()


async def search_items(
    query: str,
    status: Optional[str] = None,
    item_type: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Full-text search across all item fields.

    Args:
        query: Search query string (supports FTS5 syntax)
        status: Optional filter by status
        item_type: Optional filter by item type
        limit: Maximum results to return

    Returns:
        List of matching items with search rank
    """
    async with get_db() as db:
        # Build the query with optional filters
        # Use FTS5 match with bm25 ranking
        sql = """
            SELECT items.*, bm25(items_fts) as search_rank
            FROM items
            INNER JOIN items_fts ON items.id = items_fts.rowid
            WHERE items_fts MATCH ?
        """
        params = [query]

        if status:
            sql += " AND items.status = ?"
            params.append(status)

        if item_type:
            sql += " AND items.item_type = ?"
            params.append(item_type)

        sql += " ORDER BY search_rank LIMIT ?"
        params.append(limit)

        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()

        results = []
        for row in rows:
            item = row_to_dict(row)
            # Add search rank (lower is better in bm25)
            item['search_rank'] = row['search_rank']
            results.append(item)

        return results


async def search_items_simple(
    query: str,
    status: Optional[str] = None,
    item_type: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Simple LIKE-based search fallback if FTS fails.
    Searches across title, description, verbatim_input, tags, and notes.
    """
    async with get_db() as db:
        search_pattern = f"%{query}%"

        sql = """
            SELECT * FROM items
            WHERE (
                title LIKE ? OR
                description LIKE ? OR
                verbatim_input LIKE ? OR
                tags LIKE ? OR
                notes LIKE ? OR
                item_type LIKE ?
            )
        """
        params = [search_pattern] * 6

        if status:
            sql += " AND status = ?"
            params.append(status)

        if item_type:
            sql += " AND item_type = ?"
            params.append(item_type)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()

        return [row_to_dict(row) for row in rows]


# Initialize database on module import
if __name__ == "__main__":
    init_database()
    print(f"Database initialized at {DATABASE_PATH}")
