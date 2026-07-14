"""
POST /annotate_event_heat 的业务逻辑。
"""
import datetime
import logging

from pydantic import ValidationError

from app.llm_client import LlmCallError, get_llm_client
from app.prompts import ANNOTATE_EVENT_HEAT_SYSTEM_PROMPT
from app.schemas.annotate_event_heat import AnnotateEventHeatRequest, AnnotateEventHeatResponse, EventHeat

logger = logging.getLogger(__name__)


def _build_user_prompt(request: AnnotateEventHeatRequest) -> str:
    lines: list[str] = []

    event = request.event
    if event is not None:
        lines.append(
            f"Event: {event.canonical_name} (type={event.event_type}, "
            f"start={event.occurred_at_start}, end={event.occurred_at_end}, country={event.country})"
        )

    stats = request.aggregate_stats
    if stats is not None:
        lines.append(
            f"Aggregate stats: totalRelatedContentCount={stats.total_related_content_count}, "
            f"totalEngagement={stats.total_engagement}, distinctPlatformCount={stats.distinct_platform_count}, "
            f"earliestContentAt={stats.earliest_content_at}, latestContentAt={stats.latest_content_at}"
        )
    else:
        lines.append("Aggregate stats: none provided.")

    if request.related_entities:
        lines.append(f"Related entities ({len(request.related_entities)} total):")
        for entity in request.related_entities[:30]:
            if entity.entity_type == "media_content":
                lines.append(
                    f"- media_content published_at={entity.published_at} platform={entity.platform} "
                    f"likes={entity.like_count} comments={entity.comment_count} "
                    f"shares={entity.share_count} reposts={entity.repost_count} views={entity.view_count}"
                )
            else:
                lines.append(f"- {entity.entity_type}: {entity.name}")
    else:
        lines.append("No related entities provided.")

    return "\n".join(lines)


def _build_fallback_response() -> AnnotateEventHeatResponse:
    response = AnnotateEventHeatResponse()
    response.event_heat = EventHeat(
        heat_level="unclear",
        heat_score=None,
        heat_signal_types=["insufficient_data"],
        reasoning="Event heat annotation failed or did not return a valid result.",
    )
    response.overall_confidence = 0.0
    response.processed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return response


def annotate_event_heat(request: AnnotateEventHeatRequest) -> AnnotateEventHeatResponse:
    try:
        raw = get_llm_client().call_json(ANNOTATE_EVENT_HEAT_SYSTEM_PROMPT, _build_user_prompt(request))
        response = AnnotateEventHeatResponse.model_validate(raw)
    except (LlmCallError, ValidationError) as exc:
        logger.error("annotate_event_heat failed, falling back: %s", exc)
        return _build_fallback_response()

    if not response.processed_at:
        response.processed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return response
