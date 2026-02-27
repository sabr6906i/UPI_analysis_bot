"""
Vector Store Handler
Manages embeddings and semantic search for transaction data
"""

import pandas as pd
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from loguru import logger
from pathlib import Path

class VectorStoreHandler:
    """
    Manages vector embeddings and semantic search
    """
    
    def __init__(self, store_path: str, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize vector store
        
        Args:
            store_path: Path to persist vector store
            embedding_model: Model for generating embeddings
        """
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initializing vector store at {store_path}")
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)
        logger.info(f"Loaded embedding model: {embedding_model}")
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.store_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = None
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Initialize or load collection"""
        try:
            self.collection = self.client.get_or_create_collection(
                name="transactions",
                metadata={"description": "UPI transaction embeddings"}
            )
            logger.success(f"Collection initialized with {self.collection.count()} documents")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    def create_embeddings(self, df: pd.DataFrame, batch_size: int = 1000):
        """
        Create embeddings for transaction data
        
        Args:
            df: Transaction DataFrame
            batch_size: Batch size for processing
        """
        logger.info(f"Creating embeddings for {len(df)} transactions...")
        
        # Create text descriptions for each transaction
        texts = []
        ids = []
        metadatas = []
        
        for idx, row in df.iterrows():
            # Create descriptive text
            text = (
                f"Transaction on {row['timestamp']} for ₹{row['amount (INR)']} "
                f"in category {row['merchant_category']} via {row['device_type']} "
                f"using {row['network_type']} network. "
                f"Status: {row['transaction_status']}. "
                f"Sender from {row['sender_state']}, age {row['sender_age_group']}. "
                f"Bank: {row['sender_bank']} to {row['receiver_bank']}."
            )
            
            texts.append(text)
            ids.append(str(row['transaction id']))
            
            # Store metadata
            metadatas.append({
                'timestamp': str(row['timestamp']),
                'category': str(row['merchant_category']),
                'amount': float(row['amount (INR)']),
                'status': str(row['transaction_status']),
                'fraud_flag': int(row['fraud_flag'])
            })
            
            # Add to collection in batches
            if len(texts) >= batch_size:
                self._add_batch(texts, ids, metadatas)
                texts, ids, metadatas = [], [], []
        
        # Add remaining
        if texts:
            self._add_batch(texts, ids, metadatas)
        
        logger.success(f"Created embeddings for {self.collection.count()} transactions")
    
    def _add_batch(self, texts: List[str], ids: List[str], metadatas: List[Dict]):
        """Add batch to collection"""
        try:
            # Generate embeddings
            embeddings = self.embedding_model.encode(texts).tolist()
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                ids=ids,
                metadatas=metadatas
            )
        except Exception as e:
            logger.error(f"Failed to add batch: {e}")
    
    def search(self, query: str, n_results: int = 5, 
              filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar transactions
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_dict: Metadata filters
            
        Returns:
            List of matching results
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_dict
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
            
            logger.debug(f"Found {len(formatted_results)} results for query")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_transaction_context(self, transaction_ids: List[str]) -> List[Dict]:
        """
        Get full context for specific transactions
        
        Args:
            transaction_ids: List of transaction IDs
            
        Returns:
            List of transaction contexts
        """
        try:
            results = self.collection.get(
                ids=transaction_ids,
                include=['documents', 'metadatas']
            )
            
            contexts = []
            for i in range(len(results['ids'])):
                contexts.append({
                    'id': results['ids'][i],
                    'document': results['documents'][i],
                    'metadata': results['metadatas'][i]
                })
            
            return contexts
            
        except Exception as e:
            logger.error(f"Failed to get transaction context: {e}")
            return []
    
    def reset_collection(self):
        """Delete and recreate collection"""
        try:
            self.client.delete_collection("transactions")
            self._initialize_collection()
            logger.info("Collection reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")


if __name__ == "__main__":
    # Test vector store
    from config import Config
    
    # Initialize
    vector_store = VectorStoreHandler(
        store_path=Config.VECTOR_STORE_PATH,
        embedding_model=Config.EMBEDDING_MODEL
    )
    
    # Load sample data
    df = pd.read_csv(Config.DATA_PATH).head(100)  # Test with 100 rows
    
    # Create embeddings
    print("Creating embeddings...")
    vector_store.create_embeddings(df)
    
    # Test search
    print("\nSearching for 'high value food transactions'...")
    results = vector_store.search("high value food transactions", n_results=3)
    
    for result in results:
        print(f"\nID: {result['id']}")
        print(f"Document: {result['document'][:100]}...")
        print(f"Metadata: {result['metadata']}")
