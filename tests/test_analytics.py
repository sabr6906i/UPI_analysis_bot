"""
Unit tests for UPI Analytics System
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.routing.intent_classifier import IntentClassifier, IntentType, QueryRouter
from src.utils.helpers import format_currency, format_number, parse_date_range

class TestIntentClassifier:
    """Test intent classification"""
    
    def setup_method(self):
        """Setup for each test"""
        self.classifier = IntentClassifier()
    
    def test_descriptive_intent(self):
        """Test descriptive query classification"""
        query = "What was the total spending last month?"
        intent, confidence, entities = self.classifier.classify(query)
        assert intent == IntentType.DESCRIPTIVE
        assert confidence > 0
    
    def test_temporal_intent(self):
        """Test temporal query classification"""
        query = "Which hour has peak transactions?"
        intent, confidence, entities = self.classifier.classify(query)
        assert intent == IntentType.TEMPORAL
    
    def test_comparative_intent(self):
        """Test comparative query classification"""
        query = "Compare iOS vs Android success rates"
        intent, confidence, entities = self.classifier.classify(query)
        assert intent == IntentType.COMPARATIVE
    
    def test_risk_intent(self):
        """Test risk query classification"""
        query = "What's the fraud rate?"
        intent, confidence, entities = self.classifier.classify(query)
        assert intent == IntentType.RISK
    
    def test_entity_extraction(self):
        """Test entity extraction"""
        query = "Show top 5 food transactions"
        intent, confidence, entities = self.classifier.classify(query)
        assert entities['category'] == 'Food'
        assert entities['top_n'] == 5


class TestHelpers:
    """Test utility functions"""
    
    def test_format_currency(self):
        """Test currency formatting"""
        assert "₹1,234.56" in format_currency(1234.56)
        assert "L" in format_currency(150000)  # Lakh
        assert "Cr" in format_currency(10000000)  # Crore
    
    def test_format_number(self):
        """Test number formatting"""
        assert "1,234" in format_number(1234)
        assert "K" in format_number(5000)
        assert "L" in format_number(200000)
    
    def test_parse_date_range(self):
        """Test date range parsing"""
        result = parse_date_range("january")
        assert result is not None
        assert result[0].startswith("2024-01")
        
        result = parse_date_range("december")
        assert result is not None
        assert result[0].startswith("2024-12")


class TestQueryRouter:
    """Test query routing"""
    
    def setup_method(self):
        """Setup for each test"""
        self.router = QueryRouter()
    
    def test_sql_routing(self):
        """Test routing to SQL engine"""
        query = "How much did we spend on Food?"
        result = self.router.route(query)
        assert result['use_sql'] is True
    
    def test_vector_routing(self):
        """Test routing to vector store"""
        query = "Why did spending spike?"
        result = self.router.route(query)
        # Semantic queries should use vector store
        assert result['intent'] == 'semantic'


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
