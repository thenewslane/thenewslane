"""
tests/test_classification_node.py — Unit tests for topic classification pipeline.
"""

import pytest
from unittest.mock import Mock, patch
from nodes.classification_node import ClassificationNode, classify_topics, TOPIC_CATEGORIES


class TestClassificationNode:
    """Test cases for ClassificationNode."""

    @patch('nodes.classification_node.settings')
    @patch('nodes.classification_node.anthropic')
    def test_classify_single_topic_valid_category(self, mock_anthropic, mock_settings):
        """Test classification with valid category response."""
        mock_settings.anthropic_api_key = "test-key"
        
        # Mock Anthropic client and response
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Technology"
        mock_client.messages.create.return_value = mock_response
        
        classifier = ClassificationNode()
        category = classifier._classify_single_topic("AI Innovation", "New chatbot released")
        
        assert category == "Technology"

    @patch('nodes.classification_node.settings')
    @patch('nodes.classification_node.anthropic')
    def test_classify_single_topic_invalid_category(self, mock_anthropic, mock_settings):
        """Test classification with invalid category response - should default."""
        mock_settings.anthropic_api_key = "test-key"
        
        # Mock Anthropic client and response
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Invalid Category Name"
        mock_client.messages.create.return_value = mock_response
        
        classifier = ClassificationNode()
        category = classifier._classify_single_topic("Random topic", "Some headlines")
        
        assert category == "World News"  # Default fallback

    @patch('nodes.classification_node.settings')
    @patch('nodes.classification_node.anthropic')
    def test_classify_single_topic_fuzzy_match(self, mock_anthropic, mock_settings):
        """Test classification with fuzzy matching."""
        mock_settings.anthropic_api_key = "test-key"
        
        # Mock Anthropic client and response
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Tech"  # Should fuzzy match to "Technology"
        mock_client.messages.create.return_value = mock_response
        
        classifier = ClassificationNode()
        category = classifier._classify_single_topic("AI Innovation", "New chatbot released")
        
        assert category == "Technology"

    @patch('nodes.classification_node.settings')
    @patch('nodes.classification_node.anthropic')
    def test_classify_topics_batch(self, mock_anthropic, mock_settings):
        """Test batch classification of multiple topics."""
        mock_settings.anthropic_api_key = "test-key"
        
        # Mock Anthropic client and response
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client
        
        # Mock multiple responses
        mock_responses = []
        categories = ["Technology", "Sports", "Politics"]
        
        for category in categories:
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = category
            mock_responses.append(mock_response)
        
        mock_client.messages.create.side_effect = mock_responses
        
        topics = [
            {"id": "1", "title": "AI News", "headline_cluster": "Tech headlines"},
            {"id": "2", "title": "Football Game", "headline_cluster": "Sports headlines"},
            {"id": "3", "title": "Election Update", "headline_cluster": "Political headlines"}
        ]
        
        classifier = ClassificationNode()
        classified_topics = classifier.classify_topics_batch(topics)
        
        assert len(classified_topics) == 3
        assert classified_topics[0]["category"] == "Technology"
        assert classified_topics[1]["category"] == "Sports"
        assert classified_topics[2]["category"] == "Politics"

    def test_classify_topics_empty_list(self):
        """Test classification with empty topic list."""
        classifier = ClassificationNode()
        result = classifier.classify_topics_batch([])
        assert result == []

    @patch('nodes.classification_node.settings')
    def test_classify_topics_missing_title(self, mock_settings):
        """Test classification with missing topic title."""
        mock_settings.anthropic_api_key = "test-key"
        
        topics = [
            {"id": "1", "headline_cluster": "Some headlines"}  # No title
        ]
        
        classifier = ClassificationNode()
        result = classifier.classify_topics_batch(topics)
        
        assert len(result) == 1
        assert result[0]["id"] == "1"
        # Should not have category added due to missing title


class TestClassifyTopicsFunction:
    """Test cases for the classify_topics LangGraph node function."""

    def test_classify_topics_empty_state(self):
        """Test classification with empty topics list."""
        state = {
            "batch_id": "test-batch",
            "topics": []
        }
        
        result = classify_topics(state)
        assert result["topics"] == []

    @patch('nodes.classification_node.ClassificationNode')
    def test_classify_topics_success(self, mock_classifier_class):
        """Test successful topic classification."""
        # Mock classifier instance
        mock_classifier = Mock()
        mock_classifier_class.return_value = mock_classifier
        
        input_topics = [
            {"id": "1", "title": "Tech News", "headline_cluster": "AI headlines"}
        ]
        
        output_topics = [
            {"id": "1", "title": "Tech News", "headline_cluster": "AI headlines", "category": "Technology"}
        ]
        
        mock_classifier.classify_topics_batch.return_value = output_topics
        
        state = {
            "batch_id": "test-batch",
            "topics": input_topics
        }
        
        result = classify_topics(state)
        
        assert len(result["topics"]) == 1
        assert result["topics"][0]["category"] == "Technology"

    @patch('nodes.classification_node.ClassificationNode')
    def test_classify_topics_error_handling(self, mock_classifier_class):
        """Test error handling in classification."""
        # Mock classifier to raise exception
        mock_classifier = Mock()
        mock_classifier_class.return_value = mock_classifier
        mock_classifier.classify_topics_batch.side_effect = Exception("API Error")
        
        input_topics = [
            {"id": "1", "title": "Tech News", "headline_cluster": "AI headlines"}
        ]
        
        state = {
            "batch_id": "test-batch",
            "topics": input_topics
        }
        
        result = classify_topics(state)
        
        # Should return original topics on error
        assert result["topics"] == input_topics


def test_topic_categories_constant():
    """Test that TOPIC_CATEGORIES contains expected categories."""
    expected_categories = [
        "Technology",
        "Politics", 
        "Business & Finance",
        "Entertainment",
        "Sports",
        "Science & Health", 
        "World News",
        "Lifestyle",
        "Environment",
        "Education"
    ]
    
    assert TOPIC_CATEGORIES == expected_categories
    assert len(TOPIC_CATEGORIES) == 10