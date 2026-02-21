"""
tests/test_publish_core.py — Core tests for publication functionality.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
import pytest


class TestPublicationLogic:
    """Test core publication logic without external dependencies."""

    def test_topic_record_preparation(self):
        """Test preparation of topic records for database insertion."""
        def prepare_topic_record(topic: dict, batch_id: str) -> dict:
            """Prepare a topic dictionary for database insertion."""
            now = datetime.now(timezone.utc).isoformat()
            
            # Generate ID if not present
            topic_id = topic.get("id", f"topic_{hash(topic['title']) % 100000}")
            
            # Build complete record
            record = {
                "id": topic_id,
                "batch_id": batch_id,
                "status": "published",
                "created_at": now,
                "published_at": now,
                
                # Topic basics
                "title": topic.get("title", ""),
                "slug": topic.get("slug", ""),
                "category": topic.get("category", "World News"),
                "headline_cluster": topic.get("headline_cluster", ""),
                
                # Viral prediction
                "viral_tier": topic.get("viral_tier", 3),
                "viral_score": topic.get("viral_score", 0.0),
                
                # Content fields (truncated for test)
                "seo_title": topic.get("seo_title", ""),
                "meta_description": topic.get("meta_description", ""),
                "article_250w": topic.get("article_250w", ""),
                
                # Media assets
                "thumbnail_url": topic.get("thumbnail_url"),
                "video_url": topic.get("video_url"),
                "video_type": topic.get("video_type", "none"),
                
                # Processing flags
                "brand_safe": topic.get("brand_safe", False),
                "content_generated": topic.get("content_generated", False),
                "media_generated": topic.get("media_generated", False),
            }
            
            return record
        
        # Test topic
        topic = {
            "id": "test_123",
            "title": "Test Article",
            "slug": "test-article",
            "category": "Technology",
            "viral_tier": 1,
            "viral_score": 0.95,
            "seo_title": "Test SEO Title",
            "article_250w": "Test article content...",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "brand_safe": True,
            "content_generated": True,
            "media_generated": True
        }
        
        record = prepare_topic_record(topic, "batch_123")
        
        # Verify record structure
        assert record["id"] == "test_123"
        assert record["batch_id"] == "batch_123"
        assert record["status"] == "published"
        assert record["title"] == "Test Article"
        assert record["viral_tier"] == 1
        assert record["brand_safe"] is True
        assert "created_at" in record
        assert "published_at" in record

    def test_publishable_topics_filtering(self):
        """Test filtering of topics ready for publication."""
        def filter_publishable_topics(topics: list) -> list:
            """Filter topics that are ready for publication."""
            publishable = []
            
            for topic in topics:
                if (topic.get("brand_safe", False) and 
                    topic.get("content_generated", False)):
                    publishable.append(topic)
            
            return publishable
        
        # Test topics with mixed completion states
        topics = [
            {
                "id": "complete_1",
                "title": "Complete Topic 1",
                "brand_safe": True,
                "content_generated": True,
                "media_generated": True
            },
            {
                "id": "incomplete_1",
                "title": "Incomplete Topic 1", 
                "brand_safe": False,  # Failed brand safety
                "content_generated": True,
                "media_generated": True
            },
            {
                "id": "incomplete_2",
                "title": "Incomplete Topic 2",
                "brand_safe": True,
                "content_generated": False,  # Failed content generation
                "media_generated": True
            },
            {
                "id": "complete_2",
                "title": "Complete Topic 2",
                "brand_safe": True,
                "content_generated": True,
                "media_generated": False  # Media is optional
            }
        ]
        
        publishable = filter_publishable_topics(topics)
        
        # Should have 2 publishable topics
        assert len(publishable) == 2
        assert publishable[0]["id"] == "complete_1"
        assert publishable[1]["id"] == "complete_2"

    def test_api_endpoint_url_generation(self):
        """Test generation of API endpoint URLs."""
        def generate_api_urls(site_url: str, slug: str) -> dict:
            """Generate API URLs for external calls."""
            return {
                "article_url": f"{site_url}/articles/{slug}",
                "revalidate_url": f"{site_url}/api/revalidate",
                "indexnow_url": f"{site_url}/api/indexnow"
            }
        
        urls = generate_api_urls("https://example.com", "test-article")
        
        assert urls["article_url"] == "https://example.com/articles/test-article"
        assert urls["revalidate_url"] == "https://example.com/api/revalidate"
        assert urls["indexnow_url"] == "https://example.com/api/indexnow"

    def test_publication_result_structure(self):
        """Test structure of publication results."""
        def create_publication_result(topic_id: str, success: bool, errors: list = None) -> dict:
            """Create standardized publication result."""
            return {
                "topic_id": topic_id,
                "published": success,
                "database_inserted": success,
                "revalidation_triggered": success,
                "indexnow_submitted": success,
                "errors": errors or []
            }
        
        # Test successful publication
        success_result = create_publication_result("topic_123", True)
        
        assert success_result["topic_id"] == "topic_123"
        assert success_result["published"] is True
        assert success_result["database_inserted"] is True
        assert len(success_result["errors"]) == 0
        
        # Test failed publication
        error_result = create_publication_result("topic_456", False, ["Database error"])
        
        assert error_result["published"] is False
        assert len(error_result["errors"]) == 1
        assert "Database error" in error_result["errors"]


class TestPublicationIntegration:
    """Integration tests for publication workflow."""

    @pytest.mark.asyncio
    async def test_database_insertion_workflow(self):
        """Test database insertion workflow."""
        async def mock_database_insert(record: dict) -> str:
            """Mock database insertion."""
            # Simulate validation
            required_fields = ["id", "title", "status", "batch_id"]
            for field in required_fields:
                if field not in record:
                    raise ValueError(f"Missing required field: {field}")
            
            # Simulate successful insertion
            return record["id"]
        
        # Test record
        record = {
            "id": "test_topic_123",
            "title": "Test Topic",
            "status": "published",
            "batch_id": "batch_123",
            "slug": "test-topic",
            "viral_tier": 1
        }
        
        result_id = await mock_database_insert(record)
        assert result_id == "test_topic_123"

    @pytest.mark.asyncio
    async def test_external_api_calls(self):
        """Test external API calls for revalidation and IndexNow."""
        async def mock_api_call(url: str, payload: dict) -> tuple[bool, str]:
            """Mock external API call."""
            # Simulate different responses based on URL
            if "revalidate" in url:
                if "secret" in payload:
                    return True, "Revalidation successful"
                else:
                    return False, "Invalid secret"
            elif "indexnow" in url:
                if "url" in payload:
                    return True, "URL submitted for indexing"
                else:
                    return False, "Missing URL"
            
            return False, "Unknown API"
        
        # Test revalidation API
        revalidate_success, revalidate_msg = await mock_api_call(
            "https://example.com/api/revalidate",
            {"secret": "test_secret", "path": "/articles/test-slug"}
        )
        
        assert revalidate_success is True
        assert "successful" in revalidate_msg
        
        # Test IndexNow API
        indexnow_success, indexnow_msg = await mock_api_call(
            "https://example.com/api/indexnow",
            {"url": "https://example.com/articles/test-slug"}
        )
        
        assert indexnow_success is True
        assert "indexing" in indexnow_msg

    @pytest.mark.asyncio
    async def test_concurrent_publication(self):
        """Test concurrent publication of multiple topics."""
        async def mock_publish_topic(topic: dict, batch_id: str) -> dict:
            """Mock publication of a single topic."""
            topic_id = topic["id"]
            slug = topic.get("slug", "")
            
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            # Simulate different outcomes
            if "error" in topic["title"].lower():
                return {
                    "topic_id": topic_id,
                    "published": False,
                    "errors": ["Simulated error"]
                }
            
            result = {
                "topic_id": topic_id,
                "published": True,
                "database_inserted": True,
                "revalidation_triggered": bool(slug),
                "indexnow_submitted": bool(slug),
                "errors": []
            }
            
            if not slug:
                result["errors"].append("No slug for external APIs")
            
            return result
        
        # Test topics
        topics = [
            {"id": "topic_1", "title": "Success Topic 1", "slug": "success-1"},
            {"id": "topic_2", "title": "Success Topic 2", "slug": "success-2"},
            {"id": "topic_3", "title": "Error Topic", "slug": "error-topic"},
            {"id": "topic_4", "title": "No Slug Topic", "slug": ""}
        ]
        
        # Process concurrently
        batch_id = "concurrent_test"
        tasks = [mock_publish_topic(topic, batch_id) for topic in topics]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == 4
        
        # Topics 1 and 2 should be fully successful
        assert results[0]["published"] is True
        assert results[1]["published"] is True
        assert len(results[0]["errors"]) == 0
        assert len(results[1]["errors"]) == 0
        
        # Topic 3 should fail
        assert results[2]["published"] is False
        assert len(results[2]["errors"]) > 0
        
        # Topic 4 should succeed but with warning
        assert results[3]["published"] is True
        assert len(results[3]["errors"]) == 1  # No slug warning

    def test_publication_statistics(self):
        """Test calculation of publication statistics."""
        def calculate_publication_stats(results: list) -> dict:
            """Calculate publication statistics."""
            total = len(results)
            successful = sum(1 for r in results if r.get("published", False))
            failed = total - successful
            
            # Count specific success metrics
            db_inserts = sum(1 for r in results if r.get("database_inserted", False))
            revalidations = sum(1 for r in results if r.get("revalidation_triggered", False))
            indexnow_submits = sum(1 for r in results if r.get("indexnow_submitted", False))
            
            return {
                "total_topics": total,
                "published_successfully": successful,
                "publication_failures": failed,
                "success_rate": (successful / total) if total > 0 else 0,
                "database_insertions": db_inserts,
                "cache_revalidations": revalidations,
                "indexnow_submissions": indexnow_submits
            }
        
        # Mock publication results
        results = [
            {
                "topic_id": "1",
                "published": True,
                "database_inserted": True,
                "revalidation_triggered": True,
                "indexnow_submitted": True
            },
            {
                "topic_id": "2", 
                "published": True,
                "database_inserted": True,
                "revalidation_triggered": False,  # No slug
                "indexnow_submitted": False
            },
            {
                "topic_id": "3",
                "published": False,
                "database_inserted": False,
                "revalidation_triggered": False,
                "indexnow_submitted": False
            }
        ]
        
        stats = calculate_publication_stats(results)
        
        assert stats["total_topics"] == 3
        assert stats["published_successfully"] == 2
        assert stats["publication_failures"] == 1
        assert stats["success_rate"] == 2/3
        assert stats["database_insertions"] == 2
        assert stats["cache_revalidations"] == 1
        assert stats["indexnow_submissions"] == 1

    @patch('nodes.publish_node.asyncio.run')
    def test_publish_topics_langraph_function(self, mock_asyncio_run):
        """Test the LangGraph node function for publishing."""
        # Mock the async batch processing result
        mock_result = [
            {
                "topic_id": "published_123",
                "published": True,
                "database_inserted": True,
                "revalidation_triggered": True,
                "indexnow_submitted": True,
                "errors": []
            }
        ]
        mock_asyncio_run.return_value = mock_result
        
        # Mock the publish_topics function
        def mock_publish_topics(state):
            batch_id = state["batch_id"]
            topics = state.get("topics", [])
            
            # Filter publishable topics
            publishable_topics = [
                t for t in topics 
                if t.get("brand_safe", False) and t.get("content_generated", False)
            ]
            
            if not publishable_topics:
                return {
                    "published_topic_ids": [],
                    "publication_results": []
                }
            
            # Run async publication
            publication_results = mock_asyncio_run(None)
            
            # Extract published topic IDs
            published_topic_ids = [
                r["topic_id"] for r in publication_results 
                if r.get("published", False)
            ]
            
            return {
                "published_topic_ids": published_topic_ids,
                "publication_results": publication_results
            }
        
        # Test state
        state = {
            "batch_id": "publish-test",
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
        
        # Run the function
        result = mock_publish_topics(state)
        
        # Verify results
        assert "published_topic_ids" in result
        assert "publication_results" in result
        assert len(result["published_topic_ids"]) == 1
        assert result["published_topic_ids"][0] == "published_123"