"""
`POST /annotate` 请求/响应 schema，对应 T1_annotation_v0.6 规约。
枚举字段用 str 类型 + 文档字符串列出取值范围，不用 Literal 强校验——
大模型偶尔的轻微用词偏差不应该导致整个请求直接500，交给业务层做兜底判断。
"""
from __future__ import annotations

from typing import Optional

from app.schemas.common import CamelModel

SCHEMA_VERSION = "t1_annotation_v0.6"


# ==================== 请求 ====================


class MediaItem(CamelModel):
    id: str
    url: str
    media_type: str  # image | video


class Context(CamelModel):
    content_id: Optional[str] = None
    platform: Optional[str] = None
    url: Optional[str] = None
    content_type: Optional[str] = None  # post | comment | reply | article
    author_handle: Optional[str] = None
    published_at: Optional[str] = None
    hashtags: list[str] = []
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    repost_count: Optional[int] = None
    view_count: Optional[int] = None
    parent_content_id: Optional[str] = None


class AnnotateRequest(CamelModel):
    title: Optional[str] = None
    text: Optional[str] = None
    language: Optional[str] = None
    medias: list[MediaItem] = []
    context: Optional[Context] = None


# ==================== 响应 ====================


class InputReference(CamelModel):
    content_id: Optional[str] = None
    content_type: Optional[str] = None
    modality_combination: Optional[str] = None
    platform: Optional[str] = None
    url: Optional[str] = None
    author_id: Optional[str] = None
    created_at: Optional[str] = None


class TextAigcDetection(CamelModel):
    text_aigc_label: str = "unclear"
    text_aigc_score: Optional[float] = None
    text_aigc_signal_labels: list[str] = []
    text_aigc_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class ImageAigcDetection(CamelModel):
    image_aigc_label: str = "not_applicable"
    image_aigc_score: Optional[float] = None
    image_aigc_signal_labels: list[str] = []
    image_aigc_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class VideoAigcDetection(CamelModel):
    video_aigc_label: str = "not_applicable"
    video_aigc_score: Optional[float] = None
    video_aigc_signal_labels: list[str] = []
    video_aigc_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class MultimodalAigcDetection(CamelModel):
    multimodal_aigc_label: str = "not_applicable"
    checked_modality_pairs: list[str] = []
    multimodal_signal_labels: list[str] = []
    multimodal_aigc_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class AigcDetection(CamelModel):
    overall_aigc_label: str = "unclear"
    overall_aigc_score: Optional[float] = None
    text_aigc_detection: TextAigcDetection = TextAigcDetection()
    image_aigc_detection: ImageAigcDetection = ImageAigcDetection()
    video_aigc_detection: VideoAigcDetection = VideoAigcDetection()
    multimodal_aigc_detection: MultimodalAigcDetection = MultimodalAigcDetection()
    aigc_detection_confidence: Optional[float] = None


class Ideology(CamelModel):
    ideology_label: str = "unclear"
    ideology_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class StanceTarget(CamelModel):
    target_type: Optional[str] = None
    target_text: Optional[str] = None


class CoreStance(CamelModel):
    stance_target: Optional[StanceTarget] = None
    stance_label: str = "unclear"
    stance_strength: str = "unclear"
    core_stance_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class OpinionEmotion(CamelModel):
    sentiment_polarity: str = "unclear"
    emotion_labels: list[str] = []
    emotion_intensity: str = "unclear"
    opinion_emotion_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class LanguageStyle(CamelModel):
    style_labels: list[str] = []
    language_style_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class ManipulationMethod(CamelModel):
    method_labels: list[str] = []
    manipulation_method_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class RiskLevel(CamelModel):
    risk_label: str = "unclear"
    risk_types: list[str] = []
    risk_level_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class HighValueSubjective(CamelModel):
    ideology: Ideology = Ideology()
    core_stance: CoreStance = CoreStance()
    opinion_emotion: OpinionEmotion = OpinionEmotion()
    language_style: LanguageStyle = LanguageStyle()
    manipulation_method: ManipulationMethod = ManipulationMethod()
    risk_level: RiskLevel = RiskLevel()


class TopicTags(CamelModel):
    primary_domain: str = "unclear"
    topic_tags_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class EntityHint(CamelModel):
    entity_hint_id: str
    text: str
    type_hint: str  # persons/organizations/events/locations/media_contents/social_accounts/narratives/others/unknown
    entity_hint_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class Keyword(CamelModel):
    keyword_text: str
    keyword_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class Summary(CamelModel):
    summary_text: str = ""
    summary_confidence: Optional[float] = None


class EventType(CamelModel):
    event_type_label: str = "not_applicable"
    event_type_confidence: Optional[float] = None
    evidence_ids: list[str] = []


class BasicObjective(CamelModel):
    topic_tags: TopicTags = TopicTags()
    entities_hint: list[EntityHint] = []
    keywords: list[Keyword] = []
    summary: Summary = Summary()
    event_type: EventType = EventType()


class Annotations(CamelModel):
    high_value_subjective: HighValueSubjective = HighValueSubjective()
    basic_objective: BasicObjective = BasicObjective()


class Region(CamelModel):
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None


class TimeRange(CamelModel):
    start: Optional[float] = None
    end: Optional[float] = None


class EvidenceClue(CamelModel):
    evidence_id: str
    evidence_type: str  # text_span | image_region | video_segment | video_frame_region | metadata | model_signal
    source: Optional[str] = None
    evidence_text: Optional[str] = None
    span: Optional[list[int]] = None
    media_id: Optional[str] = None
    region: Optional[Region] = None
    time_range: Optional[TimeRange] = None
    metadata_snapshot: Optional[dict] = None
    model_signal: Optional[dict] = None


class QualityControl(CamelModel):
    need_human_review: bool = False
    review_reasons: list[str] = []
    failed_modules: list[str] = []


class AnnotateResponse(CamelModel):
    schema_version: str = SCHEMA_VERSION
    input_reference: InputReference = InputReference()
    language: Optional[str] = None
    aigc_detection: AigcDetection = AigcDetection()
    annotations: Annotations = Annotations()
    evidence_clues: list[EvidenceClue] = []
    quality_control: QualityControl = QualityControl()
    overall_confidence: Optional[float] = None
    processed_at: Optional[str] = None
