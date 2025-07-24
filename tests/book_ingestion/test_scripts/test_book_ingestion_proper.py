#!/usr/bin/env python3
"""
Test book ingestion crew with proper schema from database.
This version uses the correct schema structure.
"""

import json
import sys
import os
import time
from datetime import datetime

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'services/crew-api/src'))

def load_request():
    """Load the request JSON that matches database schema."""
    with open('book_ingestion_request.json', 'r') as f:
        return json.load(f)

def print_header(title, emoji="📌"):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"{emoji} {title}")
    print(f"{'='*70}\n")

def test_book_ingestion():
    """Test the book ingestion crew with proper schema."""
    print_header("Book Ingestion Crew Test - Schema Compliant", "🚀")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load the request
    print_header("Loading Request", "📋")
    request_data = load_request()
    print("Request structure:")
    print(json.dumps(request_data, indent=2))
    
    # Validate required fields
    print_header("Validating Required Fields", "✅")
    required_fields = [
        'client_user_id', 'actor_type', 'actor_id', 
        'job_key', 'google_drive_folder_path', 'language'
    ]
    
    request_payload = request_data['request_data']
    for field in required_fields:
        value = request_payload.get(field)
        print(f"  {field}: {value} {'✓' if value else '✗'}")
    
    print("\nOptional fields:")
    print(f"  book_metadata: {json.dumps(request_payload.get('book_metadata', {}), indent=4)}")
    print(f"  output_format: {request_payload.get('output_format', 'txt (default)')}")
    print(f"  confidence_threshold: {request_payload.get('confidence_threshold', '0.85 (default)')}")
    
    input("\n✋ Press Enter to proceed with crew import...")
    
    # Try importing the crew
    print_header("Importing Crew", "🔧")
    try:
        from crews.book_ingestion_crew.crew import kickoff
        print("✅ Successfully imported book_ingestion_crew")
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("\nThis might be due to Python version incompatibility.")
        print("CrewAI requires Python 3.10+ for union type syntax support.")
        return
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    input("\n✋ Press Enter to execute the crew...")
    
    # Execute the crew
    print_header("Executing Crew", "🚦")
    print("Processing 25 pages from Google Drive...")
    print(f"Folder: {request_payload['google_drive_folder_path']}")
    print(f"Language: {request_payload['language']} (Spanish)")
    print(f"Book: {request_payload['book_metadata']['title']} ({request_payload['book_metadata']['year']})")
    
    start_time = time.time()
    
    try:
        # Execute with just the request_data portion
        result = kickoff(request_payload)
        
        elapsed_time = time.time() - start_time
        
        print_header("Execution Complete", "✅")
        print(f"Time elapsed: {elapsed_time:.2f} seconds")
        
        # Display results
        print_header("Results", "📊")
        
        if isinstance(result, dict):
            # Save full results
            output_file = f"book_ingestion_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"💾 Full results saved to: {output_file}")
            
            # Display summary
            if 'pages_processed' in result:
                print(f"\nPages processed: {result['pages_processed']}")
            
            if 'pages' in result and isinstance(result['pages'], list):
                print(f"\nFirst page sample:")
                if result['pages']:
                    first_page = result['pages'][0]
                    print(f"  Page number: {first_page.get('page_number', 'N/A')}")
                    print(f"  Confidence: {first_page.get('confidence', 'N/A')}")
                    if 'text' in first_page:
                        preview = first_page['text'][:200] + "..." if len(first_page['text']) > 200 else first_page['text']
                        print(f"  Text preview: {preview}")
            
            # Check for errors
            if 'errors' in result:
                print(f"\n⚠️  Errors encountered: {len(result['errors'])}")
                for error in result['errors'][:3]:
                    print(f"  - {error}")
        else:
            print(f"Result type: {type(result)}")
            print(f"Result: {str(result)[:500]}...")
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        print_header("Error During Execution", "❌")
        print(f"Time elapsed before error: {elapsed_time:.2f} seconds")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🏁 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """Main entry point."""
    # Check Python version
    import sys
    if sys.version_info < (3, 10):
        print("⚠️  Warning: Python 3.10+ is required for CrewAI")
        print(f"Current version: {sys.version}")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    test_book_ingestion()

if __name__ == "__main__":
    main()