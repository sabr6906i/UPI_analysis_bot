"""
Utility functions for the UPI Analytics system
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
from loguru import logger

def format_currency(amount: float) -> str:
    """
    Format amount as Indian Rupees
    
    Args:
        amount: Amount to format
        
    Returns:
        Formatted string with ₹ symbol
    """
    if amount >= 10_000_000:  # 1 crore
        return f"₹{amount/10_000_000:.2f}Cr"
    elif amount >= 100_000:  # 1 lakh
        return f"₹{amount/100_000:.2f}L"
    elif amount >= 1_000:
        return f"₹{amount/1_000:.1f}K"
    else:
        return f"₹{amount:,.2f}"

def format_number(num: int) -> str:
    """
    Format large numbers with Indian numbering system
    
    Args:
        num: Number to format
        
    Returns:
        Formatted string
    """
    if num >= 10_000_000:  # 1 crore
        return f"{num/10_000_000:.2f}Cr"
    elif num >= 100_000:  # 1 lakh
        return f"{num/100_000:.2f}L"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{num:,}"

def parse_date_range(date_str: str) -> Optional[tuple]:
    """
    Parse natural language date ranges
    
    Args:
        date_str: Date string like "last month", "january", "Q4 2024"
        
    Returns:
        Tuple of (start_date, end_date) or None
    """
    date_str = date_str.lower()
    now = datetime.now()
    
    # Month names
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    
    # Check for month names
    for month_name, month_num in months.items():
        if month_name in date_str:
            year = 2024  # Default year
            start = datetime(year, month_num, 1)
            if month_num == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month_num + 1, 1)
            return (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    
    # Check for relative dates
    if 'last month' in date_str:
        start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        end = now.replace(day=1)
        return (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    
    if 'this month' in date_str:
        start = now.replace(day=1)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1)
        else:
            end = datetime(now.year, now.month + 1, 1)
        return (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    
    return None

def extract_metrics(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract and format key metrics from analytics results
    
    Args:
        data: Dictionary of analytics results
        
    Returns:
        Dictionary of formatted metrics
    """
    metrics = {}
    
    for key, value in data.items():
        if isinstance(value, (int, float)):
            if 'amount' in key.lower() or 'value' in key.lower():
                metrics[key] = format_currency(value)
            elif 'rate' in key.lower() or 'percent' in key.lower():
                metrics[key] = f"{value:.2f}%"
            elif 'count' in key.lower():
                metrics[key] = format_number(int(value))
            else:
                metrics[key] = f"{value:,.2f}"
        else:
            metrics[key] = str(value)
    
    return metrics

def build_evidence_block(sql_query: Optional[str], 
                        results: Dict[str, Any],
                        sample_ids: Optional[List[str]] = None) -> str:
    """
    Build evidence block for explainability
    
    Args:
        sql_query: SQL query executed
        results: Analytics results
        sample_ids: Sample transaction IDs
        
    Returns:
        Formatted evidence block
    """
    evidence_parts = ["**Evidence:**"]
    
    if sql_query:
        evidence_parts.append(f"\n```sql\n{sql_query}\n```")
    
    if results:
        evidence_parts.append("\n**Key Metrics:**")
        metrics = extract_metrics(results)
        for key, value in metrics.items():
            evidence_parts.append(f"- {key}: {value}")
    
    if sample_ids:
        evidence_parts.append("\n**Sample Transactions:**")
        evidence_parts.append(", ".join(sample_ids[:5]))
    
    return "\n".join(evidence_parts)

def summarize_dataframe(df: pd.DataFrame, max_rows: int = 5) -> str:
    """
    Create human-readable summary of DataFrame
    
    Args:
        df: DataFrame to summarize
        max_rows: Maximum rows to include
        
    Returns:
        Text summary
    """
    summary_parts = [f"Found {len(df)} records:"]
    
    for idx, row in df.head(max_rows).iterrows():
        row_summary = []
        for col, value in row.items():
            if 'amount' in col.lower():
                row_summary.append(f"{col}: {format_currency(value)}")
            elif isinstance(value, (int, float)) and value > 1000:
                row_summary.append(f"{col}: {value:,}")
            else:
                row_summary.append(f"{col}: {value}")
        summary_parts.append(f"\n{idx+1}. " + ", ".join(row_summary[:3]))
    
    if len(df) > max_rows:
        summary_parts.append(f"\n... and {len(df) - max_rows} more")
    
    return "\n".join(summary_parts)

def validate_query_params(params: Dict[str, Any]) -> bool:
    """
    Validate query parameters
    
    Args:
        params: Dictionary of parameters
        
    Returns:
        Boolean indicating if valid
    """
    # Check for SQL injection patterns
    dangerous_patterns = ['DROP', 'DELETE', 'INSERT', 'UPDATE', '--', ';--']
    
    for key, value in params.items():
        if isinstance(value, str):
            value_upper = value.upper()
            for pattern in dangerous_patterns:
                if pattern in value_upper:
                    logger.warning(f"Potential SQL injection detected: {value}")
                    return False
    
    return True

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split list into chunks
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def clean_text(text: str) -> str:
    """
    Clean and normalize text
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove special characters but keep basic punctuation
    text = ''.join(char for char in text if char.isalnum() or char in ' .,!?-')
    
    return text.strip()


if __name__ == "__main__":
    # Test utilities
    print("Testing utility functions:\n")
    
    print("Currency formatting:")
    print(f"  1,234.56 -> {format_currency(1234.56)}")
    print(f"  150,000 -> {format_currency(150000)}")
    print(f"  10,000,000 -> {format_currency(10000000)}")
    
    print("\nNumber formatting:")
    print(f"  1,234 -> {format_number(1234)}")
    print(f"  150,000 -> {format_number(150000)}")
    
    print("\nDate parsing:")
    print(f"  'january' -> {parse_date_range('january')}")
    print(f"  'last month' -> {parse_date_range('last month')}")
    
    print("\nMetrics extraction:")
    data = {
        'total_amount': 1523200,
        'transaction_count': 37464,
        'success_rate': 95.05
    }
    print(f"  {data}")
    print(f"  -> {extract_metrics(data)}")
