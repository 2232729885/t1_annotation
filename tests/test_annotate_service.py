"""
针对 annotate_service._build_user_content 的测试：确认有图片时真的构造出
OpenAI 多模态格式的 content 数组（image_url），不是只在文字里描述URL。
"""
from app.schemas.annotate import AnnotateRequest, Context, MediaItem
from app.services.annotate_service import _build_user_content


def test_no_media_returns_plain_string():
    request = AnnotateRequest(text="just some text", context=Context())
    content = _build_user_content(request)
    assert isinstance(content, str)
    assert "just some text" in content


def test_image_media_returns_multimodal_content_array():
    request = AnnotateRequest(
        text="check this image out",
        medias=[MediaItem(id="m1", url="https://example.com/a.jpg", media_type="image")],
        context=Context(),
    )
    content = _build_user_content(request)
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert "check this image out" in content[0]["text"]
    image_parts = [c for c in content if c["type"] == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"] == "https://example.com/a.jpg"


def test_video_only_media_stays_plain_string_not_sent_as_visual_content():
    """
    视频目前不直接作为视觉内容传给模型（vLLM/Qwen3-VL对视频输入的支持不如图片稳定），
    只在文字里描述URL，所以只有视频、没有图片时，content 应该还是纯字符串。
    """
    request = AnnotateRequest(
        text="check this video out",
        medias=[MediaItem(id="m1", url="https://example.com/a.mp4", media_type="video")],
        context=Context(),
    )
    content = _build_user_content(request)
    assert isinstance(content, str)
    assert "https://example.com/a.mp4" in content


def test_mixed_image_and_video_only_image_becomes_visual_content():
    request = AnnotateRequest(
        text="mixed media post",
        medias=[
            MediaItem(id="m1", url="https://example.com/a.jpg", media_type="image"),
            MediaItem(id="m2", url="https://example.com/a.mp4", media_type="video"),
        ],
        context=Context(),
    )
    content = _build_user_content(request)
    assert isinstance(content, list)
    image_parts = [c for c in content if c["type"] == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["url"] == "https://example.com/a.jpg"
    # 视频URL应该出现在文字部分里，而不是作为一个视觉内容块
    text_part = next(c for c in content if c["type"] == "text")
    assert "https://example.com/a.mp4" in text_part["text"]
