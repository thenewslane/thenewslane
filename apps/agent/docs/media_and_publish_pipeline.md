# Media Generation and Publication Pipeline

This document describes the final stages of the theNewslane content pipeline: video sourcing, media generation, and publication.

## Overview

The pipeline consists of three interconnected nodes that complete the content creation and distribution process:

1. **Video Sourcing Node** - Finds existing videos from YouTube/Vimeo or flags for AI generation
2. **Media Generation Node** - Creates thumbnails and AI videos using Replicate APIs  
3. **Publish Node** - Publishes content to database and triggers external integrations

## Video Sourcing Node

**Location**: `nodes/video_sourcing_node.py`

### Functionality

Searches for relevant videos for each topic using a two-tier approach:

#### Primary: YouTube Data API v3
- **Query**: Topic title
- **Filters**: 
  - Published within last 48 hours
  - View count > 1,000
  - Duration between 30 seconds and 10 minutes
- **Parsing**: ISO 8601 duration format (PT2M30S → 150 seconds)
- **Results**: video_id, embed_url, channel_name, view_count

#### Fallback: Vimeo API
- Same filtering criteria as YouTube
- Public API search (limited functionality without auth)
- Returns Vimeo embed URLs and metadata

#### Video Type Assignment
Based on search results and viral tier:
- **Found video**: `video_type = "youtube"` or `"vimeo"`
- **No video + Tier 1**: `video_type = "ai_needed"`  
- **No video + Tier 2/3**: `video_type = "none"`

### Usage

```python
from nodes import source_videos

state = {
    "batch_id": "batch_123",
    "topics": [
        {
            "id": "topic_1",
            "title": "Breaking Tech News",
            "viral_tier": 1
        }
    ]
}

result = source_videos(state)
# Returns topics with video sourcing information
```

### Configuration

Required environment variables:
- `YOUTUBE_API_KEY` - YouTube Data API v3 key

## Media Generation Node

**Location**: `nodes/media_generation_node.py`

### Functionality

Generates AI-powered media assets using Replicate APIs:

#### Task 1: Thumbnail Generation
- **Model**: `black-forest-labs/flux-1.1-pro`
- **Input**: `image_prompt` from content generation
- **Specs**: 1344x768 (16:9), JPG format, quality 90
- **Output**: Uploaded to Supabase Storage `thumbnails` bucket

#### Task 2: AI Video Generation (Conditional)
- **Model**: `kling-ai/kling-v1-6` 
- **Trigger**: Only when `video_type = "ai_needed"`
- **Specs**: 5-second duration, two aspect ratios
  - **Landscape**: 16:9 for YouTube/web
  - **Portrait**: 9:16 for Instagram Reels
- **Output**: Uploaded to Supabase Storage `videos` bucket

#### Storage Management
- **Automatic Upload**: Generated media → Supabase Storage
- **Public URLs**: Returns publicly accessible URLs
- **Content Types**: Auto-detected from file extensions
- **Error Handling**: Graceful degradation on storage failures

### Parallel Processing

Both thumbnail and video generation run concurrently with:
- **Concurrency Control**: Max 2 simultaneous generations
- **Async Operations**: Full asyncio support
- **Error Isolation**: Individual task failures don't affect others
- **Progress Tracking**: Per-task success/failure reporting

### Usage

```python
from nodes import generate_media

state = {
    "batch_id": "batch_123", 
    "topics": [
        {
            "id": "topic_1",
            "image_prompt": "Futuristic AI landscape",
            "video_type": "ai_needed"
        }
    ]
}

result = generate_media(state)
# Returns topics with media URLs
```

### Configuration

Required environment variables:
- `REPLICATE_API_KEY` - Replicate API access
- Supabase Storage buckets: `thumbnails`, `videos`

## Publish Node

**Location**: `nodes/publish_node.py`

### Functionality

Completes the publication process through three sequential steps:

#### Step 1: Database Publication
- **Target**: `trending_topics` table
- **Status**: `published`
- **Content**: Complete topic record with all generated content and media
- **Metadata**: Processing pipeline info, error logs, timestamps

#### Step 2: Cache Revalidation 
- **API**: Vercel ISR revalidation endpoint
- **Trigger**: `POST /api/revalidate` with article slug
- **Purpose**: Refresh cached article pages
- **Authentication**: Shared secret validation

#### Step 3: Search Engine Indexing
- **API**: IndexNow submission endpoint  
- **Trigger**: `POST /api/indexnow` with article URL
- **Purpose**: Immediate search engine indexing
- **Protocols**: Supports Bing, Google indexing

### Publication Filtering

Only processes topics that meet criteria:
- ✅ `brand_safe = true` (passed brand safety)
- ✅ `content_generated = true` (has all content)
- ⚠️ `media_generated` (optional - media failures don't block publication)

### Concurrent Processing

- **Parallelization**: Database + external APIs run concurrently
- **Concurrency Control**: Max 3 simultaneous publications
- **Error Isolation**: Database success enables publication even if external APIs fail
- **Detailed Reporting**: Per-topic success/failure tracking

### Usage

```python
from nodes import publish_topics

state = {
    "batch_id": "batch_123",
    "topics": [
        {
            "id": "topic_1",
            "title": "Published Article",
            "slug": "published-article",
            "brand_safe": True,
            "content_generated": True,
            "seo_title": "Article Title",
            "article_250w": "Article content...",
            "thumbnail_url": "https://storage.com/thumb.jpg"
        }
    ]
}

result = publish_topics(state)
# Returns: {"published_topic_ids": [...], "publication_results": [...]}
```

### Configuration

Required settings:
- `REVALIDATE_SECRET` - Shared secret for ISR
- Publication endpoints configured in `settings.py`

## Complete Pipeline Integration

### LangGraph Flow

```python
from langgraph import StateGraph
from nodes import (
    check_brand_safety, classify_topics, generate_content_sync,
    source_videos, generate_media, publish_topics
)

# Build complete pipeline
graph = StateGraph()

# Add all nodes
graph.add_node("brand_safety", check_brand_safety)
graph.add_node("classification", classify_topics)
graph.add_node("content_generation", generate_content_sync)
graph.add_node("video_sourcing", source_videos)
graph.add_node("media_generation", generate_media)
graph.add_node("publication", publish_topics)

# Define linear flow
graph.add_edge("brand_safety", "classification")
graph.add_edge("classification", "content_generation")
graph.add_edge("content_generation", "video_sourcing")
graph.add_edge("video_sourcing", "media_generation")
graph.add_edge("media_generation", "publication")

# Compile and execute
pipeline = graph.compile()
```

### Performance Characteristics

**Video Sourcing:**
- YouTube API: ~1-2s per topic
- Vimeo API: ~2-3s per topic  
- Concurrent processing: ~1s per topic average

**Media Generation:**
- Thumbnail: ~30-60s (Flux generation)
- AI Video: ~120-300s (Kling generation)
- Parallel tasks: Thumbnail + Video run simultaneously

**Publication:**
- Database insert: ~100-500ms
- External APIs: ~1-3s each (parallel)
- Total per topic: ~2-4s

**End-to-End Pipeline:**
- Complete processing: ~5-10 minutes per topic
- Bottleneck: AI video generation for Tier 1 topics
- Optimization: Parallel processing across multiple topics

## Error Handling & Resilience

### Graceful Degradation
- **Video Sourcing**: Falls back through YouTube → Vimeo → AI/None
- **Media Generation**: Thumbnail failures don't block video generation
- **Publication**: External API failures don't prevent database publication

### Error Tracking
- **Detailed Logging**: Per-stage success/failure tracking
- **Error Propagation**: Errors logged but don't halt pipeline
- **Retry Logic**: Single retry for transient failures

### Monitoring Points
- **API Rate Limits**: YouTube, Replicate, external APIs
- **Storage Quotas**: Supabase Storage usage
- **Processing Times**: Track generation durations
- **Success Rates**: Monitor completion percentages per stage

## Testing

### Test Coverage
- **Unit Tests**: 25+ tests covering core logic
- **Integration Tests**: API interaction mocking
- **Error Scenarios**: Failure handling verification
- **Performance Tests**: Concurrent processing validation

### Test Categories
- ✅ Video sourcing logic and API parsing
- ✅ Media generation workflows
- ✅ Publication filtering and database operations
- ✅ Async processing and error handling
- ✅ External API integration patterns

Run tests:
```bash
# Core functionality (works in all environments)
pytest tests/test_video_sourcing.py::TestVideoSourcingCore -v
pytest tests/test_media_generation_core.py::TestMediaGenerationLogic -v  
pytest tests/test_publish_core.py::TestPublicationLogic -v

# Integration tests (requires compatible environment)
pytest tests/test_media_and_publish_integration.py -v
```

## Future Enhancements

### Planned Features
1. **Video Source Preferences**: Prioritize certain channels/creators
2. **Media Quality Options**: Multiple resolution/format variants
3. **A/B Testing**: Generate multiple media variants
4. **Scheduling**: Delayed publication for optimal timing
5. **Analytics Integration**: Track performance metrics

### Performance Optimizations  
1. **Batch APIs**: Use Replicate batch endpoints when available
2. **Caching**: Cache media generation results
3. **CDN Integration**: Direct CDN uploads for faster delivery
4. **Background Processing**: Decouple media generation from main pipeline