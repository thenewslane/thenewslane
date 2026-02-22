"""
tests/test_media_and_publish_integration.py — Integration tests for media and publish nodes.

Tests the complete media generation and publication pipeline with mocked external APIs.
"""

import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest

# Mock replicate before importing nodes that use it
with patch.dict('sys.modules', {'replicate': Mock()}):
    from nodes.video_sourcing_node import source_videos, VideoSourcingService
    from nodes.media_generation_node import generate_media, MediaGenerator, StorageManager
    from nodes.publish_node import publish_topics, PublishService


class TestVideoSourcingNode:
    """Test cases for video sourcing functionality."""

    @patch('nodes.video_sourcing_node.settings')
    @patch('nodes.video_sourcing_node.httpx.AsyncClient')
    async def test_youtube_search_success(self, mock_http_client, mock_settings):
        """Test successful YouTube video search."""
        mock_settings.youtube_api_key = "test-key"
        
        # Mock HTTP client responses
        mock_client = AsyncMock()
        mock_http_client.return_value.__aenter__.return_value = mock_client
        
        # Mock YouTube search response
        search_response = Mock()
        search_response.json.return_value = {
            "items": [{"id": {"videoId": "test123"}}]
        }
        
        # Mock YouTube video details response
        details_response = Mock()
        details_response.json.return_value = {
            "items": [{
                "id": "test123",
                "statistics": {"viewCount": "5000"},
                "contentDetails": {"duration": "PT2M30S"},
                "snippet": {
                    "title": "Test Video",
                    "channelTitle": "Test Channel",
                    "publishedAt": "2023-01-01T00:00:00Z"
                }
            }]
        }
        
        mock_client.get.side_effect = [search_response, details_response]
        
        async with VideoSourcingService() as service:
            result = await service.search_youtube("test topic")
            
            assert result is not None
            assert result["video_type"] == "youtube"
            assert result["video_id"] == "test123"
            assert result["channel_name"] == "Test Channel"

    @patch('nodes.video_sourcing_node.settings')
    @patch('nodes.video_sourcing_node.httpx.AsyncClient')
    async def test_youtube_search_no_qualifying_videos(self, mock_http_client, mock_settings):
        """Test YouTube search when no videos meet criteria."""
        mock_settings.youtube_api_key = "test-key"
        
        mock_client = AsyncMock()
        mock_http_client.return_value.__aenter__.return_value = mock_client
        
        # Mock responses with low view count video
        search_response = Mock()
        search_response.json.return_value = {
            "items": [{"id": {"videoId": "test123"}}]
        }
        
        details_response = Mock()
        details_response.json.return_value = {
            "items": [{
                "id": "test123",
                "statistics": {"viewCount": "100"},  # Too low
                "contentDetails": {"duration": "PT2M30S"},
                "snippet": {"title": "Test Video", "channelTitle": "Test Channel"}
            }]
        }
        
        mock_client.get.side_effect = [search_response, details_response]
        
        async with VideoSourcingService() as service:
            result = await service.search_youtube("test topic")
            
            assert result is None

    def test_parse_iso8601_duration(self):
        """Test ISO 8601 duration parsing."""
        service = VideoSourcingService.__new__(VideoSourcingService)
        
        assert service._parse_iso8601_duration("PT2M30S") == 150
        assert service._parse_iso8601_duration("PT1H5M20S") == 3920
        assert service._parse_iso8601_duration("PT45S") == 45
        assert service._parse_iso8601_duration("PT10M") == 600
        assert service._parse_iso8601_duration("Invalid") == 0

    @patch('nodes.video_sourcing_node.asyncio.run')
    def test_source_videos_langraph_function(self, mock_run):
        """Test the LangGraph node function."""
        mock_run.return_value = [
            {"id": "1", "title": "Test", "video_type": "youtube", "video_id": "abc123"}
        ]
        
        state = {
            "batch_id": "test-batch",
            "topics": [{"id": "1", "title": "Test Topic", "viral_tier": 1}]
        }
        
        result = source_videos(state)
        
        assert "topics" in result
        assert len(result["topics"]) == 1
        assert result["topics"][0]["video_type"] == "youtube"


class TestMediaGenerationNode:
    """Test cases for media generation functionality."""

    @patch('nodes.media_generation_node.settings')
    @patch('nodes.media_generation_node.replicate.Client')
    def test_storage_manager_upload(self, mock_replicate, mock_settings):
        """Test file upload to Supabase Storage."""
        mock_settings.replicate_api_key = "test-key"
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write('test image data')
            tmp_path = tmp_file.name
        
        # Mock Supabase client
        mock_storage = Mock()
        mock_storage.from_.return_value.upload.return_value.status_code = 200
        mock_storage.from_.return_value.get_public_url.return_value = "https://example.com/test.jpg"
        
        storage = StorageManager()
        storage.client = Mock()
        storage.client.storage = mock_storage
        
        # Test the upload - run in async context
        async def run_test():
            result = await storage.upload_file(tmp_path, "test-bucket", "test-key.jpg")
            assert result == "https://example.com/test.jpg"
        
        asyncio.run(run_test())
        
        # Clean up
        Path(tmp_path).unlink(missing_ok=True)

    @patch('nodes.media_generation_node.settings')
    @patch('nodes.media_generation_node.replicate.Client')
    async def test_thumbnail_generation_success(self, mock_replicate_client, mock_settings):
        """Test successful thumbnail generation."""
        mock_settings.replicate_api_key = "test-key"
        
        # Mock Replicate client
        mock_client = Mock()
        mock_replicate_client.return_value = mock_client
        
        # Mock prediction
        mock_prediction = Mock()
        mock_prediction.id = "pred_123"
        mock_prediction.status = "succeeded"
        mock_prediction.output = ["https://replicate.com/output.jpg"]
        
        mock_client.predictions.create.return_value = mock_prediction
        mock_client.predictions.get.return_value = mock_prediction
        
        # Mock HTTP client for download
        mock_http = AsyncMock()
        
        # Mock storage upload
        mock_storage = AsyncMock()
        mock_storage.upload_file.return_value = "https://storage.com/thumbnail.jpg"
        
        generator = MediaGenerator.__new__(MediaGenerator)
        generator.replicate_client = mock_client
        generator.storage = mock_storage
        generator.http_client = mock_http
        
        # Mock the download method
        async def mock_download(url, path):
            with open(path, 'w') as f:
                f.write('fake image data')
        generator.download_file = mock_download
        
        topic = {
            "id": "test_topic",
            "image_prompt": "A beautiful sunset landscape"
        }
        
        result = await generator.generate_thumbnail(topic)
        
        assert "thumbnail_url" in result
        assert result["thumbnail_url"] == "https://storage.com/thumbnail.jpg"
        mock_client.predictions.create.assert_called_once()

    @patch('nodes.media_generation_node.settings')
    @patch('nodes.media_generation_node.replicate.Client')
    async def test_ai_video_generation(self, mock_replicate_client, mock_settings):
        """Test AI video generation with multiple aspect ratios."""
        mock_settings.replicate_api_key = "test-key"
        
        # Mock Replicate client
        mock_client = Mock()
        mock_replicate_client.return_value = mock_client
        
        # Mock prediction for video generation
        mock_prediction = Mock()
        mock_prediction.id = "pred_video_123"
        mock_prediction.status = "succeeded"
        mock_prediction.output = ["https://replicate.com/output.mp4"]
        
        mock_client.predictions.create.return_value = mock_prediction
        mock_client.predictions.get.return_value = mock_prediction
        
        # Mock storage upload
        mock_storage = AsyncMock()
        mock_storage.upload_file.side_effect = [
            "https://storage.com/video_landscape.mp4",
            "https://storage.com/video_portrait.mp4"
        ]
        
        generator = MediaGenerator.__new__(MediaGenerator)
        generator.replicate_client = mock_client
        generator.storage = mock_storage
        
        # Mock the download method
        async def mock_download(url, path):
            with open(path, 'w') as f:
                f.write('fake video data')
        generator.download_file = mock_download
        
        topic = {
            "id": "test_topic",
            "image_prompt": "Dynamic city scene"
        }
        
        result = await generator.generate_ai_video(topic)
        
        assert "video_url" in result
        assert "video_url_portrait" in result
        # Should call predictions.create twice (16:9 and 9:16)
        assert mock_client.predictions.create.call_count == 2

    @patch('nodes.media_generation_node.asyncio.run')
    def test_generate_media_langraph_function(self, mock_run):
        """Test the LangGraph node function for media generation."""
        mock_run.return_value = [
            {
                "id": "1", 
                "title": "Test",
                "media_generated": True,
                "thumbnail_url": "https://example.com/thumb.jpg"
            }
        ]
        
        state = {
            "batch_id": "test-batch",
            "topics": [
                {
                    "id": "1", 
                    "title": "Test Topic",
                    "image_prompt": "Test prompt",
                    "video_type": "ai_needed"
                }
            ]
        }
        
        result = generate_media(state)
        
        assert "topics" in result
        assert len(result["topics"]) == 1
        assert result["topics"][0]["media_generated"] is True
        assert "thumbnail_url" in result["topics"][0]


class TestPublishNode:
    """Test cases for publication functionality."""

    def test_prepare_topic_record(self):
        """Test preparation of topic record for database insertion."""
        service = PublishService()
        
        topic = {
            "id": "test_123",
            "title": "Test Article",
            "slug": "test-article",
            "category": "Technology",
            "viral_tier": 1,
            "viral_score": 0.95,
            "seo_title": "Test SEO Title",
            "article_50w": "Test article content...",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "brand_safe": True,
            "content_generated": True
        }
        
        record = service.prepare_topic_record(topic, "batch_123")
        
        assert record["id"] == "test_123"
        assert record["batch_id"] == "batch_123"
        assert record["status"] == "published"
        assert record["title"] == "Test Article"
        assert record["viral_tier"] == 1
        assert record["brand_safe"] is True
        assert "metadata" in record

    @patch('nodes.publish_node.db')
    async def test_database_insertion(self, mock_db):
        """Test successful database insertion."""
        mock_result = Mock()
        mock_result.data = [{"id": "inserted_123", "status": "published"}]
        mock_db.client.table.return_value.insert.return_value.execute.return_value = mock_result
        
        service = PublishService()
        
        topic_record = {
            "id": "test_123",
            "title": "Test Topic",
            "status": "published"
        }
        
        result_id = await service.insert_topic_to_database(topic_record)
        
        assert result_id == "inserted_123"
        mock_db.client.table.assert_called_with("trending_topics")

    @patch('nodes.publish_node.settings')
    @patch('nodes.publish_node.httpx.AsyncClient')
    async def test_revalidation_success(self, mock_http_client, mock_settings):
        """Test successful ISR revalidation."""
        mock_settings.revalidate_secret = "secret_key"
        mock_settings.revalidate_endpoint = "https://example.com/api/revalidate"
        
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_http_client.return_value.__aenter__.return_value = mock_client
        
        service = PublishService()
        service.http_client = mock_client
        
        result = await service.trigger_revalidation("test-slug")
        
        assert result is True
        mock_client.post.assert_called_once()

    @patch('nodes.publish_node.settings')
    @patch('nodes.publish_node.httpx.AsyncClient')
    async def test_indexnow_submission(self, mock_http_client, mock_settings):
        """Test IndexNow URL submission."""
        mock_settings.site_url = "https://example.com"
        mock_settings.indexnow_endpoint = "https://example.com/api/indexnow"
        mock_settings.revalidate_secret = "secret_key"
        
        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 202
        mock_client.post.return_value = mock_response
        mock_http_client.return_value.__aenter__.return_value = mock_client
        
        service = PublishService()
        service.http_client = mock_client
        
        result = await service.submit_to_indexnow("test-slug")
        
        assert result is True
        mock_client.post.assert_called_once()

    @patch('nodes.publish_node.asyncio.run')
    @patch('nodes.publish_node.db')
    def test_publish_topics_langraph_function(self, mock_db, mock_run):
        """Test the LangGraph node function for publishing."""
        mock_run.return_value = [
            {
                "topic_id": "published_123",
                "published": True,
                "database_inserted": True,
                "revalidation_triggered": True,
                "indexnow_submitted": True
            }
        ]
        
        state = {
            "batch_id": "test-batch",
            "topics": [
                {
                    "id": "test_123",
                    "title": "Test Topic",
                    "slug": "test-topic", 
                    "brand_safe": True,
                    "content_generated": True,
                    "seo_title": "Test SEO Title"
                }
            ]
        }
        
        result = publish_topics(state)
        
        assert "published_topic_ids" in result
        assert "publication_results" in result
        assert len(result["published_topic_ids"]) == 1
        assert result["published_topic_ids"][0] == "published_123"


class TestFullPipelineIntegration:
    """Integration tests for the complete media and publish pipeline."""

    @patch('nodes.video_sourcing_node.settings')
    @patch('nodes.video_sourcing_node.httpx.AsyncClient') 
    @patch('nodes.media_generation_node.settings')
    @patch('nodes.media_generation_node.replicate.Client')
    @patch('nodes.publish_node.settings')
    @patch('nodes.publish_node.db')
    @patch('nodes.publish_node.httpx.AsyncClient')
    def test_complete_media_publish_flow(self, 
                                       mock_pub_http, mock_pub_db, mock_pub_settings,
                                       mock_media_replicate, mock_media_settings,
                                       mock_video_http, mock_video_settings):
        """Test the complete flow from video sourcing through publication."""
        
        # Setup mocks for video sourcing
        mock_video_settings.youtube_api_key = "test-key"
        mock_video_client = AsyncMock()
        mock_video_http.return_value.__aenter__.return_value = mock_video_client
        
        # No YouTube results - should set video_type=ai_needed for Tier 1
        search_response = Mock()
        search_response.json.return_value = {"items": []}
        mock_video_client.get.return_value = search_response
        
        # Setup mocks for media generation
        mock_media_settings.replicate_api_key = "test-key"
        mock_replicate_client = Mock()
        mock_media_replicate.return_value = mock_replicate_client
        
        # Setup mocks for publishing
        mock_pub_settings.revalidate_secret = "secret"
        mock_pub_settings.revalidate_endpoint = "https://example.com/api/revalidate"
        mock_pub_settings.indexnow_endpoint = "https://example.com/api/indexnow"
        mock_pub_settings.site_url = "https://example.com"
        
        mock_db_result = Mock()
        mock_db_result.data = [{"id": "published_123"}]
        mock_pub_db.client.table.return_value.insert.return_value.execute.return_value = mock_db_result
        
        # Initial state with Tier 1 topic
        initial_state = {
            "batch_id": "integration_test",
            "topics": [{
                "id": "test_topic_1",
                "title": "Breaking AI News",
                "viral_tier": 1,
                "viral_score": 0.95,
                "category": "Technology",
                "brand_safe": True,
                "content_generated": True,
                "seo_title": "Breaking AI News Title",
                "slug": "breaking-ai-news",
                "image_prompt": "Futuristic AI visualization"
            }]
        }
        
        # Step 1: Video sourcing
        with patch('nodes.video_sourcing_node.asyncio.run') as mock_video_run:
            mock_video_run.return_value = [{
                **initial_state["topics"][0],
                "video_type": "ai_needed",
                "video_id": None,
                "embed_url": None
            }]
            
            video_result = source_videos(initial_state)
        
        # Step 2: Media generation  
        with patch('nodes.media_generation_node.asyncio.run') as mock_media_run:
            mock_media_run.return_value = [{
                **video_result["topics"][0],
                "media_generated": True,
                "thumbnail_url": "https://storage.com/thumbnail.jpg",
                "video_url": "https://storage.com/video.mp4",
                "video_url_portrait": "https://storage.com/video_portrait.mp4"
            }]
            
            media_result = generate_media(video_result)
        
        # Step 3: Publishing
        with patch('nodes.publish_node.asyncio.run') as mock_publish_run:
            mock_publish_run.return_value = [{
                "topic_id": "published_123",
                "published": True,
                "database_inserted": True,
                "revalidation_triggered": True,
                "indexnow_submitted": True
            }]
            
            publish_result = publish_topics(media_result)
        
        # Verify complete pipeline
        assert len(publish_result["published_topic_ids"]) == 1
        assert publish_result["published_topic_ids"][0] == "published_123"
        
        # Verify each stage was called
        mock_video_run.assert_called_once()
        mock_media_run.assert_called_once()  
        mock_publish_run.assert_called_once()

    def test_pipeline_with_partial_failures(self):
        """Test pipeline behavior when some stages fail."""
        # Test topics with mixed completion states
        state = {
            "batch_id": "failure_test",
            "topics": [
                {
                    "id": "complete_topic",
                    "title": "Complete Topic",
                    "brand_safe": True,
                    "content_generated": True,
                    "media_generated": True,
                    "slug": "complete-topic"
                },
                {
                    "id": "incomplete_topic", 
                    "title": "Incomplete Topic",
                    "brand_safe": False,  # Failed brand safety
                    "content_generated": True
                }
            ]
        }
        
        with patch('nodes.publish_node.asyncio.run') as mock_run:
            mock_run.return_value = [{
                "topic_id": "complete_topic", 
                "published": True,
                "database_inserted": True
            }]
            
            result = publish_topics(state)
        
        # Only the complete topic should be published
        assert len(result["published_topic_ids"]) == 1
        assert result["published_topic_ids"][0] == "complete_topic"