"""
Pydantic models for ADHD Thought Capture system.
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum


class ItemType(str, Enum):
    FILM = "film"
    BOOK = "book"
    CONCEPT = "concept"
    MUSIC = "music"
    ART = "art"
    TODO = "todo"
    OTHER = "other"


class ItemStatus(str, Enum):
    PENDING = "pending"
    CONSUMED = "consumed"
    ARCHIVED = "archived"
    SNOOZED = "snoozed"


class ConsumptionFeedback(str, Enum):
    LOVED = "loved"
    MEH = "meh"
    DISAPPOINTED = "disappointed"


class LinkInfo(BaseModel):
    url: str
    type: str  # imdb, spotify, wikipedia, article, etc.


class EnrichmentData(BaseModel):
    links: List[LinkInfo] = Field(default_factory=list)
    consumption_suggestion: Optional[str] = None


class ItemBase(BaseModel):
    verbatim_input: str
    telegram_message_id: Optional[int] = None


class ItemCreate(ItemBase):
    pass


class ItemClassification(BaseModel):
    type: ItemType
    title: str
    description: str
    links: List[LinkInfo] = Field(default_factory=list)
    estimated_minutes: int = 15
    priority: int = Field(default=3, ge=1, le=5)
    tags: List[str] = Field(default_factory=list)
    consumption_suggestion: Optional[str] = None


class ItemResponse(BaseModel):
    id: int
    telegram_message_id: Optional[int]
    verbatim_input: str
    item_type: Optional[str]
    title: Optional[str]
    description: Optional[str]
    enrichment: EnrichmentData
    priority: int
    estimated_minutes: Optional[int]
    tags: List[str]
    status: str
    created_at: datetime
    consumed_at: Optional[datetime]
    archived_at: Optional[datetime]
    snoozed_until: Optional[datetime]
    consumption_feedback: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class ItemUpdate(BaseModel):
    status: Optional[str] = None
    feedback: Optional[str] = None
    notes: Optional[str] = None
    snoozed_until: Optional[datetime] = None


class StatsResponse(BaseModel):
    total_captured: int
    total_consumed: int
    pending: int
    archived: int
    streak_days: int
    consumption_rate: float
    dashboard_url: str


class DailyPickItem(BaseModel):
    item_id: int
    reason: str


class DailyPicksResult(BaseModel):
    picks: List[DailyPickItem]
    total_estimated_time: int
    message: str


class DailyPicksResponse(BaseModel):
    date: str
    picks: List[dict]  # ItemResponse with reason
    total_estimated_time: int
    message: str


class ConfigValue(BaseModel):
    key: str
    value: str


class SearchResultItem(BaseModel):
    """Single search result with relevance score."""
    id: int
    telegram_message_id: Optional[int]
    verbatim_input: str
    item_type: Optional[str]
    title: Optional[str]
    description: Optional[str]
    enrichment: EnrichmentData
    priority: int
    estimated_minutes: Optional[int]
    tags: List[str]
    status: str
    created_at: datetime
    consumed_at: Optional[datetime]
    archived_at: Optional[datetime]
    snoozed_until: Optional[datetime]
    consumption_feedback: Optional[str]
    notes: Optional[str]
    search_rank: Optional[float] = None

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Response for search endpoint."""
    query: str
    total: int
    results: List[SearchResultItem]
