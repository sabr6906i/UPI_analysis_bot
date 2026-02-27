"""
Intent Classification & Query Routing
Routes natural language queries to appropriate handlers
"""

import re
from typing import Dict, Tuple, Optional
from enum import Enum
from loguru import logger

class IntentType(Enum):
    """Query intent types"""
    DESCRIPTIVE = "descriptive"  # What, How much, Show me
    TEMPORAL = "temporal"  # When, Which hour, Trend
    COMPARATIVE = "comparative"  # Compare, vs, difference
    SEGMENTATION = "segmentation"  # Top N, By category, Group by
    RISK = "risk"  # Fraud, failure, risk
    SEMANTIC = "semantic"  # Why, Explain, Unusual
    UNKNOWN = "unknown"


class IntentClassifier:
    """
    Rule-based intent classifier with keyword matching
    """
    
    # Intent detection patterns
    PATTERNS = {
        IntentType.DESCRIPTIVE: [
            r'\b(what|how much|total|sum|count|show|display|tell me)\b',
            r'\b(spending|spent|volume|transactions?|amount)\b',
            r'\b(average|mean|median|stats)\b'
        ],
        
        IntentType.TEMPORAL: [
            r'\b(when|which (hour|day|month|time))\b',
            r'\b(trend|over time|daily|monthly|weekly)\b',
            r'\b(peak|highest|lowest|busiest)\b',
            r'\b(last (month|week|year|quarter))\b'
        ],
        
        IntentType.COMPARATIVE: [
            r'\b(compare|vs|versus|between)\b',
            r'\b(difference|higher|lower|better|worse)\b',
            r'\b(ios vs android|weekday vs weekend)\b'
        ],
        
        IntentType.SEGMENTATION: [
            r'\b(top \d+|bottom \d+)\b',
            r'\b(by (category|state|age|device|bank))\b',
            r'\b(group by|breakdown|segment)\b',
            r'\b(which (states?|categories?|merchants?))\b'
        ],
        
        IntentType.RISK: [
            r'\b(fraud|risk|suspicious|flagged)\b',
            r'\b(fail(ed|ure)?|error|problem)\b',
            r'\b(success rate|failure rate)\b'
        ],
        
        IntentType.SEMANTIC: [
            r'\b(why|explain|reason|cause)\b',
            r'\b(unusual|anomal|spike|drop|strange)\b',
            r'\b(insight|pattern|trend)\b'
        ]
    }
    
    # Category keywords for extraction
    CATEGORIES = [
        'Food', 'Grocery', 'Shopping', 'Fuel', 'Entertainment', 
        'Utilities', 'Transport', 'Healthcare', 'Education', 'Other'
    ]
    
    DEVICES = ['Android', 'iOS', 'Web']
    NETWORKS = ['4G', '5G', 'WiFi', '3G']
    
    def __init__(self):
        """Initialize classifier"""
        self.compiled_patterns = {
            intent: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for intent, patterns in self.PATTERNS.items()
        }
    
    def classify(self, query: str) -> Tuple[IntentType, float, Dict]:
        """
        Classify query intent
        
        Args:
            query: User query string
            
        Returns:
            Tuple of (intent_type, confidence, extracted_entities)
        """
        query_lower = query.lower()
        scores = {intent: 0 for intent in IntentType}
        
        # Score each intent type
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(query_lower):
                    scores[intent] += 1
        
        # Get best intent
        if max(scores.values()) == 0:
            best_intent = IntentType.UNKNOWN
            confidence = 0.0
        else:
            best_intent = max(scores, key=scores.get)
            confidence = min(scores[best_intent] / len(self.compiled_patterns[best_intent]), 1.0)
        
        # Extract entities
        entities = self._extract_entities(query)
        
        logger.info(f"Classified '{query[:50]}...' as {best_intent.value} (confidence: {confidence:.2f})")
        
        return best_intent, confidence, entities
    
    def _extract_entities(self, query: str) -> Dict:
        """
        Extract entities like categories, dates, numbers from query
        """
        entities = {
            'category': None,
            'device': None,
            'network': None,
            'date_range': None,
            'amount_range': None,
            'top_n': None
        }
        
        query_lower = query.lower()
        
        # Extract category
        for category in self.CATEGORIES:
            if category.lower() in query_lower:
                entities['category'] = category
                break
        
        # Extract device
        for device in self.DEVICES:
            if device.lower() in query_lower:
                entities['device'] = device
                break
        
        # Extract network
        for network in self.NETWORKS:
            if network.lower() in query_lower:
                entities['network'] = network
                break
        
        # Extract top N
        top_n_match = re.search(r'top\s+(\d+)', query_lower)
        if top_n_match:
            entities['top_n'] = int(top_n_match.group(1))
        
        # Extract date references
        if 'january' in query_lower or 'jan' in query_lower:
            entities['date_range'] = ('2024-01-01', '2024-02-01')
        elif 'december' in query_lower or 'dec' in query_lower:
            entities['date_range'] = ('2024-12-01', '2025-01-01')
        elif 'last month' in query_lower:
            entities['date_range'] = ('2024-12-01', '2025-01-01')
        
        return entities
    
    def should_use_vector_store(self, intent: IntentType, confidence: float) -> bool:
        """
        Determine if vector store should be used
        
        Args:
            intent: Classified intent
            confidence: Classification confidence
            
        Returns:
            Boolean indicating if vector store should be used
        """
        # Use vector store for semantic queries or low-confidence classifications
        return intent == IntentType.SEMANTIC or confidence < 0.5


class QueryRouter:
    """
    Routes queries to appropriate handlers based on intent
    """
    
    def __init__(self):
        """Initialize router with classifier"""
        self.classifier = IntentClassifier()
    
    def route(self, query: str) -> Dict:
        """
        Route query to appropriate handler
        
        Args:
            query: User query
            
        Returns:
            Routing decision dictionary
        """
        intent, confidence, entities = self.classifier.classify(query)
        
        routing_decision = {
            'intent': intent.value,
            'confidence': confidence,
            'entities': entities,
            'use_sql': intent in [
                IntentType.DESCRIPTIVE,
                IntentType.TEMPORAL,
                IntentType.COMPARATIVE,
                IntentType.SEGMENTATION,
                IntentType.RISK
            ],
            'use_vector_store': self.classifier.should_use_vector_store(intent, confidence),
            'query': query
        }
        
        logger.debug(f"Routing decision: {routing_decision}")
        
        return routing_decision


if __name__ == "__main__":
    # Test the classifier
    router = QueryRouter()
    
    test_queries = [
        "How much did we spend on Food in January?",
        "Compare iOS vs Android success rates",
        "Show top 5 states by volume",
        "Why did spending spike in March?",
        "What's the fraud rate?",
        "Which hour has peak transactions?"
    ]
    
    for query in test_queries:
        result = router.route(query)
        print(f"\nQuery: {query}")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"Entities: {result['entities']}")
        print(f"Use SQL: {result['use_sql']}, Use Vector: {result['use_vector_store']}")
