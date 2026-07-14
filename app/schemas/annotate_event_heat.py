"""
`POST /annotate_event_heat` 请求/响应 schema，对应 T1_annotation_v0.6 规约。
"""
from __future__ import annotations

from typing import Optional

from app.schemas.common import CamelModel

SCHEMA_VERSION = "t1_annotation_v0.6"


# ==================== 请求 ====================


class EventInfo(CamelModel):
    event_id: Optional[str] = None
    canonical_name: Optional[str] = None
    event_type: Optional[str] = None  # election|military|diplomatic|protest|disaster|other
    occurred_at_start: Optional[str] = None
    occurred_at_end: Optional[str] = None
    country: Optional[str] = None


class RelatedEntity(CamelModel):
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None  # person|organization|location|media_content|social_account
    name: Optional[str] = None
    published_at: Optional[str] = None
    platform: Optional[str] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    repost_count: Optional[int] = None
    view_count: Optional[int] = None


class AggregateStats(CamelModel):
    total_related_content_count: Optional[int] = None
    total_engagement: Optional[int] = None
    distinct_platform_count: Optional[int] = None
    earliest_content_at: Optional[str] = None
    latest_content_at: Optional[str] = None


class AnnotateEventHeatRequest(CamelModel):
    event: Optional[EventInfo] = None
    related_entities: list[RelatedEntity] = []
    aggregate_stats: Optional[AggregateStats] = None


# ==================== 响应 ====================


class EventHeat(CamelModel):
    heat_level: str = "unclear"  # low|medium|high|explosive|unclear
    heat_score: Optional[float] = None  # 0.0-1.0
    heat_signal_types: list[str] = []
    reasoning: Optional[str] = None


class AnnotateEventHeatResponse(CamelModel):
    schema_version: str = SCHEMA_VERSION
    event_heat: EventHeat = EventHeat()
    overall_confidence: Optional[float] = None
    processed_at: Optional[str] = None
