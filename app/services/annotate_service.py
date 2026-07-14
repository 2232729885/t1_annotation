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


def _build_user_content(request: AnnotateRequest):
    """
    返回值可能是纯字符串（没有图片时），也可能是 OpenAI 多模态格式的 content 数组
    （有图片时）——只有 image 类型的媒体会真的作为图片发给模型看，video 目前只在文字里
    描述URL（vLLM/Qwen3-VL 对视频输入的支持不如图片稳定和标准化，暂时不直接传视频内容，
    等确认模型/vLLM版本对视频输入的支持情况后再考虑升级）。

    注意：模型要能看到图片，vLLM 服务本身必须能访问到这个图片URL（通常是MinIO地址），
    如果 vLLM 部署的网络访问不到 MinIO，这里传了图片URL过去模型也看不到，
    请确认内网网络策略允许 vLLM 所在机器访问 MinIO。
    """
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

    image_urls = [m.url for m in request.medias if m.media_type == "image"]
    video_urls = [m.url for m in request.medias if m.media_type == "video"]

    if image_urls:
        parts.append(f"{len(image_urls)} image(s) attached below for you to analyze directly.")
    if video_urls:
        video_lines = "\n".join(f"- {url}" for url in video_urls)
        parts.append(
            "Video attached (URL only, video content itself is not passed to you, "
            "judge based on title/text/context and mark video-specific fields as unclear "
            "if there isn't enough textual signal):\n" + video_lines
        )
    if not request.medias:
        parts.append("No media attached (text-only input).")

    text_content = "\n\n".join(parts) if parts else "(empty input)"

    if not image_urls:
        return text_content

    content: list[dict] = [{"type": "text", "text": text_content}]
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    return content


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
            "summary", "topicType",
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
        raw = get_llm_client().call_json(ANNOTATE_SYSTEM_PROMPT, _build_user_content(request))
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
