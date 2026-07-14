"""
`POST /annotate_account` 请求/响应 schema，对应 T1_annotation_v0.6 规约。
"""
from __future__ import annotations

from typing import Optional

from app.schemas.common import CamelModel

SCHEMA_VERSION = "t1_annotation_v0.6"


# ==================== 请求 ====================


class AnnotateAccountRequest(CamelModel):
    platform: Optional[str] = None
    platform_user_id: Optional[str] = None
    account_entity_type: Optional[str] = None  # user|channel|page|group|community|forum_board|news_source
    platform_native_type: Optional[str] = None

    handle: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    self_declared_location: Optional[str] = None
    verified: Optional[bool] = None
    verified_type: Optional[str] = None  # none|blue|org|government|media
    is_suspended: Optional[bool] = None
    account_created_at: Optional[str] = None

    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    subscriber_count: Optional[int] = None
    member_count: Optional[int] = None
    post_count: Optional[int] = None
    view_count: Optional[int] = None

    recent_post_samples: list[str] = []


# ==================== 响应 ====================


class AccountReference(CamelModel):
    platform: Optional[str] = None
    platform_user_id: Optional[str] = None
    account_entity_type: Optional[str] = None
    platform_native_type: Optional[str] = None
    handle: Optional[str] = None
    display_name: Optional[str] = None


class PrimaryAccountCategory(CamelModel):
    category_label: str = "unknown"
    evidence_ids: list[str] = []


class AccountSubtypeTag(CamelModel):
    subtype_tag: str
    evidence_ids: list[str] = []


class AutomationSuspicion(CamelModel):
    suspicion_level: str = "unclear"
    evidence_ids: list[str] = []


class AccountType(CamelModel):
    primary_account_category: PrimaryAccountCategory = PrimaryAccountCategory()
    account_subtype_tags: list[AccountSubtypeTag] = []
    automation_suspicion: AutomationSuspicion = AutomationSuspicion()


class AccountEvidenceClue(CamelModel):
    evidence_id: str
    # profile_text/verification_info/account_metadata/activity_statistics/recent_post_sample/platform_label/other
    evidence_type: str
    # display_name/bio/self_declared_location/verified/verified_type/account_entity_type/
    # platform_native_type/account_created_at/followers_count/following_count/subscriber_count/
    # member_count/post_count/view_count/recent_post_sample/other
    source_field: Optional[str] = None
    metadata_snapshot: Optional[dict] = None


class AccountQualityControl(CamelModel):
    need_human_review: bool = False
    review_reasons: list[str] = []
    failed_modules: list[str] = []


class AnnotateAccountResponse(CamelModel):
    schema_version: str = SCHEMA_VERSION
    account_reference: Optional[AccountReference] = None
    account_type: AccountType = AccountType()
    evidence_clues: list[AccountEvidenceClue] = []
    quality_control: AccountQualityControl = AccountQualityControl()
    overall_confidence: Optional[float] = None
    processed_at: Optional[str] = None
