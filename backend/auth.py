"""
Authentication module for ThoughtCapture PWA.
Handles user registration, login, JWT tokens, and session management.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

from config import (
    JWT_SECRET_KEY, JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS
)

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer(auto_error=False)


# Pydantic Models

class UserCreate(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=100, pattern=r'^[a-zA-Z0-9_@.\-]+$')
    password: str = Field(..., min_length=6, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """User login request."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User data response (no password)."""
    id: int
    username: str
    display_name: Optional[str]
    created_at: str
    last_login: Optional[str]
    is_active: bool


class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


# Token Payload
class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user_id
    username: str
    type: str  # "access" or "refresh"
    exp: datetime
    iat: datetime


# Password utilities

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# JWT utilities

def create_access_token(user_id: int, username: str) -> str:
    """Create a new access token."""
    now = datetime.utcnow()
    expire = now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "exp": expire,
        "iat": now
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int, username: str) -> str:
    """Create a new refresh token."""
    now = datetime.utcnow()
    expire = now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "refresh",
        "exp": expire,
        "iat": now
    }

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def create_tokens(user_id: int, username: str) -> Dict[str, Any]:
    """Create both access and refresh tokens."""
    return {
        "access_token": create_access_token(user_id, username),
        "refresh_token": create_refresh_token(user_id, username),
        "token_type": "bearer",
        "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


# Database operations for users

async def create_user(username: str, password: str, display_name: Optional[str] = None) -> Optional[int]:
    """Create a new user in the database."""
    from database import get_db

    hashed_password = hash_password(password)

    async with get_db() as db:
        try:
            cursor = await db.execute(
                """INSERT INTO users (username, password_hash, display_name)
                   VALUES (?, ?, ?)""",
                (username.lower(), hashed_password, display_name or username)
            )
            await db.commit()
            logger.info(f"Created user: {username}")
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return None


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username."""
    from database import get_db

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username.lower(),)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    from database import get_db

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_last_login(user_id: int):
    """Update user's last login timestamp."""
    from database import get_db

    async with get_db() as db:
        await db.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
        await db.commit()


async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with username and password."""
    user = await get_user_by_username(username)

    if not user:
        logger.warning(f"Login attempt for non-existent user: {username}")
        return None

    if not user.get('is_active', True):
        logger.warning(f"Login attempt for inactive user: {username}")
        return None

    if not verify_password(password, user['password_hash']):
        logger.warning(f"Invalid password for user: {username}")
        return None

    # Update last login
    await update_last_login(user['id'])

    return user


# FastAPI dependency for authentication

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to get the current authenticated user.
    Returns None if not authenticated (for optional auth endpoints).
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        return None

    if payload.get("type") != "access":
        return None

    user_id = int(payload.get("sub", 0))
    user = await get_user_by_id(user_id)

    if not user or not user.get('is_active', True):
        return None

    return user


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency that requires authentication.
    Raises HTTPException if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = int(payload.get("sub", 0))
    user = await get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


def user_to_response(user: Dict[str, Any]) -> UserResponse:
    """Convert database user dict to UserResponse."""
    return UserResponse(
        id=user['id'],
        username=user['username'],
        display_name=user.get('display_name'),
        created_at=user.get('created_at', ''),
        last_login=user.get('last_login'),
        is_active=user.get('is_active', True)
    )


# Push subscription management

async def save_push_subscription(user_id: int, subscription: Dict[str, Any]) -> bool:
    """Save a push notification subscription for a user."""
    from database import get_db
    import json

    async with get_db() as db:
        try:
            # Check if subscription exists
            cursor = await db.execute(
                "SELECT id FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
                (user_id, subscription.get('endpoint'))
            )
            existing = await cursor.fetchone()

            if existing:
                # Update existing
                await db.execute(
                    """UPDATE push_subscriptions
                       SET keys = ?, updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (json.dumps(subscription.get('keys', {})), existing['id'])
                )
            else:
                # Insert new
                await db.execute(
                    """INSERT INTO push_subscriptions (user_id, endpoint, keys)
                       VALUES (?, ?, ?)""",
                    (user_id, subscription.get('endpoint'), json.dumps(subscription.get('keys', {})))
                )

            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save push subscription: {e}")
            return False


async def get_push_subscriptions(user_id: int) -> list:
    """Get all push subscriptions for a user."""
    from database import get_db
    import json

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM push_subscriptions WHERE user_id = ?",
            (user_id,)
        )
        rows = await cursor.fetchall()

        subscriptions = []
        for row in rows:
            sub = dict(row)
            if sub.get('keys'):
                sub['keys'] = json.loads(sub['keys'])
            subscriptions.append(sub)

        return subscriptions


async def delete_push_subscription(user_id: int, endpoint: str) -> bool:
    """Delete a push subscription."""
    from database import get_db

    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
            (user_id, endpoint)
        )
        await db.commit()
        return cursor.rowcount > 0
