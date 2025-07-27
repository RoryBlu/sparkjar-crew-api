#!/usr/bin/env python
"""Simple direct test of the book translation crew without full environment."""
import os
import sys
import asyncio
from pathlib import Path

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres.gvfiezbiyfggwdlvqnsc:Supabase123!@aws-0-us-west-1.pooler.supabase.com:5432/postgres'
os.environ['DATABASE_URL_DIRECT'] = 'postgresql+asyncpg://postgres.gvfiezbiyfggwdlvqnsc:Supabase123!@aws-0-us-west-1.pooler.supabase.com:5432/postgres'
os.environ['DATABASE_URL_POOLED'] = 'postgresql+asyncpg://postgres.gvfiezbiyfggwdlvqnsc:Supabase123!@aws-0-us-west-1.pooler.supabase.com:5432/postgres'
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', '')

# Add paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Mock the shared config to bypass sparkjar-shared import
class MockConfig:
    CHROMA_URL = None
    DATABASE_URL = os.environ['DATABASE_URL']
    DATABASE_URL_DIRECT = os.environ['DATABASE_URL_DIRECT']
    DATABASE_URL_POOLED = os.environ['DATABASE_URL_POOLED']
    API_SECRET_KEY = "test-key"
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

sys.modules['config'] = MockConfig
sys.modules['sparkjar_shared'] = type(sys)('sparkjar_shared')
sys.modules['sparkjar_shared.config'] = type(sys)('config')
sys.modules['sparkjar_shared.config.shared_settings'] = MockConfig

# Now we can import
from src.crews.book_translation_crew.main import kickoff

def test_translation():
    """Test the translation with 5 pages."""
    print("=" * 80)
    print("BOOK TRANSLATION CREW - DIRECT TEST")
    print("=" * 80)
    
    # Test inputs - Using valid client_user_id
    inputs = {
        "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
        "book_key": "el-baron-book",  # Using existing book
        "target_language": "en"
    }
    
    print(f"\nTesting translation for book: {inputs['book_key']}")
    print(f"Target language: {inputs['target_language']}")
    print("\nStarting crew execution...")
    print("-" * 80)
    
    try:
        # Run the crew
        result = kickoff(inputs)
        
        print("\n" + "-" * 80)
        print("RESULT:")
        print(f"Status: {result.get('status')}")
        print(f"Book Key: {result.get('book_key')}")
        
        if result.get('status') == 'completed':
            print("\n✅ Translation completed successfully!")
            print(f"\nResult summary: {result.get('result', 'No result data')[:500]}...")
        else:
            print(f"\n❌ Translation failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ Error during execution: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check for API key
    if not os.environ.get('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY environment variable is not set")
        sys.exit(1)
    
    test_translation()