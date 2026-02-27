#!/usr/bin/env python3
"""
Automated Setup Script for UPI Analytics Project
Helps with initial configuration and data loading
"""

import os
import sys
import shutil
from pathlib import Path
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

class ProjectSetup:
    """Handles project setup and initialization"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        logger.info(f"Project root: {self.project_root}")
    
    def check_python_version(self):
        """Check Python version"""
        logger.info("Checking Python version...")
        version = sys.version_info
        
        if version.major < 3 or (version.major == 3 and version.minor < 9):
            logger.error(f"Python 3.9+ required, found {version.major}.{version.minor}")
            return False
        
        logger.success(f"Python {version.major}.{version.minor}.{version.micro} ✓")
        return True
    
    def check_env_file(self):
        """Check and create .env file"""
        logger.info("Checking .env configuration...")
        
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if not env_file.exists():
            if env_example.exists():
                shutil.copy(env_example, env_file)
                logger.warning(".env file created from .env.example")
                logger.warning("⚠️  Please edit .env and add your GROQ_API_KEY!")
                return False
            else:
                logger.error(".env.example not found")
                return False
        
        # Check if API key is set
        with open(env_file) as f:
            content = f.read()
            if "your_groq_api_key_here" in content:
                logger.warning("⚠️  GROQ_API_KEY not set in .env file")
                return False
        
        logger.success(".env file configured ✓")
        return True
    
    def check_data_file(self):
        """Check if data file exists"""
        logger.info("Checking data file...")
        
        data_dir = self.project_root / "data" / "raw"
        data_files = list(data_dir.glob("*.csv"))
        
        if not data_files:
            logger.warning("⚠️  No CSV file found in data/raw/")
            logger.info("Please copy your upi_transactions_2024.csv to data/raw/")
            return False
        
        data_file = data_files[0]
        size_mb = data_file.stat().st_size / (1024 * 1024)
        logger.success(f"Data file found: {data_file.name} ({size_mb:.1f} MB) ✓")
        return True
    
    def check_dependencies(self):
        """Check if required packages are installed"""
        logger.info("Checking dependencies...")
        
        required = [
            'pandas', 'duckdb', 'streamlit', 'groq', 
            'langchain', 'chromadb', 'sentence_transformers',
            'matplotlib', 'loguru'
        ]
        
        missing = []
        for package in required:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
        
        if missing:
            logger.warning(f"⚠️  Missing packages: {', '.join(missing)}")
            logger.info("Run: pip install -r requirements.txt")
            return False
        
        logger.success("All dependencies installed ✓")
        return True
    
    def create_directories(self):
        """Ensure all directories exist"""
        logger.info("Creating project directories...")
        
        dirs = [
            "data/raw",
            "data/processed",
            "data/embeddings",
            "logs",
            "outputs/reports",
            "outputs/visualizations"
        ]
        
        for dir_path in dirs:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
        
        logger.success("Directories created ✓")
        return True
    
    def test_groq_connection(self):
        """Test Groq API connection"""
        logger.info("Testing Groq API connection...")
        
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key or api_key == "your_groq_api_key_here":
                logger.warning("⚠️  GROQ_API_KEY not configured")
                return False
            
            from groq import Groq
            client = Groq(api_key=api_key)
            
            # Simple test
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            logger.success("Groq API connection successful ✓")
            return True
            
        except Exception as e:
            logger.error(f"Groq API test failed: {e}")
            return False
    
    def run_full_check(self):
        """Run all checks"""
        logger.info("=" * 60)
        logger.info("UPI ANALYTICS PROJECT - SETUP CHECK")
        logger.info("=" * 60)
        
        checks = [
            ("Python Version", self.check_python_version),
            ("Project Directories", self.create_directories),
            ("Dependencies", self.check_dependencies),
            ("Environment Config", self.check_env_file),
            ("Data File", self.check_data_file),
            ("Groq API", self.test_groq_connection)
        ]
        
        results = []
        for name, check_func in checks:
            try:
                result = check_func()
                results.append((name, result))
            except Exception as e:
                logger.error(f"{name} check failed: {e}")
                results.append((name, False))
            print()
        
        # Summary
        logger.info("=" * 60)
        logger.info("SETUP SUMMARY")
        logger.info("=" * 60)
        
        for name, passed in results:
            status = "✓ PASS" if passed else "✗ FAIL"
            color = "green" if passed else "red"
            logger.info(f"{name:<25} {status}")
        
        all_passed = all(passed for _, passed in results)
        
        print()
        if all_passed:
            logger.success("🎉 All checks passed! Ready to run the application.")
            logger.info("Start the app with: streamlit run app.py")
        else:
            logger.warning("⚠️  Some checks failed. Please fix the issues above.")
            logger.info("\nQuick fixes:")
            logger.info("1. Install dependencies: pip install -r requirements.txt")
            logger.info("2. Configure .env: Add your GROQ_API_KEY")
            logger.info("3. Add data: Copy CSV to data/raw/")
        
        return all_passed


def main():
    """Main setup function"""
    setup = ProjectSetup()
    success = setup.run_full_check()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
