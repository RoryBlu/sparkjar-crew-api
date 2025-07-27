#!/usr/bin/env python
"""Run translation quality test with detailed output."""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Also add src to path
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from tests.crews.test_book_translation_crew.test_integration import TestBookTranslationIntegration


async def main():
    """Run the translation quality test."""
    print("=" * 80)
    print("BOOK TRANSLATION QUALITY TEST")
    print("=" * 80)
    print("\nThis test will:")
    print("1. Insert 5 Spanish pages from 'El Barón Rampante' into the database")
    print("2. Run the book translation crew to translate them to English")
    print("3. Validate that translations are complete (not summaries)")
    print("4. Check translation quality metrics")
    print("\n" + "=" * 80)
    
    # Create test instance
    test_instance = TestBookTranslationIntegration()
    
    # Setup test data - Using valid client_user_id
    test_client_data = {
        "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
        "client_id": "gvfiezbiyfggwdlvqnsc",
        "book_key": "test_translation_quality",
        "database_url": None
    }
    
    sample_pages = await test_instance.sample_spanish_pages()
    
    try:
        print("\n📝 Setting up test data...")
        await test_instance.setup_test_data(test_client_data, sample_pages)
        print("✓ Test data inserted successfully")
        
        print("\n🔄 Running translation crew...")
        print("This may take a few minutes as the crew translates 5 pages...")
        
        # Run the actual test
        await test_instance.test_5_page_translation_quality(test_client_data, sample_pages)
        
        print("\n✅ TEST PASSED: All translations are complete and high quality!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🧹 Cleaning up test data...")
        await test_instance.cleanup_test_data(test_client_data)
        print("✓ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())