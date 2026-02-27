"""
UPI Conversational Analytics - Streamlit Application
Main user interface for the analytics system
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from config import Config
from src.analytics.duckdb_engine import DuckDBAnalytics
from src.routing.intent_classifier import QueryRouter
from src.llm.groq_handler import GroqLLMHandler
from src.retrieval.vector_store import VectorStoreHandler
from loguru import logger
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="UPI Analytics Assistant",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .evidence-box {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #1f77b4;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'analytics_engine' not in st.session_state:
    st.session_state.analytics_engine = None
if 'query_router' not in st.session_state:
    st.session_state.query_router = None
if 'llm_handler' not in st.session_state:
    st.session_state.llm_handler = None

@st.cache_resource
def initialize_system():
    """Initialize all system components"""
    with st.spinner("🔄 Initializing analytics system..."):
        try:
            # Initialize analytics engine
            analytics = DuckDBAnalytics(Config.DATA_PATH)
            logger.info("Analytics engine initialized")
            
            # Initialize query router
            router = QueryRouter()
            logger.info("Query router initialized")
            
            # Initialize LLM handler
            llm = GroqLLMHandler(
                api_key=Config.GROQ_API_KEY,
                model=Config.LLM_MODEL,
                temperature=Config.LLM_TEMPERATURE,
                max_tokens=Config.LLM_MAX_TOKENS
            )
            logger.info("LLM handler initialized")
            
            return analytics, router, llm
            
        except Exception as e:
            st.error(f"Failed to initialize system: {e}")
            logger.error(f"Initialization error: {e}")
            return None, None, None

def process_query(query: str, analytics: DuckDBAnalytics, 
                 router: QueryRouter, llm: GroqLLMHandler):
    """Process user query and generate response"""
    try:
        # Route query
        routing = router.route(query)
        
        # Get analytics results based on intent
        if routing['use_sql']:
            # Execute appropriate SQL query based on entities
            entities = routing['entities']
            
            if routing['intent'] == 'descriptive':
                if entities['category']:
                    result = analytics.get_category_spending(
                        entities['category'],
                        entities['date_range'][0] if entities['date_range'] else None,
                        entities['date_range'][1] if entities['date_range'] else None
                    )
                else:
                    result = analytics.get_total_transactions(
                        entities['date_range'][0] if entities['date_range'] else None,
                        entities['date_range'][1] if entities['date_range'] else None
                    )
            
            elif routing['intent'] == 'temporal':
                result_df = analytics.get_peak_hours(
                    entities['category'],
                    top_n=entities['top_n'] or 5
                )
                result = result_df.to_dict('records')
            
            elif routing['intent'] == 'comparative':
                if 'ios' in query.lower() and 'android' in query.lower():
                    result_df = analytics.compare_devices('iOS', 'Android')
                    result = result_df.to_dict('records')
                else:
                    result = {"message": "Comparison query detected but specific comparison not identified"}
            
            elif routing['intent'] == 'segmentation':
                result_df = analytics.get_top_states(top_n=entities['top_n'] or 10)
                result = result_df.to_dict('records')
            
            elif routing['intent'] == 'risk':
                result_df = analytics.get_fraud_analysis(entities['category'])
                result = result_df.to_dict('records')
            
            else:
                result = analytics.get_total_transactions()
            
            # Get sample transactions
            sample_txns = analytics.get_sample_transactions(
                filters={'merchant_category': entities['category']} if entities['category'] else None,
                limit=5
            )
            sample_txns_list = sample_txns.to_dict('records') if not sample_txns.empty else []
            
            # Generate natural language response
            response = llm.generate_response(
                query=query,
                analytics_result=result,
                sample_transactions=sample_txns_list,
                sql_query="SQL query executed"
            )
        
        else:
            # Semantic/exploratory query
            response = llm.generate_explanation(
                query=query,
                context="This is a semantic query requiring contextual explanation."
            )
        
        return response, routing
        
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        return f"I encountered an error processing your query: {str(e)}", None

def main():
    """Main application"""
    
    # Header
    st.markdown('<h1 class="main-header">💳 UPI Analytics Assistant</h1>', unsafe_allow_html=True)
    st.markdown("**Ask questions about your UPI transactions in natural language**")
    
    # Sidebar
    with st.sidebar:
        st.header("📊 System Info")
        
        # Initialize system
        if st.session_state.analytics_engine is None:
            analytics, router, llm = initialize_system()
            st.session_state.analytics_engine = analytics
            st.session_state.query_router = router
            st.session_state.llm_handler = llm
        
        if st.session_state.analytics_engine:
            # Show stats
            stats = st.session_state.analytics_engine.get_total_transactions()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Transactions", f"{stats['total_transactions']:,}")
            with col2:
                st.metric("Total Value", f"₹{stats['total_value']/1_000_000:.1f}M")
            
            st.metric("Average Transaction", f"₹{stats['avg_amount']:.2f}")
            
            st.markdown("---")
            st.markdown("### 💡 Sample Questions")
            sample_queries = [
                "How much did we spend on Food?",
                "Compare iOS vs Android success rates",
                "Show top 5 states by volume",
                "What's the fraud rate?",
                "Which hour has peak transactions?",
                "Show weekend vs weekday patterns"
            ]
            
            for query in sample_queries:
                if st.button(query, key=f"sample_{query}"):
                    st.session_state.current_query = query
        
        st.markdown("---")
        if st.button("🔄 Clear Chat"):
            st.session_state.messages = []
            st.rerun()
    
    # Main chat interface
    st.markdown("### 💬 Chat")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "routing" in message and message["routing"]:
                    with st.expander("🔍 Query Analysis"):
                        st.json(message["routing"])
    
    # Query input
    if prompt := st.chat_input("Ask a question about your transactions..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process query
        with st.chat_message("assistant"):
            with st.spinner("🤔 Analyzing..."):
                response, routing = process_query(
                    prompt,
                    st.session_state.analytics_engine,
                    st.session_state.query_router,
                    st.session_state.llm_handler
                )
            
            st.markdown(response)
            
            if routing:
                with st.expander("🔍 Query Analysis"):
                    st.json(routing)
        
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "routing": routing
        })
    
    # Handle sample query from sidebar
    if hasattr(st.session_state, 'current_query'):
        query = st.session_state.current_query
        delattr(st.session_state, 'current_query')
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": query})
        
        # Process
        response, routing = process_query(
            query,
            st.session_state.analytics_engine,
            st.session_state.query_router,
            st.session_state.llm_handler
        )
        
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "routing": routing
        })
        
        st.rerun()

if __name__ == "__main__":
    main()
