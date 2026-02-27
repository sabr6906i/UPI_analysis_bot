"""
Configuration management for UPI Analytics System
Loads settings from .env file and provides centralized access
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
SRC_DIR = PROJECT_ROOT / "src"
LOGS_DIR = PROJECT_ROOT / "logs"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

class Config:
    """Centralized configuration class"""
    
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Data paths
    DATA_PATH = os.getenv("DATA_PATH", str(DATA_DIR / "raw" / "upi_transactions_2024.csv"))
    PROCESSED_DATA_PATH = os.getenv("PROCESSED_DATA_PATH", str(DATA_DIR / "processed"))
    EMBEDDINGS_PATH = os.getenv("EMBEDDINGS_PATH", str(DATA_DIR / "embeddings"))
    
    # Database
    DUCKDB_PATH = os.getenv("DUCKDB_PATH", str(DATA_DIR / "processed" / "analytics.duckdb"))
    
    # Vector Store
    VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "chromadb")
    VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", str(DATA_DIR / "embeddings" / "chroma_db"))
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # LLM Configuration
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3-70b-8192")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1000"))
    
    # Application
    APP_NAME = os.getenv("APP_NAME", "UPI Analytics Assistant")
    APP_PORT = int(os.getenv("APP_PORT", "8501"))
    DEBUG_MODE = os.getenv("DEBUG_MODE", "True").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Query settings
    MAX_RETRIEVAL_RESULTS = int(os.getenv("MAX_RETRIEVAL_RESULTS", "5"))
    SQL_TIMEOUT_SECONDS = int(os.getenv("SQL_TIMEOUT_SECONDS", "30"))
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "True").lower() == "true"
    
    # Security
    ENABLE_AUTH = os.getenv("ENABLE_AUTH", "False").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Schema information (from your dataset)
    SCHEMA_INFO = {
        "table_name": "transactions",
        "columns": {
            "transaction id": "str - Unique transaction identifier",
            "timestamp": "datetime - Transaction timestamp",
            "transaction type": "str - P2P, P2M, Bill Payment, Recharge",
            "merchant_category": "str - Category like Food, Grocery, Shopping, etc.",
            "amount (INR)": "int - Transaction amount in INR",
            "transaction_status": "str - SUCCESS or FAILED",
            "sender_age_group": "str - Age group of sender",
            "receiver_age_group": "str - Age group of receiver",
            "sender_state": "str - Indian state of sender",
            "sender_bank": "str - Bank name",
            "receiver_bank": "str - Bank name",
            "device_type": "str - Android, iOS, Web",
            "network_type": "str - 4G, 5G, WiFi, 3G",
            "fraud_flag": "int - 0 or 1",
            "hour_of_day": "int - 0-23",
            "day_of_week": "str - Monday to Sunday",
            "is_weekend": "int - 0 or 1"
        }
    }
    
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        errors = []
        
        if not cls.GROQ_API_KEY:
            errors.append("GROQ_API_KEY not set in .env file")
        
        if not Path(cls.DATA_PATH).exists():
            errors.append(f"Data file not found: {cls.DATA_PATH}")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True

# Validate on import (optional - comment out if needed)
# Config.validate()
