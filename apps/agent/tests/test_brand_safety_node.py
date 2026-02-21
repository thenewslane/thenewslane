"""
tests/test_brand_safety_node.py — Unit tests for brand safety pipeline.
"""

import pytest
from unittest.mock import Mock, patch
from nodes.brand_safety_filters import KeywordFilter, LlamaGuardFilter, BrandSafetyLLMFilter
from nodes.brand_safety import BrandSafetyNode, check_brand_safety


class TestKeywordFilter:
    """Test cases for KeywordFilter."""

    @patch('nodes.brand_safety_filters.db')
    def test_keyword_filter_blocks_content(self, mock_db):
        """Test that keyword filter blocks content with blocked keywords."""
        mock_db.get_config_value.return_value = ["violence", "inappropriate", "spam"]
        
        filter_instance = KeywordFilter()
        
        # Test blocked content
        is_safe, blocked_keyword = filter_instance.check(
            "Violence in the Streets",
            "Multiple reports of inappropriate behavior"
        )
        
        assert not is_safe
        assert blocked_keyword == "violence"

    @patch('nodes.brand_safety_filters.db')
    def test_keyword_filter_allows_safe_content(self, mock_db):
        """Test that keyword filter allows safe content."""
        mock_db.get_config_value.return_value = ["violence", "inappropriate", "spam"]
        
        filter_instance = KeywordFilter()
        
        # Test safe content
        is_safe, blocked_keyword = filter_instance.check(
            "Technology Innovation",
            "New breakthrough in artificial intelligence research"
        )
        
        assert is_safe
        assert blocked_keyword is None


class TestLlamaGuardFilter:
    """Test cases for LlamaGuardFilter."""

    @patch('nodes.brand_safety_filters.settings')
    @patch('nodes.brand_safety_filters.Groq')
    def test_llama_guard_safe_response(self, mock_groq_class, mock_settings):
        """Test Llama Guard safe response parsing."""
        mock_settings.groq_api_key = "test-key"
        
        # Mock Groq client and response
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "safe"
        mock_client.chat.completions.create.return_value = mock_response
        
        filter_instance = LlamaGuardFilter()
        is_safe, categories = filter_instance.check("Safe topic", "Safe headlines")
        
        assert is_safe
        assert categories == []

    @patch('nodes.brand_safety_filters.settings')
    @patch('nodes.brand_safety_filters.Groq')
    def test_llama_guard_unsafe_response(self, mock_groq_class, mock_settings):
        """Test Llama Guard unsafe response parsing."""
        mock_settings.groq_api_key = "test-key"
        
        # Mock Groq client and response
        mock_client = Mock()
        mock_groq_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "unsafe\nS1,S10"
        mock_client.chat.completions.create.return_value = mock_response
        
        filter_instance = LlamaGuardFilter()
        is_safe, categories = filter_instance.check("Unsafe topic", "Unsafe headlines")
        
        assert not is_safe
        assert "S1: Violent Crimes" in categories
        assert "S10: Hate" in categories


class TestBrandSafetyLLMFilter:
    """Test cases for BrandSafetyLLMFilter."""

    @patch('nodes.brand_safety_filters.settings')
    @patch('nodes.brand_safety_filters.anthropic')
    def test_brand_safety_safe_response(self, mock_anthropic, mock_settings):
        """Test brand safety LLM safe response parsing."""
        mock_settings.anthropic_api_key = "test-key"
        
        # Mock Anthropic client and response
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "SAFE - This is appropriate content for mainstream advertisers."
        mock_client.messages.create.return_value = mock_response
        
        filter_instance = BrandSafetyLLMFilter()
        is_safe, explanation = filter_instance.check("Technology news", "Innovation headlines")
        
        assert is_safe
        assert "SAFE" in explanation

    @patch('nodes.brand_safety_filters.settings')
    @patch('nodes.brand_safety_filters.anthropic')
    def test_brand_safety_unsafe_response(self, mock_anthropic, mock_settings):
        """Test brand safety LLM unsafe response parsing."""
        mock_settings.anthropic_api_key = "test-key"
        
        # Mock Anthropic client and response
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "UNSAFE - This content contains controversial material."
        mock_client.messages.create.return_value = mock_response
        
        filter_instance = BrandSafetyLLMFilter()
        is_safe, explanation = filter_instance.check("Controversial topic", "Sensitive headlines")
        
        assert not is_safe
        assert "UNSAFE" in explanation


class TestBrandSafetyNode:
    """Test cases for BrandSafetyNode integration."""

    @patch('nodes.brand_safety.db')
    @patch('nodes.brand_safety.KeywordFilter')
    @patch('nodes.brand_safety.LlamaGuardFilter')  
    @patch('nodes.brand_safety.BrandSafetyLLMFilter')
    def test_brand_safety_node_integration(self, mock_bs_filter, mock_lg_filter, mock_kw_filter, mock_db):
        """Test the full brand safety pipeline integration."""
        # Mock database
        mock_db.get_config_value.return_value = []
        mock_db.client.table.return_value.insert.return_value.execute.return_value = None
        
        # Mock filter instances
        mock_kw_instance = Mock()
        mock_kw_instance.check.return_value = (True, None)
        mock_kw_filter.return_value = mock_kw_instance
        
        mock_lg_instance = Mock()
        mock_lg_instance.check.return_value = (True, [])
        mock_lg_filter.return_value = mock_lg_instance
        
        mock_bs_instance = Mock()
        mock_bs_instance.check.return_value = (True, "SAFE - Good content")
        mock_bs_filter.return_value = mock_bs_instance
        
        # Create test state
        test_state = {
            "batch_id": "test-batch-123",
            "topics": [
                {
                    "id": "topic-1",
                    "title": "Technology Innovation",
                    "headline_cluster": "New AI breakthrough announced"
                }
            ]
        }
        
        result = check_brand_safety(test_state)
        
        assert "topics" in result
        assert len(result["topics"]) == 1
        assert result["topics"][0]["brand_safe"] is True
        assert result["topics_rejected"] == 0