"""
DuckDB Analytics Engine
Handles all deterministic SQL queries and aggregations
"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

class DuckDBAnalytics:
    """
    Analytics engine using DuckDB for fast in-memory SQL queries
    """
    
    def __init__(self, data_path: str, db_path: Optional[str] = None):
        """
        Initialize DuckDB connection and load data
        
        Args:
            data_path: Path to CSV file
            db_path: Optional path for persistent database
        """
        self.data_path = data_path
        self.db_path = db_path or ":memory:"
        self.conn = None
        self._initialize()
    
    def _initialize(self):
        """Set up DuckDB connection and load data"""
        try:
            logger.info(f"Initializing DuckDB with data from {self.data_path}")
            
            # Create connection
            self.conn = duckdb.connect(self.db_path)
            
            # Load CSV directly into DuckDB
            logger.info("Loading CSV into DuckDB...")
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS transactions AS 
                SELECT * FROM read_csv_auto('{self.data_path}')
            """)
            
            # Get row count
            row_count = self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            logger.success(f"Loaded {row_count:,} transactions into DuckDB")
            
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB: {e}")
            raise
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame
        
        Args:
            query: SQL query string
            
        Returns:
            DataFrame with query results
        """
        try:
            logger.debug(f"Executing query: {query[:100]}...")
            result = self.conn.execute(query).df()
            logger.debug(f"Query returned {len(result)} rows")
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def get_total_transactions(self, start_date: Optional[str] = None, 
                               end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get total transaction count and value"""
        where_clause = ""
        if start_date and end_date:
            where_clause = f"WHERE timestamp >= '{start_date}' AND timestamp < '{end_date}'"
        
        query = f"""
            SELECT 
                COUNT(*) as total_transactions,
                SUM("amount (INR)") as total_value,
                AVG("amount (INR)") as avg_amount,
                MIN("amount (INR)") as min_amount,
                MAX("amount (INR)") as max_amount
            FROM transactions
            {where_clause}
        """
        
        result = self.execute_query(query)
        return result.to_dict('records')[0]
    
    def get_category_spending(self, category: str, start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get spending for specific category"""
        where_clause = f"WHERE merchant_category = '{category}'"
        if start_date and end_date:
            where_clause += f" AND timestamp >= '{start_date}' AND timestamp < '{end_date}'"
        
        query = f"""
            SELECT 
                merchant_category,
                COUNT(*) as transaction_count,
                SUM("amount (INR)") as total_spent,
                AVG("amount (INR)") as avg_amount,
                MIN("amount (INR)") as min_amount,
                MAX("amount (INR)") as max_amount
            FROM transactions
            {where_clause}
            GROUP BY merchant_category
        """
        
        result = self.execute_query(query)
        return result.to_dict('records')[0] if len(result) > 0 else {}
    
    def get_peak_hours(self, category: Optional[str] = None, top_n: int = 5) -> pd.DataFrame:
        """Get peak transaction hours"""
        where_clause = f"WHERE merchant_category = '{category}'" if category else ""
        
        query = f"""
            SELECT 
                hour_of_day,
                COUNT(*) as transaction_count,
                SUM("amount (INR)") as total_value,
                AVG("amount (INR)") as avg_amount
            FROM transactions
            {where_clause}
            GROUP BY hour_of_day
            ORDER BY transaction_count DESC
            LIMIT {top_n}
        """
        
        return self.execute_query(query)
    
    def compare_devices(self, device1: str, device2: str, 
                       start_date: Optional[str] = None) -> pd.DataFrame:
        """Compare success rates between devices"""
        where_clause = f"WHERE device_type IN ('{device1}', '{device2}')"
        if start_date:
            where_clause += f" AND timestamp >= '{start_date}'"
        
        query = f"""
            SELECT 
                device_type,
                COUNT(*) as total_transactions,
                SUM(CASE WHEN transaction_status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN transaction_status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                ROUND(100.0 * SUM(CASE WHEN transaction_status = 'SUCCESS' THEN 1 ELSE 0 END) 
                      / COUNT(*), 2) as success_rate
            FROM transactions
            {where_clause}
            GROUP BY device_type
        """
        
        return self.execute_query(query)
    
    def get_fraud_analysis(self, category: Optional[str] = None) -> pd.DataFrame:
        """Get fraud statistics"""
        where_clause = "WHERE fraud_flag = 1"
        if category:
            where_clause += f" AND merchant_category = '{category}'"
        
        query = f"""
            SELECT 
                merchant_category,
                COUNT(*) as fraud_count,
                SUM("amount (INR)") as total_fraud_amount,
                AVG("amount (INR)") as avg_fraud_amount
            FROM transactions
            {where_clause}
            GROUP BY merchant_category
            ORDER BY fraud_count DESC
            LIMIT 10
        """
        
        return self.execute_query(query)
    
    def get_top_states(self, top_n: int = 10, start_date: Optional[str] = None) -> pd.DataFrame:
        """Get top states by transaction volume"""
        where_clause = f"WHERE timestamp >= '{start_date}'" if start_date else ""
        
        query = f"""
            SELECT 
                sender_state,
                COUNT(*) as transaction_count,
                SUM("amount (INR)") as total_value,
                AVG("amount (INR)") as avg_amount
            FROM transactions
            {where_clause}
            GROUP BY sender_state
            ORDER BY transaction_count DESC
            LIMIT {top_n}
        """
        
        return self.execute_query(query)
    
    def get_sample_transactions(self, filters: Optional[Dict] = None, limit: int = 5) -> pd.DataFrame:
        """Get sample transactions matching filters"""
        where_clauses = []
        
        if filters:
            for key, value in filters.items():
                if isinstance(value, str):
                    where_clauses.append(f"{key} = '{value}'")
                else:
                    where_clauses.append(f"{key} = {value}")
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
            SELECT * 
            FROM transactions
            {where_clause}
            LIMIT {limit}
        """
        
        return self.execute_query(query)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()


if __name__ == "__main__":
    # Test the analytics engine
    from config import Config
    
    engine = DuckDBAnalytics(Config.DATA_PATH)
    
    # Test queries
    print("Total transactions:", engine.get_total_transactions())
    print("\nFood spending:", engine.get_category_spending("Food"))
    print("\nPeak hours:\n", engine.get_peak_hours())
    print("\niOS vs Android:\n", engine.compare_devices("iOS", "Android"))
