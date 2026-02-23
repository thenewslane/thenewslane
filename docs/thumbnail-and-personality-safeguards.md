# Thumbnail and personality image safeguards

This document describes the cross-checks in place to reduce wrong-person and wrong-story images (e.g. showing Joe Biden for an article about Finland’s PM Sanna Marin).

## Problem

Thumbnails are chosen from, in order:

1. **YouTube** — from the video already selected for the topic (video_id).
2. **Wikipedia** — first search result for the topic title can be wrong (e.g. generic “Election” or an unrelated person).
3. **Wikimedia Commons** — search by topic title; filenames can be unrelated.
4. **DALL-E** — AI-generated from `image_prompt` (no real faces by design).

If Wikipedia or Commons return an unrelated page/image (e.g. Biden for a Finland story), that image was used with no check.

## Cross-checks in place

### 1. Topic key terms (`_topic_key_terms`)

- **Location:** `apps/agent/nodes/media_generation_node.py`
- **What:** Builds a set of significant words from the topic **title** and **headline_cluster** (lowercased, minimal stopwords, length ≥ 2).
- **Use:** All relevance checks use this set so we require the chosen source to actually relate to the topic (e.g. “finland”, “marin”, “election”).

### 2. Wikipedia relevance check

- **Location:** `_wikipedia_thumbnail_url` in `media_generation_node.py`
- **What:**
  - Fetches up to 10 search results (title + snippet).
  - Scores each result by how many topic key terms appear in **title + snippet**.
  - Chooses the **best-scoring** result (not blindly the first).
  - Uses it **only if** that score is at least `MIN_WIKIPEDIA_RELEVANCE_TERMS` (default **2**). Otherwise skips Wikipedia and falls back to Commons/DALL-E.
- **Config:** `MIN_WIKIPEDIA_RELEVANCE_TERMS = 2` at top of `media_generation_node.py`. Increase to be stricter, decrease to allow more Wikipedia thumbnails.

### 3. Wikimedia Commons relevance check

- **Location:** `_wikimedia_image_url` in `media_generation_node.py`
- **What:** For each image, the Commons **page title** (filename) is checked. We only keep candidates where at least **one** topic key term appears in that title. Among those, we still pick the widest image.
- **Effect:** Avoids using a Commons image whose filename has nothing to do with the topic (e.g. “Joe_Biden_speech.jpg” for a Finland article would have 0 matching terms and be skipped).

### 4. YouTube

- **No extra check in media node.** The video (and thus thumbnail) is chosen earlier in the pipeline (video_sourcing_node). If the sourced video is wrong for the topic, the thumbnail will be wrong. Improving that would require relevance checks in the video sourcing step (e.g. match video title/description to topic entities).

### 5. DALL-E fallback

- **Content generation** instructs the model: *“No real people, faces, logos, or brand names”* and to describe a **place or environment**, not a person. So DALL-E thumbnails are scene-based and should not depict a specific person. No extra personality check in the media node.

## How to tighten or relax

- **Stricter:** Increase `MIN_WIKIPEDIA_RELEVANCE_TERMS` (e.g. to 3) so Wikipedia is used only when several topic terms appear in the page.
- **Looser:** Decrease to 1 so any single term match is enough (more Wikipedia thumbnails, slightly higher risk of a bad match).
- **Commons:** The Commons check is “at least 1 term”. You could require 2 by adding a `MIN_COMMONS_RELEVANCE_TERMS` and filtering candidates the same way.

## Fixing an already-published wrong image

For a single article (e.g. Finland PM showing Biden):

1. **Manual fix:** In Supabase, set `thumbnail_url` for that topic to `NULL` or to a correct image URL. Optionally run a one-off script that re-runs only thumbnail selection for that topic (with the new relevance logic) and updates the row.
2. **Backfill:** The `backfill_thumbnails.py` script fills missing thumbnails; it does not yet implement the same relevance scoring. To avoid reintroducing bad images, you could extend it to use the same `_topic_key_terms` + minimum score logic when choosing Wikipedia/Commons.

## Summary

| Source        | Cross-check                                                                 | Config / note                    |
|-------------------------------------------------------------------------------|----------------------------------|
| Wikipedia     | Best result by term overlap; use only if score ≥ 2                          | `MIN_WIKIPEDIA_RELEVANCE_TERMS`  |
| Wikimedia     | Keep only images whose filename contains ≥ 1 topic key term                 | —                                |
| YouTube       | None in media node (relies on video sourcing)                               | Improve in video_sourcing_node   |
| DALL-E        | Prompt forbids real people/faces; scene-only                                | —                                |

These checks reduce the chance of a wrong-person or wrong-story thumbnail; they do not guarantee every image is perfect (e.g. correct person but wrong photo). For high-stakes topics, consider a manual review step or a future image-caption/LLM verification step.
