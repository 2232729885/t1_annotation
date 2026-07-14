"""
POST /annotate 的业务逻辑：拼用户提示词 -> 调大模型 -> 解析成 AnnotateResponse。
"""
import datetime
import logging

from pydantic import ValidationError

from app.llm_client import LlmCallError, get_llm_client
from app.prompts import ANNOTATE_SYSTEM_PROMPT
from app.schemas.annotate import AnnotateRequest, AnnotateResponse, InputReference, QualityControl

logger = logging.getLogger(__name__)


def _resolve_modality_combination(has_text: bool, has_images: bool, has_videos: bool) -> str:
    if has_text and has_images and has_videos:
        return "text_image_video"
    if has_text and has_images:
        return "text_image"
    if has_text and has_videos:
        return "text_video"
    if has_images and has_videos:
        return "image_video"
    if has_videos:
        return "video"
    if has_images:
        return "image"
    return "text"


def _build_user_prompt(request: AnnotateRequest) -> str:
    parts: list[str] = []
    if request.title:
        parts.append(f"Title: {request.title}")
    if request.text:
        parts.append(f"Text: {request.text}")

    ctx = request.context
    if ctx is not None:
        if ctx.content_type:
            parts.append(f"Content type: {ctx.content_type}")
        if ctx.platform:
            parts.append(f"Platform: {ctx.platform}")
        if ctx.hashtags:
            parts.append(f"Hashtags: {', '.join(ctx.hashtags)}")
        engagement_bits = []
        for label, value in (
            ("likes", ctx.like_count),
            ("comments", ctx.comment_count),
            ("shares", ctx.share_count),
            ("reposts", ctx.repost_count),
            ("views", ctx.view_count),
        ):
            if value is not None:
                engagement_bits.append(f"{label}={value}")
        if engagement_bits:
            parts.append("Engagement: " + ", ".join(engagement_bits))

    if request.medias:
        media_lines = [f"- {m.media_type}: {m.url}" for m in request.medias]
        parts.append("Attached media:\n" + "\n".join(media_lines))
    else:
        parts.append("No media attached (text-only input).")

    return "\n\n".join(parts) if parts else "(empty input)"


def _build_fallback_response(request: AnnotateRequest, has_text: bool, has_images: bool, has_videos: bool) -> AnnotateResponse:
    ctx = request.context
    response = AnnotateResponse()
    response.input_reference = InputReference(
        content_id=ctx.content_id if ctx else None,
        content_type=ctx.content_type if ctx else None,
        modality_combination=_resolve_modality_combination(has_text, has_images, has_videos),
        platform=ctx.platform if ctx else None,
        url=ctx.url if ctx else None,
        author_id=ctx.author_handle if ctx else None,
        created_at=ctx.published_at if ctx else None,
    )
    response.language = request.language
    response.quality_control = QualityControl(
        need_human_review=True,
        review_reasons=["module_failure"],
        failed_modules=[
            "textAigcDetection", "ideology", "coreStance", "opinionEmotion", "languageStyle",
            "manipulationMethod", "riskLevel", "topicTags", "entitiesHint", "keywords",
            "summary", "eventType",
        ],
    )
    response.overall_confidence = 0.0
    response.processed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return response


def annotate(request: AnnotateRequest) -> AnnotateResponse:
    has_text = bool(request.text and request.text.strip())
    has_images = any(m.media_type == "image" for m in request.medias)
    has_videos = any(m.media_type == "video" for m in request.medias)

    try:
        raw = get_llm_client().call_json(ANNOTATE_SYSTEM_PROMPT, _build_user_prompt(request))
        response = AnnotateResponse.model_validate(raw)
    except (LlmCallError, ValidationError) as exc:
        logger.error("annotate failed, falling back: %s", exc)
        return _build_fallback_response(request, has_text, has_images, has_videos)

    # 输入引用信息、语言这些由服务端权威决定，不完全依赖大模型自己回填，覆盖一次确保准确
    ctx = request.context
    response.input_reference.content_id = ctx.content_id if ctx else None
    response.input_reference.content_type = ctx.content_type if ctx else None
    response.input_reference.modality_combination = _resolve_modality_combination(has_text, has_images, has_videos)
    response.input_reference.platform = ctx.platform if ctx else None
    response.input_reference.url = ctx.url if ctx else None
    response.input_reference.author_id = ctx.author_handle if ctx else None
    response.input_reference.created_at = ctx.published_at if ctx else None
    if not response.language:
        response.language = request.language
    if not response.processed_at:
        response.processed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return response
