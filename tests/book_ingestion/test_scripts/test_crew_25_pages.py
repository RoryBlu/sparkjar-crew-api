#!/usr/bin/env python
"""Test book ingestion crew with 25 pages."""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/crew-api/src'))

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Test with the simple crew implementation
from crews.book_ingestion_crew.crew_simple import build_simple_crew, list_files
import time

def test_crew_25_pages():
    """Test the crew with 25 pages."""
    client_user_id = "3a411a30-1653-4caf-acee-de257ff50e36"
    folder_id = "1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO"
    
    print("🚀 Testing Book Ingestion Crew")
    print("=" * 60)
    
    # First list the files
    inputs = {
        "client_user_id": client_user_id,
        "google_drive_folder_path": folder_id,
        "language": "es"
    }
    
    print("📁 Listing files...")
    files = list_files(inputs)
    print(f"Found {len(files)} files")
    
    # Build the crew
    print("\n🤖 Building crew...")
    crew = build_simple_crew()
    
    # Prepare inputs for first 5 pages as a test
    page_inputs = []
    for i, file_info in enumerate(files[:5]):
        if file_info.get('local_path'):
            page_input = {
                "file_name": file_info['name'],
                "local_path": file_info['local_path'],
                "calculated_page_number": i + 1,
                "client_user_id": client_user_id,
                "book_key": folder_id,
                "language_code": "es"
            }
            page_inputs.append(page_input)
    
    print(f"\n📄 Processing {len(page_inputs)} pages with crew...")
    start_time = time.time()
    
    # Process with kickoff_for_each
    try:
        results = crew.kickoff_for_each(inputs=page_inputs)
        
        # Check results
        successful = 0
        for i, result in enumerate(results):
            if hasattr(result, 'raw'):
                result_str = str(result.raw)
            else:
                result_str = str(result)
            
            if "success" in result_str.lower() or "stored" in result_str.lower():
                successful += 1
                print(f"✅ Page {i+1}: Success")
            else:
                print(f"❌ Page {i+1}: Failed")
                print(f"   Result: {result_str[:100]}...")
        
        elapsed = time.time() - start_time
        print(f"\n📊 Summary:")
        print(f"   Processed: {len(page_inputs)}")
        print(f"   Successful: {successful}")
        print(f"   Time: {elapsed/60:.1f} minutes")
        print(f"   Rate: {successful/elapsed:.2f} pages/sec")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_crew_25_pages()