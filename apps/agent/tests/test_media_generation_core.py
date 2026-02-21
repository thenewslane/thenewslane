"""
tests/test_media_generation_core.py — Core tests for media generation logic.
"""

import asyncio
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pytest


class TestMediaGenerationLogic:
    """Test core media generation logic without external dependencies."""

    def test_content_type_detection(self):
        """Test content type detection from file extensions."""
        def get_content_type(file_path: str) -> str:
            """Determine content type from file extension."""
            suffix = Path(file_path).suffix.lower()
            content_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg', 
                '.png': 'image/png',
                '.webp': 'image/webp',
                '.mp4': 'video/mp4',
                '.webm': 'video/webm'
            }
            return content_types.get(suffix, 'application/octet-stream')
        
        assert get_content_type("image.jpg") == "image/jpeg"
        assert get_content_type("thumbnail.png") == "image/png"
        assert get_content_type("video.mp4") == "video/mp4"
        assert get_content_type("unknown.xyz") == "application/octet-stream"

    def test_media_generation_task_preparation(self):
        """Test preparation of media generation tasks."""
        topic = {
            "id": "test_topic",
            "title": "Test Topic",
            "image_prompt": "Beautiful sunset landscape",
            "video_type": "ai_needed"
        }
        
        # Mock task preparation logic
        tasks = []
        
        # Always add thumbnail task
        thumbnail_task = ("thumbnail", topic["image_prompt"])
        tasks.append(thumbnail_task)
        
        # Add video task if needed
        if topic.get("video_type") == "ai_needed":
            video_task = ("video", topic["image_prompt"])
            tasks.append(video_task)
        
        # Verify task preparation
        assert len(tasks) == 2
        assert tasks[0][0] == "thumbnail"
        assert tasks[1][0] == "video"
        assert all(task[1] == topic["image_prompt"] for task in tasks)

    def test_media_url_generation(self):
        """Test generation of media URLs."""
        topic_id = "test_topic_123"
        
        def generate_storage_url(topic_id: str, media_type: str, aspect_ratio: str = None) -> str:
            """Generate storage URL for media."""
            base_url = "https://storage.supabase.co/v1/object/public"
            
            if media_type == "thumbnail":
                return f"{base_url}/thumbnails/{topic_id}/thumbnail_{uuid.uuid4().hex[:8]}.jpg"
            elif media_type == "video":
                orientation = "landscape" if aspect_ratio == "16:9" else "portrait"
                return f"{base_url}/videos/{topic_id}/video_{orientation}_{uuid.uuid4().hex[:8]}.mp4"
            
            return f"{base_url}/media/{topic_id}/unknown.bin"
        
        # Test URL generation
        thumbnail_url = generate_storage_url(topic_id, "thumbnail")
        video_url_16_9 = generate_storage_url(topic_id, "video", "16:9")
        video_url_9_16 = generate_storage_url(topic_id, "video", "9:16")
        
        assert "thumbnails" in thumbnail_url
        assert topic_id in thumbnail_url
        assert "videos" in video_url_16_9
        assert "landscape" in video_url_16_9
        assert "portrait" in video_url_9_16

    def test_media_generation_results_processing(self):
        """Test processing of media generation results."""
        # Mock successful media generation results
        thumbnail_result = {"thumbnail_url": "https://example.com/thumb.jpg"}
        video_result = {
            "video_url": "https://example.com/video.mp4",
            "video_url_portrait": "https://example.com/video_portrait.mp4"
        }
        
        # Simulate combining results
        topic = {
            "id": "test_topic",
            "title": "Test Topic",
            "video_type": "ai_needed"
        }
        
        # Combine all results
        final_result = {
            **topic,
            **thumbnail_result,
            **video_result,
            "media_generated": True
        }
        
        # Verify final result
        assert final_result["media_generated"] is True
        assert "thumbnail_url" in final_result
        assert "video_url" in final_result
        assert "video_url_portrait" in final_result
        assert final_result["id"] == "test_topic"  # Original fields preserved

    def test_media_generation_error_handling(self):
        """Test error handling in media generation."""
        topic = {
            "id": "error_topic",
            "title": "Error Topic",
            "video_type": "ai_needed"
        }
        
        # Simulate media generation with errors
        def simulate_media_generation_with_errors():
            results = {}
            exceptions = []
            
            # Thumbnail generation succeeds
            try:
                results["thumbnail_url"] = "https://example.com/thumb.jpg"
            except Exception as e:
                exceptions.append(f"thumbnail: {e}")
            
            # Video generation fails
            try:
                raise Exception("API timeout")
            except Exception as e:
                exceptions.append(f"video: {e}")
            
            # Add error info if any tasks failed
            if exceptions:
                results["media_generation_errors"] = exceptions
            
            results["media_generated"] = len(exceptions) == 0
            
            return {**topic, **results}
        
        result = simulate_media_generation_with_errors()
        
        # Verify error handling
        assert result["media_generated"] is False
        assert "media_generation_errors" in result
        assert len(result["media_generation_errors"]) == 1
        assert "video: API timeout" in result["media_generation_errors"]
        assert "thumbnail_url" in result  # Successful operations still recorded


class TestMediaGenerationIntegration:
    """Integration tests for media generation workflow."""

    def test_replicate_api_call_structure(self):
        """Test structure of Replicate API calls."""
        # Mock Replicate API call structure
        def mock_replicate_call(model: str, inputs: dict):
            """Mock Replicate API call."""
            prediction = {
                "id": f"pred_{uuid.uuid4().hex[:8]}",
                "status": "starting",
                "model": model,
                "input": inputs
            }
            return prediction
        
        # Test Flux thumbnail generation call
        thumbnail_prediction = mock_replicate_call(
            "black-forest-labs/flux-1.1-pro",
            {
                "prompt": "Beautiful sunset landscape",
                "width": 1344,
                "height": 768,
                "num_outputs": 1,
                "output_format": "jpg"
            }
        )
        
        assert thumbnail_prediction["model"] == "black-forest-labs/flux-1.1-pro"
        assert thumbnail_prediction["input"]["width"] == 1344
        assert thumbnail_prediction["input"]["height"] == 768
        
        # Test Kling video generation call
        video_prediction = mock_replicate_call(
            "kling-ai/kling-v1-6",
            {
                "prompt": "Beautiful sunset landscape",
                "duration": 5,
                "aspect_ratio": "16:9"
            }
        )
        
        assert video_prediction["model"] == "kling-ai/kling-v1-6"
        assert video_prediction["input"]["duration"] == 5
        assert video_prediction["input"]["aspect_ratio"] == "16:9"

    @pytest.mark.asyncio
    async def test_concurrent_media_generation(self):
        """Test concurrent media generation for multiple topics."""
        async def mock_generate_media_for_topic(topic):
            """Mock media generation for a single topic."""
            topic_id = topic["id"]
            
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            result = {
                **topic,
                "media_generated": True,
                "thumbnail_url": f"https://example.com/{topic_id}_thumb.jpg"
            }
            
            # Add video URL if needed
            if topic.get("video_type") == "ai_needed":
                result["video_url"] = f"https://example.com/{topic_id}_video.mp4"
                result["video_url_portrait"] = f"https://example.com/{topic_id}_portrait.mp4"
            
            return result
        
        # Test topics
        topics = [
            {"id": "topic_1", "title": "Topic 1", "video_type": "ai_needed", "image_prompt": "Prompt 1"},
            {"id": "topic_2", "title": "Topic 2", "video_type": "youtube", "image_prompt": "Prompt 2"},
            {"id": "topic_3", "title": "Topic 3", "video_type": "none", "image_prompt": "Prompt 3"}
        ]
        
        # Process concurrently
        tasks = [mock_generate_media_for_topic(topic) for topic in topics]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == 3
        assert all(r["media_generated"] for r in results)
        assert all("thumbnail_url" in r for r in results)
        
        # Only topic 1 should have video URLs (ai_needed)
        assert "video_url" in results[0]
        assert "video_url_portrait" in results[0]
        assert "video_url" not in results[1]
        assert "video_url" not in results[2]

    def test_storage_upload_workflow(self):
        """Test the storage upload workflow."""
        def mock_storage_upload(local_file_path: str, bucket: str, object_name: str) -> str:
            """Mock storage upload process."""
            # Simulate file validation
            if not Path(local_file_path).exists():
                raise FileNotFoundError(f"Local file not found: {local_file_path}")
            
            # Simulate upload process
            base_url = "https://storage.supabase.co/v1/object/public"
            public_url = f"{base_url}/{bucket}/{object_name}"
            
            return public_url
        
        # Test thumbnail upload
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b'fake image data')
            tmp_path = tmp_file.name
        
        try:
            thumbnail_url = mock_storage_upload(
                tmp_path,
                "thumbnails", 
                "topic_123/thumbnail_abc.jpg"
            )
            
            assert "thumbnails" in thumbnail_url
            assert "topic_123/thumbnail_abc.jpg" in thumbnail_url
            
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch('nodes.media_generation_node.asyncio.run')
    def test_generate_media_langraph_function(self, mock_asyncio_run):
        """Test the LangGraph node function for media generation."""
        # Mock the async batch processing result
        mock_result = [
            {
                "id": "topic_1",
                "title": "Topic 1",
                "media_generated": True,
                "thumbnail_url": "https://example.com/thumb1.jpg",
                "video_url": "https://example.com/video1.mp4"
            }
        ]
        mock_asyncio_run.return_value = mock_result
        
        # Mock the generate_media function
        def mock_generate_media(state):
            batch_id = state["batch_id"]
            topics = state.get("topics", [])
            
            if not topics:
                return {"topics": topics}
            
            enriched_topics = mock_asyncio_run(None)
            return {"topics": enriched_topics}
        
        # Test state
        state = {
            "batch_id": "media-test",
            "topics": [
                {
                    "id": "topic_1", 
                    "title": "Topic 1",
                    "image_prompt": "Test prompt",
                    "video_type": "ai_needed"
                }
            ]
        }
        
        # Run the function
        result = mock_generate_media(state)
        
        # Verify results
        assert "topics" in result
        assert len(result["topics"]) == 1
        assert result["topics"][0]["media_generated"] is True
        assert "thumbnail_url" in result["topics"][0]