#!/usr/bin/env python
"""Test translation of Vervelyn book."""
import os
import sys
from pathlib import Path

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres.gvfiezbiyfggwdlvqnsc:Supabase123!@aws-0-us-west-1.pooler.supabase.com:5432/postgres'
os.environ['DATABASE_URL_DIRECT'] = 'postgresql+asyncpg://postgres.gvfiezbiyfggwdlvqnsc:Supabase123!@aws-0-us-west-1.pooler.supabase.com:5432/postgres'
os.environ['DATABASE_URL_POOLED'] = 'postgresql+asyncpg://postgres.gvfiezbiyfggwdlvqnsc:Supabase123!@aws-0-us-west-1.pooler.supabase.com:5432/postgres'

# Add paths
project_root = Path(__file__).parent
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

def test_vervelyn_translation():
    """Test the translation of Vervelyn book."""
    print("=" * 80)
    print("VERVELYN BOOK TRANSLATION TEST")
    print("=" * 80)
    
    # Vervelyn book information from VERVELYN_CLIENT_INFO.md
    inputs = {
        "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
        "book_key": "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO",
        "target_language": "en"
    }
    
    print(f"\nTranslating Vervelyn book:")
    print(f"Book key: {inputs['book_key']}")
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
            
            # Save the result to a file
            import json
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"vervelyn_translation_result_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"\nFull result saved to: {output_file}")
            
            # Try to extract and save as markdown
            if 'result' in result:
                md_file = f"vervelyn_book_translated_{timestamp}.md"
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write("# Vervelyn Book - English Translation\n\n")
                    f.write(f"**Source**: {inputs['book_key']}\n")
                    f.write(f"**Translated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")
                    f.write(str(result['result']))
                
                print(f"Translation exported to: {md_file}")
                
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
        print("Please set it with: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    test_vervelyn_translation()