"""
nodes/media_generation_node.py — Thumbnail and video generation.

Thumbnail priority:
  1. YouTube video thumbnail (free, if topic already has a YouTube embed)
  2. Wikimedia Commons image search (free, CC-licensed)
  3. OpenAI DALL-E 3 in Studio Ghibli style (AI fallback)

Video generation:
  Kling AI via Replicate for ai_needed topics (skipped on Python 3.14).
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

try:
    import replicate
except Exception:
    replicate = None  # type: ignore[assignment]

from config.settings import settings
from utils.logger import get_logger
from utils.supabase_client import db
from utils.video_assembler import create_shorts_package
from utils.voiceover_generator import VoiceoverGenerator

log = get_logger(__name__)

VIDEO_DURATION  = 5
POLL_INTERVAL   = 10
MAX_WAIT_TIME   = 300

USER_AGENT = "theNewslane/1.0 (news aggregator; contact@thenewslane.com)"

# Minimum number of topic key terms that must appear in a Wikipedia result title/snippet.
# Reduces wrong-person/wrong-story thumbnails (e.g. Biden image for a Finland/Sanna Marin story).
MIN_WIKIPEDIA_RELEVANCE_TERMS = 2

# Stopwords to exclude when deriving key terms from topic title (relevance check).
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "about", "with", "by", "from", "as", "into", "through", "during", "after",
})


# ── Supabase Storage helper ────────────────────────────────────────────────────


class StorageManager:
    """Upload files to Supabase Storage and return public URLs."""

    def __init__(self) -> None:
        self.client = db.client

    async def upload_file(self, file_path: str, bucket: str, object_name: str) -> str:
        """Upload local file → Supabase Storage → return public URL."""
        with open(file_path, "rb") as fh:
            file_data = fh.read()

        content_type = self._content_type(file_path)

        try:
            # supabase-py v2: raises StorageException on failure
            self.client.storage.from_(bucket).upload(
                path=object_name,
                file=file_data,
                file_options={"content-type": content_type, "upsert": "true"},
            )
        except Exception as exc:
            # If the error is "already exists" (duplicate), upsert should handle it —
            # but if not, re-raise so callers can fall back.
            raise RuntimeError(f"Supabase upload failed ({bucket}/{object_name}): {exc}") from exc

        # get_public_url returns a plain string in supabase-py v2
        public_url: str = self.client.storage.from_(bucket).get_public_url(object_name)
        log.debug("Uploaded %s → %s/%s", file_path, bucket, object_name)
        return public_url

    @staticmethod
    def _content_type(path: str) -> str:
        return {
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png":  "image/png",
            ".webp": "image/webp",
            ".mp4":  "video/mp4",
            ".webm": "video/webm",
        }.get(Path(path).suffix.lower(), "application/octet-stream")


# ── Media generator ────────────────────────────────────────────────────────────


class MediaGenerator:
    """
    Orchestrates thumbnail and video generation per topic.

    Thumbnail priority
    ------------------
    1. YouTube thumbnail — free, if topic already has a YouTube embed
    2. Wikimedia Commons — free CC-licensed image matching the topic title
    3. OpenAI DALL-E 3  — Ghibli-style AI generation (fallback)
    """

    # Category-specific Ghibli environment hints for DALL-E
    _CATEGORY_HINTS: dict[str, str] = {
        "technology":    "glowing holographic displays and warm lamplight, a cozy futuristic workshop",
        "politics":      "grand parliament hall or government plaza with dramatic golden-hour light",
        "sports":        "vast open stadium at dusk with crowd silhouettes and floodlights",
        "entertainment": "theatrical stage with warm amber spotlights and velvet curtains",
        "health":        "tranquil forest clearing with sunlight through ancient trees, gentle mist",
        "science":       "observatory dome or open-air lab under a star-filled sky",
        "business":      "bustling waterfront market or gleaming city skyline at golden hour",
        "world":         "iconic landmark or sweeping panoramic landscape in soft morning light",
        "environment":   "lush rolling hills, rivers, and forests under dramatic cloud-streaked skies",
        "default":       "sweeping cinematic landscape with rich atmospheric detail and dramatic skies",
    }

    def __init__(self) -> None:
        if replicate is None:
            log.warning("replicate package unavailable — video generation skipped (Python 3.14)")
            self.replicate_client = None
        elif settings.replicate_api_key:
            self.replicate_client = replicate.Client(api_token=settings.replicate_api_key)
        else:
            log.warning("REPLICATE_API_KEY not set — video generation skipped")
            self.replicate_client = None

        self.storage     = StorageManager()
        self.http_client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    async def __aenter__(self) -> "MediaGenerator":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.http_client.aclose()

    # ── Schema-blocks helper ─────────────────────────────────────────────────

    @staticmethod
    def _sb(topic: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely retrieve a value from topic['schema_blocks'][key]."""
        sb = topic.get("schema_blocks") or {}
        if isinstance(sb, list):
            # Defensive: schema_blocks should be a dict, not a list
            sb = sb[0] if sb else {}
        return sb.get(key, default)

    @staticmethod
    def _topic_key_terms(topic: Dict[str, Any]) -> set[str]:
        """
        Extract significant words from topic title and headline_cluster for
        thumbnail relevance checks. Used to avoid wrong-person/wrong-story
        images (e.g. Biden thumbnail for a Finland/Sanna Marin article).
        """
        title = (topic.get("title") or "").strip()
        headlines = (topic.get("headline_cluster") or "").strip()
        text = f"{title} {headlines}".lower()
        # Words: letters/numbers only, len >= 2, not stopwords
        words = set()
        for word in text.replace("-", " ").split():
            w = "".join(c for c in word if c.isalnum())
            if len(w) >= 2 and w not in _STOPWORDS:
                words.add(w)
        return words

    # ── Thumbnail: step 1 — YouTube ──────────────────────────────────────────

    async def _youtube_thumbnail_url(self, topic: Dict[str, Any]) -> Optional[str]:
        """Return the best available YouTube thumbnail URL for the topic."""
        # video_id lives in schema_blocks, not as a top-level field
        video_id   = topic.get("video_id") or self._sb(topic, "video_id")
        video_type = topic.get("video_type", "")
        if not video_id or "youtube" not in str(video_type):
            return None
        # Try maxresdefault → hqdefault
        for quality in ("maxresdefault", "hqdefault"):
            url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
            try:
                r = await self.http_client.head(url, timeout=8.0)
                if r.status_code == 200:
                    log.debug("Using YouTube thumbnail: %s", url)
                    return url
            except Exception:
                pass
        return None

    # ── Thumbnail: step 2 — Wikipedia page thumbnail ─────────────────────────

    async def _wikipedia_thumbnail_url(self, topic: Dict[str, Any]) -> Optional[str]:
        """
        Search Wikipedia for the article title and return its page thumbnail URL.
        Only uses a result if it passes a relevance check: at least
        MIN_WIKIPEDIA_RELEVANCE_TERMS words from the topic must appear in the
        page title/snippet to avoid wrong-person or wrong-story images (e.g.
        Biden thumbnail for a Finland/Sanna Marin article).
        """
        query = (topic.get("title") or "").strip()
        if not query:
            return None

        key_terms = self._topic_key_terms(topic)
        if not key_terms:
            return None

        try:
            resp = await self.http_client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query[:100],
                    "srlimit": 10,
                    "format": "json",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            )
            if resp.status_code != 200:
                return None

            results = resp.json().get("query", {}).get("search", [])
            if not results:
                return None

            # Pick the result that best matches the topic (title + snippet)
            best_score = -1
            best_result: Optional[Dict[str, Any]] = None
            for r in results:
                title = (r.get("title") or "").lower()
                snippet = (r.get("snippet") or "").lower()
                combined = f"{title} {snippet}"
                score = sum(1 for t in key_terms if t in combined)
                if score > best_score:
                    best_score = score
                    best_result = r

            if (
                best_result is None
                or best_score < MIN_WIKIPEDIA_RELEVANCE_TERMS
            ):
                log.info(
                    "Wikipedia relevance check failed for '%s': best score=%d (need >=%d), skipping to avoid wrong image",
                    query[:40], best_score, MIN_WIKIPEDIA_RELEVANCE_TERMS,
                )
                return None

            page_title = best_result["title"].replace(" ", "_")
            resp2 = await self.http_client.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}",
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            )
            if resp2.status_code != 200:
                return None

            thumb = (resp2.json().get("thumbnail") or {}).get("source")
            if not thumb:
                return None

            # Upgrade to a larger resolution
            for small, large in [
                ("/200px-", "/1200px-"), ("/320px-", "/1200px-"),
                ("/400px-", "/1200px-"), ("/640px-", "/1200px-"),
            ]:
                if small in thumb:
                    thumb = thumb.replace(small, large)
                    break

            log.info(
                "Wikipedia thumbnail for '%s' (score=%d): %s",
                query[:40], best_score, thumb[:60],
            )
            return thumb

        except Exception as exc:
            log.debug("Wikipedia search failed for '%s': %s", query, exc)
            return None

    # ── Thumbnail: step 3 — Wikimedia Commons ────────────────────────────────

    async def _wikimedia_image_url(self, topic: Dict[str, Any]) -> Optional[str]:
        """
        Search Wikimedia Commons for a free CC-licensed image.
        Only returns an image if its filename/title contains at least one topic
        key term (relevance check to avoid wrong-person/wrong-story images).
        """
        query = (topic.get("title") or "").strip()
        if not query:
            return None

        key_terms = self._topic_key_terms(topic)

        try:
            resp = await self.http_client.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action":    "query",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrnamespace": "6",          # File namespace
                    "prop":      "imageinfo",
                    "iiprop":    "url|mime|size",
                    "format":    "json",
                    "gsrlimit":  "10",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            )
            if resp.status_code != 200:
                return None

            pages = resp.json().get("query", {}).get("pages", {})
            candidates: list[dict[str, Any]] = []

            for page in pages.values():
                infos = page.get("imageinfo", [])
                if not infos:
                    continue
                info = infos[0]
                mime   = info.get("mime", "")
                width  = int(info.get("width",  0))
                height = int(info.get("height", 0))
                url    = info.get("url", "")
                title  = (page.get("title") or "").lower()

                if mime not in ("image/jpeg", "image/png"):
                    continue
                if width < 900 or height < 400:       # too small
                    continue
                if height > 0 and width / height < 1.2:  # must be landscape-ish
                    continue

                # Relevance: at least one topic key term in filename/title
                if key_terms and not any(t in title for t in key_terms):
                    continue
                candidates.append({"url": url, "width": width, "height": height})

            if not candidates:
                return None

            # Pick the widest image among relevance-filtered candidates
            best = max(candidates, key=lambda c: c["width"])
            log.info("Wikimedia Commons image found: %s", best["url"])
            return best["url"]

        except Exception as exc:
            log.debug("Wikimedia search failed for '%s': %s", query, exc)
            return None

    # ── Thumbnail: step 3 — DALL-E Ghibli ────────────────────────────────────

    def _build_ghibli_prompt(self, topic: Dict[str, Any]) -> str:
        # image_prompt is stored inside schema_blocks
        scene    = (topic.get("image_prompt") or self._sb(topic, "image_prompt") or "").strip()
        title    = (topic.get("title")        or "").strip()
        headlines = (topic.get("headline_cluster") or "").strip()
        category = (topic.get("category")    or "default").strip().lower()

        if not scene:
            context = headlines[:200] if headlines else title
            scene = f"A scene capturing the atmosphere of this news event: {context}"

        hint = self._CATEGORY_HINTS.get(category, self._CATEGORY_HINTS["default"])

        return (
            "Studio Ghibli style illustration, hand-painted animation art by Hayao Miyazaki, "
            "watercolor textures, lush and vivid colour palette, soft diffused natural lighting, "
            "highly detailed painterly backgrounds, dreamlike atmosphere, anime art style. "
            f"Scene inspired by real news: {scene}. "
            f"Environment style: {hint}. "
            "No human faces, no text, no logos, no brand names, no real people. "
            "16:9 cinematic composition."
        )[:4000]

    async def _dalle_thumbnail(self, topic: Dict[str, Any], topic_id: str) -> Optional[str]:
        """Generate a Ghibli-style image via DALL-E 3 and return a Supabase URL."""
        if not getattr(settings, "openai_api_key", None):
            log.warning("OPENAI_API_KEY not configured — skipping DALL-E fallback")
            return None

        prompt = self._build_ghibli_prompt(topic)
        log.info("DALL-E 3 Ghibli fallback for topic %s", topic_id)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model":   "dall-e-3",
                        "prompt":  prompt,
                        "size":    "1792x1024",
                        "quality": "hd",
                        "n":       1,
                    },
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"OpenAI {resp.status_code}: {resp.text[:200]}")

                image_url = resp.json()["data"][0]["url"]
                img_data  = (await client.get(image_url)).content

            tmp = f"/tmp/dalle_{topic_id}.png"
            with open(tmp, "wb") as fh:
                fh.write(img_data)

            url = await self.storage.upload_file(tmp, "thumbnails", f"{topic_id}.png")
            Path(tmp).unlink(missing_ok=True)
            return url

        except Exception as exc:
            log.error("DALL-E generation failed for %s: %s", topic_id, exc)
            return None

    # ── Main thumbnail orchestrator ───────────────────────────────────────────

    async def generate_thumbnail(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve thumbnail via priority chain:
          1. YouTube thumbnail    — free, instant, relevant (uses schema_blocks['video_id'])
          2. Wikipedia            — free, no key, good news coverage
          3. Wikimedia Commons    — free CC image search
          4. DALL-E 3 Ghibli     — AI fallback (only if billing allows)

        Wikipedia and Wikimedia URLs are stored directly (no Supabase re-host needed).
        """
        topic_id = topic.get("id") or f"topic_{uuid.uuid4().hex[:8]}"

        # 1. YouTube — no quota consumed, URL is stable
        yt_url = await self._youtube_thumbnail_url(topic)
        if yt_url:
            return {"thumbnail_url": yt_url}

        # 2. Wikipedia page thumbnail (best for news topics)
        wp_url = await self._wikipedia_thumbnail_url(topic)
        if wp_url:
            return {"thumbnail_url": wp_url}

        # 3. Wikimedia Commons (broader CC image database)
        wm_url = await self._wikimedia_image_url(topic)
        if wm_url:
            return {"thumbnail_url": wm_url}

        # 4. DALL-E 3 Ghibli fallback
        dalle_url = await self._dalle_thumbnail(topic, topic_id)
        return {"thumbnail_url": dalle_url}

    # ── Video generation ──────────────────────────────────────────────────────

    async def generate_ai_video(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        image_prompt = topic.get("image_prompt", "")
        topic_id     = topic.get("id") or f"topic_{uuid.uuid4().hex[:8]}"

        if not image_prompt:
            return {"video_url": None}

        if self.replicate_client is None:
            log.warning("Skipping AI video — Replicate unavailable (Python 3.14)")
            return {"video_url": None}

        log.info("Generating AI video for topic %s", topic_id)
        try:
            landscape = await self._generate_video_aspect("16:9", image_prompt, topic_id, "landscape")
            portrait  = await self._generate_video_aspect("9:16",  image_prompt, topic_id, "portrait")
            return {
                "video_url":          landscape.get("video_url"),
                "video_url_portrait": portrait.get("video_url"),
            }
        except Exception as exc:
            log.error("AI video generation failed for %s: %s", topic_id, exc)
            return {"video_url": None}

    async def _generate_video_aspect(
        self, aspect: str, prompt: str, topic_id: str, orientation: str,
    ) -> Dict[str, Any]:
        pred = self.replicate_client.predictions.create(
            model="kling-ai/kling-v1-6",
            input={"prompt": prompt, "duration": VIDEO_DURATION, "aspect_ratio": aspect},
        )
        pred = await self._poll(pred.id)
        if pred.status != "succeeded":
            raise RuntimeError(f"Kling prediction {pred.id} status: {pred.status}")

        video_url = pred.output[0] if pred.output else None
        if not video_url:
            raise RuntimeError("Kling returned no output URL")

        tmp = f"/tmp/video_{topic_id}_{orientation}.mp4"
        async with self.http_client.stream("GET", video_url) as r:
            r.raise_for_status()
            with open(tmp, "wb") as fh:
                async for chunk in r.aiter_bytes():
                    fh.write(chunk)

        obj = f"{topic_id}/video_{orientation}_{uuid.uuid4().hex[:8]}.mp4"
        public_url = await self.storage.upload_file(tmp, "videos", obj)
        Path(tmp).unlink(missing_ok=True)
        return {"video_url": public_url}

    async def _poll(self, prediction_id: str) -> Any:
        elapsed = 0
        while elapsed < MAX_WAIT_TIME:
            pred = self.replicate_client.predictions.get(prediction_id)
            if pred.status == "succeeded":
                return pred
            if pred.status in ("failed", "canceled", "cancelled"):
                raise RuntimeError(f"Prediction {prediction_id} {pred.status}: {pred.error}")
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
        raise RuntimeError(f"Prediction {prediction_id} timed out after {MAX_WAIT_TIME}s")

    # ── Voiceover + Shorts (Tier 1 only) ─────────────────────────────────────

    async def _generate_shorts_video(
        self,
        topic: Dict[str, Any],
        topic_id: str,
        thumbnail_url: Optional[str],
    ) -> Optional[str]:
        """
        Generate an ElevenLabs voiceover, assemble a 9:16 Shorts MP4,
        upload to Supabase Storage, and return the public URL.

        Returns None on any failure so the caller can continue gracefully.
        """
        script = (topic.get("script") or topic.get("youtube_script") or "").strip()
        if not script:
            log.info("[shorts] No script for topic %s — skipping voiceover", topic_id)
            return None

        try:
            vo_gen = VoiceoverGenerator()
            remaining = vo_gen.check_quota()
            if remaining < 2000:
                log.warning(
                    "[shorts] ElevenLabs quota low (%d chars) — skipping voiceover for %s",
                    remaining, topic_id,
                )
                return None

            vo_path = f"/tmp/vo_{topic_id}.mp3"
            vo_gen.generate(script, vo_path)

            # Download thumbnail locally if it's a remote URL
            local_thumb: Optional[str] = None
            if thumbnail_url:
                try:
                    img_resp = await self.http_client.get(thumbnail_url, timeout=20.0)
                    img_resp.raise_for_status()
                    suffix = ".jpg" if "jpeg" in img_resp.headers.get("content-type", "") else ".png"
                    local_thumb = f"/tmp/thumb_{topic_id}{suffix}"
                    Path(local_thumb).write_bytes(img_resp.content)
                except Exception as exc:
                    log.warning("[shorts] Could not download thumbnail for %s: %s", topic_id, exc)
                    local_thumb = None

            title       = topic.get("title", "")
            source_name = topic.get("source_name") or topic.get("category") or "theNewslane"
            ai_video    = topic.get("video_url")  # landscape AI video from Kling (may be None)

            shorts_path = f"/tmp/shorts_{topic_id}.mp4"
            create_shorts_package(
                thumbnail_path=local_thumb,
                ai_video_path=ai_video,
                voiceover_path=vo_path,
                title=title,
                source_name=str(source_name),
                output_path=shorts_path,
            )

            obj_name = f"{topic_id}/shorts_{uuid.uuid4().hex[:8]}.mp4"
            public_url = await self.storage.upload_file(shorts_path, "videos", obj_name)

            # Clean up temp files
            for p in [vo_path, local_thumb, shorts_path]:
                if p:
                    Path(p).unlink(missing_ok=True)

            log.info("[shorts] Uploaded Shorts video for %s → %s", topic_id, public_url)
            return public_url

        except Exception as exc:
            log.error("[shorts] Shorts generation failed for %s: %s", topic_id, exc)
            return None

    # ── Per-topic orchestrator ────────────────────────────────────────────────

    async def process_topic_media(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        topic_id   = topic.get("id", "unknown")
        video_type = topic.get("video_type", "none")

        log.info("Processing media for topic %s (video_type: %s)", topic_id, video_type)

        tasks: list[tuple[str, Any]] = [("thumbnail", self.generate_thumbnail(topic))]
        if video_type == "ai_needed":
            tasks.append(("video", self.generate_ai_video(topic)))

        results: dict[str, Any] = {}
        errors:  list[str]      = []

        task_names, coros = zip(*tasks)
        done = await asyncio.gather(*coros, return_exceptions=True)

        for name, result in zip(task_names, done):
            if isinstance(result, Exception):
                log.error("Media task '%s' failed for %s: %s", name, topic_id, result)
                errors.append(f"{name}: {result}")
            else:
                results.update(result)

        # Tier 1 only: generate ElevenLabs voiceover + assemble Shorts video
        if topic.get("viral_tier") == 1:
            instagram_url = await self._generate_shorts_video(
                topic, str(topic_id), results.get("thumbnail_url")
            )
            if instagram_url:
                results["instagram_video_url"] = instagram_url

        results["media_generated"] = len(errors) == 0
        if errors:
            results["media_generation_errors"] = errors

        log.info("Media done for %s — thumbnail=%s", topic_id, bool(results.get("thumbnail_url")))
        return {**topic, **results}


# ── Batch entry point ──────────────────────────────────────────────────────────


async def generate_media_batch(topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not topics:
        return []

    log.info("generate_media_batch: %d topics", len(topics))
    async with MediaGenerator() as gen:
        sem = asyncio.Semaphore(2)

        async def _process(t: Dict[str, Any]) -> Dict[str, Any]:
            async with sem:
                return await gen.process_topic_media(t)

        results = await asyncio.gather(*[_process(t) for t in topics], return_exceptions=True)

    processed: list[Dict[str, Any]] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            log.error("Media exception for topic %d: %s", i, r)
            processed.append({**topics[i], "media_generated": False,
                               "media_generation_errors": [str(r)]})
        else:
            processed.append(r)

    ok = sum(1 for t in processed if t.get("media_generated"))
    log.info("generate_media_batch complete: %d/%d succeeded", ok, len(topics))
    return processed


def generate_media(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node — generate thumbnails and AI videos."""
    batch_id = state["batch_id"]
    topics   = state.get("topics", [])

    log.info("generate_media: %d topics  batch_id=%s", len(topics), batch_id)
    if not topics:
        return {"topics": topics}

    try:
        enriched = asyncio.run(generate_media_batch(topics))
        thumbs   = sum(1 for t in enriched if t.get("thumbnail_url"))
        videos   = sum(1 for t in enriched if t.get("video_url"))
        log.info("generate_media: %d thumbnails, %d videos", thumbs, videos)
        return {"topics": enriched}
    except Exception as exc:
        log.error("generate_media failed for batch %s: %s", batch_id, exc)
        return {"topics": [{**t, "media_generated": False} for t in topics]}
