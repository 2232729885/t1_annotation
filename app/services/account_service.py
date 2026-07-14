"""
POST /annotate_account 的业务逻辑。
"""
import datetime
import logging

from pydantic import ValidationError

from app.llm_client import LlmCallError, get_llm_client
from app.prompts import ANNOTATE_ACCOUNT_SYSTEM_PROMPT
from app.schemas.annotate_account import (
    AccountQualityControl,
    AccountReference,
    AnnotateAccountRequest,
    AnnotateAccountResponse,
)

logger = logging.getLogger(__name__)


def _build_user_prompt(request: AnnotateAccountRequest) -> str:
    lines = [
        f"Platform: {request.platform}",
        f"Account entity type: {request.account_entity_type}",
        f"Handle: {request.handle}",
        f"Display name: {request.display_name}",
        f"Bio: {request.bio or '(empty)'}",
        f"Self-declared location: {request.self_declared_location or '(none)'}",
        f"Verified: {request.verified}, verified type: {request.verified_type}",
        f"Is suspended: {request.is_suspended}",
        f"Account created at: {request.account_created_at}",
        (
            f"Metrics - followers: {request.followers_count}, following: {request.following_count}, "
            f"subscribers: {request.subscriber_count}, members: {request.member_count}, "
            f"posts: {request.post_count}, views: {request.view_count}"
        ),
    ]
    if request.recent_post_samples:
        lines.append("Recent post samples:\n" + "\n".join(f"- {s}" for s in request.recent_post_samples[:10]))
    else:
        lines.append("No recent post samples provided.")
    return "\n".join(lines)


def _build_account_reference(request: AnnotateAccountRequest) -> AccountReference:
    return AccountReference(
        platform=request.platform,
        platform_user_id=request.platform_user_id,
        account_entity_type=request.account_entity_type,
        platform_native_type=request.platform_native_type,
        handle=request.handle,
        display_name=request.display_name,
    )


def _build_fallback_response(request: AnnotateAccountRequest) -> AnnotateAccountResponse:
    response = AnnotateAccountResponse()
    response.account_reference = _build_account_reference(request)
    response.quality_control = AccountQualityControl(
        need_human_review=True,
        review_reasons=["module_failure"],
        failed_modules=["primaryAccountCategory", "accountSubtypeTags", "automationSuspicion"],
    )
    response.overall_confidence = 0.0
    response.processed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return response


def annotate_account(request: AnnotateAccountRequest) -> AnnotateAccountResponse:
    try:
        raw = get_llm_client().call_json(ANNOTATE_ACCOUNT_SYSTEM_PROMPT, _build_user_prompt(request))
        response = AnnotateAccountResponse.model_validate(raw)
    except (LlmCallError, ValidationError) as exc:
        logger.error("annotate_account failed, falling back: %s", exc)
        return _build_fallback_response(request)

    response.account_reference = _build_account_reference(request)
    if not response.processed_at:
        response.processed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return response
