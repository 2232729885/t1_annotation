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


def test_null_list_fields_are_treated_as_empty():
    """
    Java DTO 的 List<X> 字段没有值时，Jackson 序列化出来是显式的 null，不是省略key也不是[]。
    这里模拟真实报错场景：medias 和 context.hashtags 都显式传 null，应该被当成空列表处理，
    不能直接校验失败（这是2026-07-14生产环境真实报过的一个422错误）。
    """
    request = AnnotateRequest.model_validate(
        {
            "title": None,
            "text": "some text",
            "language": "en",
            "medias": None,
            "context": {
                "contentId": "abc123",
                "platform": "reddit",
                "contentType": "comment",
                "hashtags": None,
            },
        }
    )
    assert request.medias == []
    assert request.context.hashtags == []


def test_llm_client_limits_concurrent_requests(monkeypatch):
    """
    2026-07-14生产环境真实事故：并发请求太多、其中又有带图片的多模态请求，
    把vLLM的GPU显存压爆导致整个引擎崩溃（CUDA OOM in _merge_multimodal_embeddings）。
    这里验证 LlmClient 内部的信号量确实把同时真正打给vLLM的请求数限制住了，
    多出来的请求会排队等，不会一股脑全部并发发过去。
    """
    import threading
    import time
    from unittest.mock import MagicMock, patch

    monkeypatch.setenv("LLM_MAX_CONCURRENT_REQUESTS", "2")
    from app.llm_client import LlmClient

    with patch("app.llm_client.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]

        concurrent_count = [0]
        max_concurrent = [0]
        lock = threading.Lock()

        def slow_create(*args, **kwargs):
            with lock:
                concurrent_count[0] += 1
                max_concurrent[0] = max(max_concurrent[0], concurrent_count[0])
            time.sleep(0.1)
            with lock:
                concurrent_count[0] -= 1
            return mock_response

        mock_client.chat.completions.create.side_effect = slow_create

        client = LlmClient()
        threads = [threading.Thread(target=client.call_json, args=("sys", "user")) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert max_concurrent[0] <= 2


def test_422_validation_errors_are_logged_with_detail(caplog):
    """
    FastAPI默认422只把detail塞进响应体，不打印到容器日志。这里验证自定义的
    validation_exception_handler确实把详细的校验错误和原始请求体打进了日志
    （2026-07-14排查T3的422问题时发现两边日志都看不到具体原因，补上这个）。
    """
    import logging

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    with caplog.at_level(logging.ERROR):
        resp = client.post("/annotate", json={"medias": "not-a-list"})

    assert resp.status_code == 422
    assert any("422 Unprocessable Entity" in record.message for record in caplog.records)
    assert any("not-a-list" in record.message for record in caplog.records)
