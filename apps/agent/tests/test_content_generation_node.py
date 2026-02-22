"""
tests/test_content_generation_node.py — Unit tests for content generation pipeline.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from nodes.content_generation_node import (
    ContentGenerator, 
    ValidationResult, 
    generate_content, 
    generate_content_sync
)


class TestValidation:
    """Test cases for content validation."""

    def test_validate_content_valid(self):
        """Test validation with valid content."""
        generator = ContentGenerator.__new__(ContentGenerator)  # Skip __init__
        
        valid_content = {
            "seo_title": "Short Title",
            "meta_description": "A description under 160 characters that describes the content properly.",
            "summary_16w": " ".join(["word"] * 16),  # Exactly 16 words
            "article_50w": " ".join(["word"] * 50),  # 50 words
            "faq": [
                {"question": "What is this?", "answer": "This is an answer."},
                {"question": "Why important?", "answer": "It matters because reasons."}
            ],
            "facebook_post": " ".join(["word"] * 149) + " ARTICLE_LINK_PLACEHOLDER",
            "instagram_caption": "Short caption #tag1 #tag2 #tag3 #tag4 #tag5",
            "twitter_thread": [
                "First tweet under 280 characters",
                "Second tweet under 280 characters", 
                "Third tweet under 280 characters"
            ],
            "youtube_script": " ".join(["word"] * 400),  # 400 words
            "image_prompt": "Abstract scene description",
            "iab_categories": ["Technology", "News"],
            "slug": "valid-url-slug"
        }
        
        result = generator._validate_content(valid_content)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_content_missing_fields(self):
        """Test validation with missing required fields."""
        generator = ContentGenerator.__new__(ContentGenerator)
        
        incomplete_content = {
            "seo_title": "Title",
            "meta_description": "Description"
            # Missing other required fields
        }
        
        result = generator._validate_content(incomplete_content)
        assert not result.is_valid
        assert "Missing required field: summary_16w" in result.errors
        assert "Missing required field: article_50w" in result.errors

    def test_validate_content_length_violations(self):
        """Test validation with length violations."""
        generator = ContentGenerator.__new__(ContentGenerator)
        
        invalid_content = {
            "seo_title": "This is a very long title that exceeds the 60 character limit and should fail validation",
            "meta_description": "This is an extremely long meta description that definitely exceeds the 160 character limit and should trigger a validation error when processed by the validator. Adding even more text to make sure it's over 160.",
            "summary_16w": " ".join(["word"] * 50),  # Wrong word count (should be 16)
            "article_50w": " ".join(["word"] * 100),  # Wrong word count (should be 50)
            "faq": [{"question": "Q1", "answer": "A1"}],  # Only 1 instead of 2
            "facebook_post": "Short post",  # Missing placeholder, wrong length
            "instagram_caption": "Caption without hashtags",
            "twitter_thread": ["Tweet 1", "Tweet 2"],  # Only 2 instead of 3
            "youtube_script": " ".join(["word"] * 100),  # Too short
            "image_prompt": "Prompt",
            "iab_categories": ["Only one"],  # Need 2-3
            "slug": "Invalid Slug With Spaces"  # Invalid characters
        }
        
        result = generator._validate_content(invalid_content)
        assert not result.is_valid
        
        # Check specific error messages
        error_text = " ".join(result.errors)
        assert "seo_title too long" in error_text
        assert "meta_description too long" in error_text
        assert "summary_16w wrong length" in error_text
        assert "article_50w wrong length" in error_text
        assert "faq must be array of exactly 2" in error_text
        assert "ARTICLE_LINK_PLACEHOLDER" in error_text
        assert "instagram_caption needs 5 hashtags" in error_text
        assert "twitter_thread must be array of exactly 3" in error_text
        assert "youtube_script wrong length" in error_text
        assert "iab_categories must be array of 2-3" in error_text
        assert "slug must be URL-safe" in error_text


class TestContentGenerator:
    """Test cases for ContentGenerator class."""

    @patch('nodes.content_generation_node.settings')
    def test_init_missing_api_key(self, mock_settings):
        """Test initialization fails without API key."""
        mock_settings.anthropic_api_key = ""
        
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            ContentGenerator()

    @patch('nodes.content_generation_node.settings')
    def test_create_generation_prompt_tier1(self, mock_settings):
        """Test prompt creation for Tier 1 viral topic."""
        mock_settings.anthropic_api_key = "test-key"
        generator = ContentGenerator()
        
        topic = {
            "title": "Breaking Tech News",
            "headline_cluster": "Major announcement",
            "category": "Technology",
            "viral_tier": 1,
            "viral_score": 0.95
        }
        
        prompt = generator._create_generation_prompt(topic)
        
        assert "Breaking Tech News" in prompt
        assert "Technology" in prompt
        assert "HIGH URGENCY" in prompt
        assert "Tier 1 viral topic" in prompt
        assert "return only" in prompt.lower()

    @patch('nodes.content_generation_node.settings')
    def test_create_generation_prompt_tier3(self, mock_settings):
        """Test prompt creation for Tier 3 topic."""
        mock_settings.anthropic_api_key = "test-key"
        generator = ContentGenerator()
        
        topic = {
            "title": "Regular News",
            "headline_cluster": "Standard update",
            "category": "World News", 
            "viral_tier": 3,
            "viral_score": 0.3
        }
        
        prompt = generator._create_generation_prompt(topic)
        
        assert "Regular News" in prompt
        assert "MEASURED TONE" in prompt
        assert "Tier 3 topic" in prompt

    @patch('nodes.content_generation_node.settings')
    def test_create_correction_prompt(self, mock_settings):
        """Test correction prompt creation."""
        mock_settings.anthropic_api_key = "test-key"
        generator = ContentGenerator()
        
        topic = {"title": "Test Topic"}
        errors = ["seo_title too long", "missing hashtags"]
        previous_content = {"seo_title": "Too long title"}
        
        prompt = generator._create_correction_prompt(topic, errors, previous_content)
        
        assert "Test Topic" in prompt
        assert "seo_title too long" in prompt
        assert "missing hashtags" in prompt
        assert "Too long title" in prompt
        assert "Return ONLY a corrected valid JSON" in prompt

    @patch('nodes.content_generation_node.settings')
    @patch('nodes.content_generation_node.anthropic')
    async def test_call_claude_for_content_success(self, mock_anthropic, mock_settings):
        """Test successful Claude API call."""
        mock_settings.anthropic_api_key = "test-key"
        
        # Mock async client
        mock_client = AsyncMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client
        
        # Mock response with valid JSON
        valid_json = {
            "seo_title": "Test Title",
            "meta_description": "Test description"
        }
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps(valid_json)
        mock_client.messages.create.return_value = mock_response
        
        generator = ContentGenerator()
        topic = {"title": "Test"}
        
        result = await generator._call_claude_for_content(topic)
        
        assert result == valid_json
        mock_client.messages.create.assert_called_once()

    @patch('nodes.content_generation_node.settings')
    @patch('nodes.content_generation_node.anthropic')
    async def test_call_claude_for_content_invalid_json(self, mock_anthropic, mock_settings):
        """Test Claude API call with invalid JSON response."""
        mock_settings.anthropic_api_key = "test-key"
        
        # Mock async client
        mock_client = AsyncMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client
        
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "This is not valid JSON"
        mock_client.messages.create.return_value = mock_response
        
        generator = ContentGenerator()
        topic = {"title": "Test"}
        
        with pytest.raises(ValueError, match="Invalid JSON response"):
            await generator._call_claude_for_content(topic)

    @patch('nodes.content_generation_node.settings')
    async def test_generate_content_for_topic_success(self, mock_settings):
        """Test successful content generation for a single topic."""
        mock_settings.anthropic_api_key = "test-key"
        
        # Create a mock generator with mocked methods
        generator = ContentGenerator.__new__(ContentGenerator)
        
        # Mock valid content that passes validation
        valid_content = {
            "seo_title": "Valid Title",
            "meta_description": "Valid description under 160 characters",
            "summary_16w": " ".join(["word"] * 16),
            "article_50w": " ".join(["word"] * 50),
            "faq": [
                {"question": "Q1", "answer": "A1"},
                {"question": "Q2", "answer": "A2"}
            ],
            "facebook_post": " ".join(["word"] * 149) + " ARTICLE_LINK_PLACEHOLDER",
            "instagram_caption": "Caption #tag1 #tag2 #tag3 #tag4 #tag5",
            "twitter_thread": ["Tweet 1", "Tweet 2", "Tweet 3"],
            "youtube_script": " ".join(["word"] * 400),
            "image_prompt": "Image description",
            "iab_categories": ["Tech", "News"],
            "slug": "valid-slug"
        }
        
        generator._call_claude_for_content = AsyncMock(return_value=valid_content)
        generator._validate_content = Mock(return_value=ValidationResult(True, []))
        
        topic = {"id": "test-1", "title": "Test Topic"}
        semaphore = asyncio.Semaphore(1)
        
        result = await generator._generate_content_for_topic(topic, semaphore)
        
        assert result["content_generated"] is True
        assert result["seo_title"] == "Valid Title"
        assert result["id"] == "test-1"

    @patch('nodes.content_generation_node.settings')
    async def test_generate_content_for_topic_validation_failure_then_success(self, mock_settings):
        """Test content generation with initial validation failure, then successful retry."""
        mock_settings.anthropic_api_key = "test-key"
        
        generator = ContentGenerator.__new__(ContentGenerator)
        
        # First response fails validation
        invalid_content = {"seo_title": "Too long title that exceeds character limits"}
        valid_content = {"seo_title": "Fixed Title"}
        
        # Mock the API calls
        generator._call_claude_for_content = AsyncMock(return_value=invalid_content)
        generator._call_claude_for_correction = AsyncMock(return_value=valid_content)
        
        # Mock validation results
        def mock_validate(content):
            if content == invalid_content:
                return ValidationResult(False, ["seo_title too long"])
            return ValidationResult(True, [])
        
        generator._validate_content = Mock(side_effect=mock_validate)
        
        topic = {"id": "test-1", "title": "Test Topic"}
        semaphore = asyncio.Semaphore(1)
        
        result = await generator._generate_content_for_topic(topic, semaphore)
        
        assert result["content_generated"] is True
        assert generator._call_claude_for_correction.called

    @patch('nodes.content_generation_node.settings')
    async def test_generate_content_batch_concurrency(self, mock_settings):
        """Test batch processing with concurrency control."""
        mock_settings.anthropic_api_key = "test-key"
        
        generator = ContentGenerator.__new__(ContentGenerator)
        
        # Mock successful generation for all topics
        async def mock_generate_topic(topic, semaphore):
            # Simulate some processing time
            await asyncio.sleep(0.1)
            return {**topic, "content_generated": True}
        
        generator._generate_content_for_topic = mock_generate_topic
        
        topics = [
            {"id": "1", "title": "Topic 1"},
            {"id": "2", "title": "Topic 2"},
            {"id": "3", "title": "Topic 3"}
        ]
        
        results = await generator.generate_content_batch(topics)
        
        assert len(results) == 3
        assert all(r["content_generated"] for r in results)

    @patch('nodes.content_generation_node.settings')
    async def test_generate_content_batch_exception_handling(self, mock_settings):
        """Test batch processing handles exceptions gracefully."""
        mock_settings.anthropic_api_key = "test-key"
        
        generator = ContentGenerator.__new__(ContentGenerator)
        
        # Mock function that raises exception for second topic
        async def mock_generate_topic(topic, semaphore):
            if topic["id"] == "2":
                raise Exception("Test exception")
            return {**topic, "content_generated": True}
        
        generator._generate_content_for_topic = mock_generate_topic
        
        topics = [
            {"id": "1", "title": "Topic 1"},
            {"id": "2", "title": "Topic 2"},
            {"id": "3", "title": "Topic 3"}
        ]
        
        results = await generator.generate_content_batch(topics)
        
        assert len(results) == 3
        assert results[0]["content_generated"] is True
        assert results[1]["content_generated"] is False
        assert "Test exception" in results[1]["generation_errors"]
        assert results[2]["content_generated"] is True


class TestLangGraphFunctions:
    """Test cases for LangGraph node functions."""

    @patch('nodes.content_generation_node.ContentGenerator')
    async def test_generate_content_success(self, mock_generator_class):
        """Test successful content generation node function."""
        # Mock generator instance
        mock_generator = AsyncMock()
        mock_generator_class.return_value = mock_generator
        
        input_topics = [{"id": "1", "title": "Test Topic"}]
        output_topics = [{"id": "1", "title": "Test Topic", "content_generated": True}]
        
        mock_generator.generate_content_batch.return_value = output_topics
        
        state = {
            "batch_id": "test-batch",
            "topics": input_topics
        }
        
        result = await generate_content(state)
        
        assert len(result["topics"]) == 1
        assert result["topics"][0]["content_generated"] is True

    async def test_generate_content_empty_topics(self):
        """Test content generation with empty topics list."""
        state = {
            "batch_id": "test-batch",
            "topics": []
        }
        
        result = await generate_content(state)
        assert result["topics"] == []

    @patch('nodes.content_generation_node.ContentGenerator')
    async def test_generate_content_exception_handling(self, mock_generator_class):
        """Test content generation handles exceptions."""
        # Mock generator to raise exception
        mock_generator_class.side_effect = Exception("Test error")
        
        topics = [{"id": "1", "title": "Test Topic"}]
        state = {
            "batch_id": "test-batch",
            "topics": topics
        }
        
        result = await generate_content(state)
        
        assert len(result["topics"]) == 1
        assert result["topics"][0]["content_generated"] is False
        assert "Test error" in result["topics"][0]["generation_errors"]

    @patch('nodes.content_generation_node.asyncio.run')
    def test_generate_content_sync(self, mock_run):
        """Test synchronous wrapper function."""
        mock_run.return_value = {"topics": []}
        
        state = {"batch_id": "test", "topics": []}
        result = generate_content_sync(state)
        
        mock_run.assert_called_once()
        assert result == {"topics": []}


def test_validation_result_dataclass():
    """Test ValidationResult dataclass."""
    result = ValidationResult(is_valid=False, errors=["Error 1", "Error 2"])
    
    assert result.is_valid is False
    assert len(result.errors) == 2
    assert "Error 1" in result.errors