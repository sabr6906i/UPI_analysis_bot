"""
Groq LLM Handler
Manages interactions with Groq API for natural language generation
"""

from typing import Dict, List, Optional
from groq import Groq
from loguru import logger
import json

class GroqLLMHandler:
    """
    Handler for Groq LLM API interactions
    """
    
    SYSTEM_PROMPT = """You are an analytics assistant for a UPI payment system. You help users understand transaction data through natural language.

CRITICAL RULES:
1. You ONLY explain and narrate results provided by the analytics engine
2. You NEVER perform calculations yourself
3. Always include an "Evidence" section citing:
   - The SQL query or aggregation used
   - Key numeric results
   - Sample transaction IDs (up to 5)
4. Be concise but informative (2-4 sentences for simple queries)
5. Use Indian Rupee (₹) symbol for currency
6. Compare results to dataset norms when relevant

DATASET CONTEXT:
- 250,000 UPI transactions from 2024
- Overall success rate: 95%
- Fraud rate: 0.19%
- Peak transaction hour: 7 PM
- Top categories: Grocery (20%), Food (15%), Shopping (12%)
- Geographic leader: Maharashtra (15%)

When explaining anomalies or patterns, reference these baseline metrics."""

    def __init__(self, api_key: str, model: str = "llama3-70b-8192", 
                 temperature: float = 0.1, max_tokens: int = 1000):
        """
        Initialize Groq handler
        
        Args:
            api_key: Groq API key
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
        """
        if not api_key:
            raise ValueError("Groq API key is required")
        
        self.client = Groq(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        logger.info(f"Initialized Groq handler with model: {model}")
    
    def generate_response(self, query: str, analytics_result: Dict, 
                         sample_transactions: Optional[List] = None,
                         sql_query: Optional[str] = None) -> str:
        """
        Generate natural language response from analytics results
        
        Args:
            query: Original user query
            analytics_result: Results from analytics engine
            sample_transactions: Sample transaction records
            sql_query: SQL query that was executed
            
        Returns:
            Natural language response with evidence
        """
        try:
            # Build context message
            context = self._build_context(query, analytics_result, 
                                         sample_transactions, sql_query)
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            answer = response.choices[0].message.content
            
            logger.debug(f"Generated response for query: {query[:50]}...")
            return answer
            
        except Exception as e:
            logger.error(f"Failed to generate LLM response: {e}")
            return self._fallback_response(analytics_result)
    
    def _build_context(self, query: str, analytics_result: Dict,
                      sample_transactions: Optional[List], 
                      sql_query: Optional[str]) -> str:
        """Build context message for LLM"""
        
        context_parts = [
            f"User Query: {query}",
            "",
            "Analytics Results:",
            json.dumps(analytics_result, indent=2, default=str)
        ]
        
        if sql_query:
            context_parts.extend([
                "",
                "SQL Query Used:",
                sql_query
            ])
        
        if sample_transactions:
            context_parts.extend([
                "",
                "Sample Transactions:",
                json.dumps(sample_transactions[:5], indent=2, default=str)
            ])
        
        context_parts.extend([
            "",
            "Instructions:",
            "1. Provide a clear 2-4 sentence answer to the user's query",
            "2. Reference the specific numbers from the analytics results",
            "3. End with an 'Evidence' section listing:",
            "   - SQL query used (if available)",
            "   - Key metrics",
            "   - Sample transaction IDs (if available)"
        ])
        
        return "\n".join(context_parts)
    
    def _fallback_response(self, analytics_result: Dict) -> str:
        """Generate fallback response if LLM fails"""
        
        if not analytics_result:
            return "I couldn't retrieve any data for your query. Please try rephrasing."
        
        # Simple formatted output
        response_parts = ["Here are the results:\n"]
        
        for key, value in analytics_result.items():
            if isinstance(value, (int, float)):
                if 'amount' in key.lower() or 'value' in key.lower():
                    response_parts.append(f"• {key}: ₹{value:,.2f}")
                else:
                    response_parts.append(f"• {key}: {value:,}")
            else:
                response_parts.append(f"• {key}: {value}")
        
        return "\n".join(response_parts)
    
    def generate_explanation(self, query: str, context: str) -> str:
        """
        Generate explanation for semantic/exploratory queries
        
        Args:
            query: User query
            context: Contextual information
            
        Returns:
            Explanation text
        """
        try:
            prompt = f"""User asked: "{query}"

Context and data:
{context}

Provide a clear, data-driven explanation addressing the user's question. 
Reference specific metrics and patterns from the context."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}")
            return "I encountered an error generating the explanation. Please try again."


if __name__ == "__main__":
    # Test the LLM handler
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if api_key:
        handler = GroqLLMHandler(api_key)
        
        # Test with sample analytics result
        test_result = {
            "merchant_category": "Food",
            "transaction_count": 37464,
            "total_spent": 19919402,
            "avg_amount": 531.65
        }
        
        response = handler.generate_response(
            query="How much did we spend on Food in January?",
            analytics_result=test_result,
            sql_query="SELECT * FROM transactions WHERE category='Food'"
        )
        
        print("Generated Response:")
        print(response)
    else:
        print("GROQ_API_KEY not set in .env file")
