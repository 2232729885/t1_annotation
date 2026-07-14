"""
基础冒烟测试：只验证 schema 能不能正确解析请求/响应样例，不依赖真实大模型调用。
"""
import json

from app.schemas.annotate import AnnotateRequest, AnnotateResponse
from app.schemas.annotate_account import AnnotateAccountRequest, AnnotateAccountResponse
from app.schemas.annotate_event_heat import AnnotateEventHeatRequest, AnnotateEventHeatResponse


def test_annotate_request_parses_real_sample():
    sample = {
        "title": "Betting on battery storage",
        "text": "CATL will start mass producing sodium-ion batteries next year.",
        "language": "en",
        "medias": [{"id": "media_001", "url": "https://example.com/a.jpg", "mediaType": "image"}],
        "context": {
            "contentId": "abc123",
            "platform": "reddit",
            "url": "https://reddit.com/r/x/abc123",
            "contentType": "post",
            "authorHandle": "some_user",
            "publishedAt": "2026-07-02T03:50:22Z",
            "hashtags": [],
            "likeCount": 93,
            "commentCount": 26,
            "shareCount": 0,
            "repostCount": 0,
            "viewCount": 0,
        },
    }
    request = AnnotateRequest.model_validate(sample)
    assert request.text.startswith("CATL")
    assert request.context.like_count == 93
    assert request.medias[0].media_type == "image"


def test_annotate_response_round_trips_camel_case():
    sample = {
        "schemaVersion": "t1_annotation_v0.6",
        "inputReference": {"contentId": "abc123", "contentType": "post", "modalityCombination": "text_image"},
        "language": "en",
        "aigcDetection": {"overallAigcLabel": "human_generated"},
        "annotations": {
            "highValueSubjective": {
                "coreStance": {
                    "stanceTarget": {"targetType": "organization", "targetText": "CATL"},
                    "stanceLabel": "neutral",
                }
            },
            "basicObjective": {"topicTags": {"primaryDomain": "economy_finance"}},
        },
        "evidenceClues": [],
        "qualityControl": {"needHumanReview": False, "reviewReasons": [], "failedModules": []},
        "overallConfidence": 0.8,
    }
    response = AnnotateResponse.model_validate(sample)
    assert response.annotations.high_value_subjective.core_stance.stance_target.target_text == "CATL"
    dumped = json.loads(response.model_dump_json(by_alias=True))
    assert dumped["annotations"]["highValueSubjective"]["coreStance"]["stanceTarget"]["targetText"] == "CATL"


def test_annotate_account_request_and_response():
    request = AnnotateAccountRequest.model_validate(
        {
            "platform": "reddit",
            "platformUserId": "ya_boi_greenbean",
            "accountEntityType": "user",
            "handle": "ya_boi_greenbean",
            "displayName": "silly greatness",
            "bio": "",
            "verified": False,
            "recentPostSamples": [],
        }
    )
    assert request.platform_user_id == "ya_boi_greenbean"

    response = AnnotateAccountResponse.model_validate(
        {
            "schemaVersion": "t1_annotation_v0.6",
            "accountType": {
                "primaryAccountCategory": {"categoryLabel": "ordinary_user", "evidenceIds": []},
                "accountSubtypeTags": [],
                "automationSuspicion": {"suspicionLevel": "low", "evidenceIds": []},
            },
            "evidenceClues": [],
            "qualityControl": {"needHumanReview": False, "reviewReasons": [], "failedModules": []},
            "overallConfidence": 0.6,
        }
    )
    assert response.account_type.primary_account_category.category_label == "ordinary_user"


def test_annotate_event_heat_no_related_content():
    request = AnnotateEventHeatRequest.model_validate(
        {
            "event": {"eventId": "evt-1", "canonicalName": "Some Event"},
            "relatedEntities": [],
            "aggregateStats": {"totalRelatedContentCount": 0},
        }
    )
    assert request.aggregate_stats.total_related_content_count == 0

    response = AnnotateEventHeatResponse.model_validate(
        {
            "schemaVersion": "t1_annotation_v0.6",
            "eventHeat": {"heatLevel": "unclear", "heatScore": None, "heatSignalTypes": ["insufficient_data"]},
            "overallConfidence": 0.2,
        }
    )
    assert response.event_heat.heat_level == "unclear"
