#!/usr/bin/env python3
"""
Standalone execution entry point for Memory Import Crew.
Allows direct CLI testing without the full API infrastructure.

Usage:
    python main.py --data-file path/to/data.json
    python main.py --data '{"client_user_id": "test-client", "data": [...]}'
    python main.py --test  # Uses sample test data
"""

import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import logging
logger = logging.getLogger(__name__)

# Add parent directory to path for imports

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the crew's kickoff function
from crews.memory_import_crew.src.crew import kickoff

def load_test_data() -> Dict[str, Any]:
    """Load sample test data for memory import."""
    return {
        "client_user_id": "test-client-123",
        "job_id": "standalone-test",
        "data": [
            {
                "type": "person",
                "name": "Jane Smith",
                "email": "jane.smith@example.com",
                "role": "Marketing Director",
                "company": "Acme Corp",
                "notes": "Key decision maker for marketing technology purchases"
            },
            {
                "type": "company",
                "name": "Acme Corp",
                "industry": "Technology",
                "size": "500-1000 employees",
                "website": "https://acmecorp.example.com",
                "notes": "Enterprise software company specializing in CRM solutions"
            },
            {
                "type": "interaction",
                "date": "2025-01-08",
                "type_detail": "meeting",
                "participants": ["Jane Smith", "John Doe"],
                "topic": "Q1 Marketing Strategy",
                "notes": "Discussed implementing AI-powered marketing automation"
            }
        ]
    }

def main() -> None:
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(
        description='Run Memory Import Crew',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use test data
    python main.py --test
    
    # Import from JSON file
    python main.py --data-file import_data.json
    
    # Import from command line
    python main.py --data '{"client_user_id": "client-123", "data": [...]}'
    
    # Specify client ID with test data
    python main.py --test --client-id "my-client-id"
        """
    )
    
    parser.add_argument('--test', action='store_true', 
                       help='Use sample test data')
    parser.add_argument('--data-file', type=str,
                       help='Path to JSON file containing import data')
    parser.add_argument('--data', type=str,
                       help='Raw import data as JSON string')
    parser.add_argument('--client-id', type=str,
                       help='Override client_user_id in the data')
    parser.add_argument('--job-id', type=str, default='standalone-test',
                       help='Job ID for tracking (default: standalone-test)')
    
    args = parser.parse_args()
    
    # Determine data source
    if args.test:
        logger.info("📄 Using sample test data")
        inputs = load_test_data()
    elif args.data_file:
        logger.info(f"📁 Loading data from file: {args.data_file}")
        try:
            with open(args.data_file, 'r', encoding='utf-8') as f:
                inputs = json.load(f)
        except FileNotFoundError:
            logger.info(f"❌ Error: File '{args.data_file}' not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.info(f"❌ Error: Invalid JSON in file - {e}")
            sys.exit(1)
    elif args.data:
        logger.info("📝 Using data from command line")
        try:
            inputs = json.loads(args.data)
        except json.JSONDecodeError as e:
            logger.info(f"❌ Error: Invalid JSON string - {e}")
            sys.exit(1)
    else:
        logger.info("❌ Error: Must provide --test, --data-file, or --data")
        parser.print_help()
        sys.exit(1)
    
    # Override client_user_id if specified
    if args.client_id:
        inputs['client_user_id'] = args.client_id
    
    # Override job_id
    inputs['job_id'] = args.job_id
    
    # Validate required fields
    if 'client_user_id' not in inputs:
        logger.info("❌ Error: 'client_user_id' is required in the data")
        sys.exit(1)
    
    if 'data' not in inputs or not isinstance(inputs['data'], list):
        logger.info("❌ Error: 'data' field must be a list of items to import")
        sys.exit(1)
    
    logger.info("\n🚀 Starting Memory Import Crew")
    logger.info("=" * 50)
    logger.info(f"Client ID: {inputs['client_user_id']}")
    logger.info(f"Job ID: {inputs['job_id']}")
    logger.info(f"Items to import: {len(inputs['data'])}")
    logger.info("=" * 50 + "\n")
    
    try:
        # Execute the crew
        result = kickoff(inputs)
        
        logger.info("\n✅ Memory import completed!")
        logger.info("=" * 50)
        
        # Display results
        if isinstance(result, dict):
            # Show import summary
            if 'summary' in result:
                summary = result['summary']
                logger.info(f"\n📊 Import Summary:")
                logger.info(f"  - Total items: {summary.get('total_items', 0)}")
                logger.info(f"  - Successful: {summary.get('successful_imports', 0)}")
                logger.info(f"  - Failed: {summary.get('failed_imports', 0)}")
                logger.info(f"  - Processing time: {summary.get('processing_time_seconds', 0):.2f} seconds")
            
            # Show imported entities
            if 'entities' in result and result['entities']:
                logger.info(f"\n💾 Imported Entities:")
                for entity in result['entities'][:5]:  # Show first 5
                    logger.info(f"  - {entity.get('type')}: {entity.get('name')} (ID: {entity.get('entity_id')})")
                if len(result['entities']) > 5:
                    logger.info(f"  ... and {len(result['entities']) - 5} more")
            
            # Show any errors
            if 'errors' in result and result['errors']:
                logger.info(f"\n⚠️  Import Errors:")
                for error in result['errors']:
                    logger.info(f"  - {error}")
            
            # Show raw result in verbose mode
            if os.getenv('VERBOSE', '').lower() == 'true':
                logger.info(f"\n📋 Full Result:")
                logger.info(json.dumps(result, indent=2))
        else:
            # Fallback for non-dict results
            logger.info(f"Result: {result}")
            
    except Exception as e:
        logger.info(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()