"""
utils/image_selection.py — Image selection strategy by content type.

Decides which image intents to try and in what order, without changing
source logic (YouTube, Unsplash, Pexels, Wikimedia, Wikipedia, Together, default logo).

Strategies:
  1. Personality-driven news: personality image (copyright-free) → topic-related; avoid unsafe.
  2. Product news: OEM site image → product from copyright-free sources → similar image → OEM logo.
  3. Nature, monuments, events, other: combine above + existing source order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ImageIntent(str, Enum):
    """What kind of image we are looking for in this step."""
    YOUTUBE = "youtube"           # Use video thumbnail (source-only; no query)
    PERSONALITY = "personality"  # Copyright-free image of the person
    TOPIC_RELATED = "topic_related"
    PRODUCT_OEM = "product_oem"  # Product image from OEM site (stub)
    PRODUCT_FREE = "product_free"  # Product image from copyright-free sources
    SIMILAR = "similar"         # Similar/generic topic image
    OEM_LOGO = "oem_logo"       # Brand/OEM logo
    GENERAL = "general"          # Single generic step (topic title/keyword)


@dataclass
class ImageStep:
    """One step in the image selection strategy."""
    intent: ImageIntent
    search_query: str
    require_safe: bool = True


def _normalize_category(category: Any) -> str:
    if not category:
        return ""
    return (category if isinstance(category, str) else str(category)).strip().lower()


# Categories that often feature personalities (celebrities, politicians, leaders).
_PERSONALITY_CATEGORIES = frozenset({
    "entertainment", "politics", "world news", "lifestyle",
})
# Categories that often feature products (launches, reviews).
_PRODUCT_CATEGORIES = frozenset({
    "technology", "business & finance", "business", "finance",
})
# Nature, monuments, events — can mix personality + product + general.
_NATURE_EVENT_CATEGORIES = frozenset({
    "environment", "science & health", "science", "health",
    "sports", "education", "culture & arts", "culture", "arts",
})

# Verbs that often follow a person's name in headlines.
_PERSON_VERBS = re.compile(
    r"\b(says|announces|reveals|confirms|denies|responds|meets|visits|"
    r"launches|unveils|wins|backs|slams|criticizes|praises|apologizes|"
    r"resigns|elected|appoints|interview|talks|speaks)\b",
    re.I,
)
# Pattern: "Brand Name Product" or "Brand Product" (e.g. Apple iPhone 16).
_KNOWN_BRANDS = re.compile(
    r"\b(apple|google|samsung|microsoft|amazon|meta|tesla|nvidia|intel|"
    r"sony|nike|adidas|ford|gm|volkswagen|bmw|netflix|spotify)\b",
    re.I,
)


def _derive_person_query(topic: Dict[str, Any]) -> Optional[str]:
    """
    Heuristic: derive a person-name query from title/summary for personality image.
    E.g. "Elon Musk announces Tesla deal" -> "Elon Musk".
    """
    title = (topic.get("title") or "").strip()
    if not title:
        return None
    # Look for "Name Verb ..." — take words before the verb.
    match = _PERSON_VERBS.search(title)
    if match:
        before = title[: match.start()].strip()
        # First 2–5 words (likely the person name)
        words = before.split()
        if 1 <= len(words) <= 6:
            return " ".join(words[: min(4, len(words))])
    # Fallback: first 3 words of title (often name in personality news).
    words = title.split()
    if words:
        return " ".join(words[: min(3, len(words))])
    return None


def _derive_product_and_oem(topic: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """
    Heuristic: derive product name and OEM/brand from title.
    Returns (product_query, oem_query). E.g. "Apple iPhone 16 Pro announced" -> ("iPhone 16 Pro", "Apple").
    """
    title = (topic.get("title") or "").strip()
    if not title:
        return None, None
    match = _KNOWN_BRANDS.search(title)
    if match:
        brand = match.group(1).strip()
        # Product: rest of title or brand + following words (e.g. "Apple iPhone 16")
        start = match.end()
        rest = title[start:].strip()
        words = rest.split()
        product_words = [w for w in words if len(w) > 1 and w.isalnum()][:5]
        product = " ".join(product_words) if product_words else brand
        if product and not product.lower().startswith(brand.lower()):
            product = f"{brand} {product}"
        elif not product:
            product = brand
        return product[:80], brand[:60]
    # No known brand: use title as product query, no OEM.
    return title[:80], None


def classify_image_type(topic: Dict[str, Any]) -> str:
    """
    Classify topic into image strategy type.
    Returns one of: "personality_driven", "product", "nature_monument_event", "other".
    """
    category = _normalize_category(topic.get("category"))
    title = (topic.get("title") or "").strip().lower()

    if category in _PERSONALITY_CATEGORIES:
        person_query = _derive_person_query(topic)
        if person_query and len(person_query) > 2:
            return "personality_driven"

    if category in _PRODUCT_CATEGORIES:
        product, oem = _derive_product_and_oem(topic)
        if product or oem:
            return "product"

    if category in _NATURE_EVENT_CATEGORIES:
        return "nature_monument_event"

    if category in _PERSONALITY_CATEGORIES:
        return "personality_driven"

    return "other"


def get_topic_query(topic: Dict[str, Any]) -> str:
    """Default search query from topic (title or keyword)."""
    q = (topic.get("title") or topic.get("keyword") or "").strip()[:100]
    return q or "news"


def get_image_strategy(topic: Dict[str, Any]) -> List[ImageStep]:
    """
    Return ordered list of image steps for this topic.
    Sources (YouTube, Unsplash, Pexels, etc.) are unchanged; each step provides
    the search_query to use when querying those sources. Avoid unsafe images
    (require_safe=True) for personality and general steps.
    """
    image_type = classify_image_type(topic)
    topic_query = get_topic_query(topic)
    steps: List[ImageStep] = []

    if image_type == "personality_driven":
        # 1. Personality image (copyright-free). 2. Topic-related. Avoid unsafe.
        person_q = _derive_person_query(topic)
        if person_q:
            steps.append(ImageStep(ImageIntent.PERSONALITY, person_q, require_safe=True))
        steps.append(ImageStep(ImageIntent.TOPIC_RELATED, topic_query, require_safe=True))

    elif image_type == "product":
        # 1. OEM site (stub). 2. Product from copyright-free. 3. Similar. 4. OEM logo.
        product_q, oem_q = _derive_product_and_oem(topic)
        steps.append(ImageStep(ImageIntent.PRODUCT_OEM, product_q or topic_query, require_safe=True))
        steps.append(ImageStep(ImageIntent.PRODUCT_FREE, product_q or topic_query, require_safe=True))
        steps.append(ImageStep(ImageIntent.SIMILAR, topic_query, require_safe=True))
        if oem_q:
            steps.append(ImageStep(ImageIntent.OEM_LOGO, f"{oem_q} logo", require_safe=True))

    elif image_type == "nature_monument_event":
        # Combine: try personality if applicable, then topic/general.
        person_q = _derive_person_query(topic)
        if person_q:
            steps.append(ImageStep(ImageIntent.PERSONALITY, person_q, require_safe=True))
        product_q, oem_q = _derive_product_and_oem(topic)
        if product_q or oem_q:
            steps.append(ImageStep(ImageIntent.PRODUCT_FREE, product_q or topic_query, require_safe=True))
        steps.append(ImageStep(ImageIntent.TOPIC_RELATED, topic_query, require_safe=True))

    else:
        # other: personality then topic (same as personality_driven but may not have person).
        person_q = _derive_person_query(topic)
        if person_q:
            steps.append(ImageStep(ImageIntent.PERSONALITY, person_q, require_safe=True))
        steps.append(ImageStep(ImageIntent.GENERAL, topic_query, require_safe=True))

    if not steps:
        steps.append(ImageStep(ImageIntent.GENERAL, topic_query, require_safe=True))

    return steps
