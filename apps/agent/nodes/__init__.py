# nodes — LangGraph node functions for each pipeline stage

from .brand_safety import check_brand_safety
from .classification_node import classify_topics
from .content_generation_node import generate_content_sync
from .video_sourcing_node import source_videos

try:
    from .media_generation_node import generate_media
except Exception:
    # media_generation_node requires replicate which may be incompatible
    def generate_media(state):  # type: ignore[misc]
        return {"topics": state.get("topics", [])}

from .publish_node import publish_topics

__all__ = [
    "check_brand_safety",
    "classify_topics",
    "generate_content_sync",
    "source_videos",
    "generate_media",
    "publish_topics",
]
