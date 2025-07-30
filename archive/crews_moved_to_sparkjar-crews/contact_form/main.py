#!/usr/bin/env python3
"""
Standalone execution entry point for Contact Form Crew.
Allows direct CLI testing without the full API infrastructure.

Usage:
    python main.py
    python main.py --name "John Doe" --email "john@example.com" --message "Your message"
    python main.py --test  # Uses test JSON file
"""

import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

# Add parent directory to path for imports

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the crew's kickoff function
from crews.contact_form.crew import kickoff

def load_test_data():
    """Load test data from fixtures."""
    test_file = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "tests/fixtures/test_contact_form_api.json"
    if test_file.exists():
        with open(test_file, 'r') as f:
            return json.load(f)
    return None

def main():
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(description='Run Contact Form Crew')
    parser.add_argument('--test', action='store_true', help='Use test data from JSON file')
    parser.add_argument('--name', type=str, help='Contact name')
    parser.add_argument('--email', type=str, help='Contact email')
    parser.add_argument('--company', type=str, help='Company name')
    parser.add_argument('--phone', type=str, help='Phone number')
    parser.add_argument('--message', type=str, help='Inquiry message')
    parser.add_argument('--inquiry-type', type=str, default='contact_form',
                       choices=['contact_form', 'demo_request', 'early_access'],
                       help='Type of inquiry')
    parser.add_argument('--source-site', type=str, default='n3xusiq.com',
                       choices=['n3xusiq.com', 'n3xusiq.mx'],
                       help='Source website')
    parser.add_argument('--source-locale', type=str, default='en_US',
                       choices=['en_US', 'es_MX'],
                       help='Source locale')
    
    args = parser.parse_args()
    
    # Load test data if requested
    if args.test:
        test_data = load_test_data()
        if test_data:
            logger.info("📄 Using test data from JSON file")
            # Remove API key as we don't need it for direct execution
            test_data.pop('api_key', None)
            inputs = test_data
        else:
            logger.info("❌ Test JSON file not found")
            sys.exit(1)
    else:
        # Build inputs from command line arguments
        if not args.name or not args.email or not args.message:
            logger.info("❌ Error: --name, --email, and --message are required (unless using --test)")
            parser.print_help()
            sys.exit(1)
        
        inputs = {
            'inquiry_type': args.inquiry_type,
            'contact': {
                'name': args.name,
                'email': args.email,
                'company': args.company,
                'phone': args.phone
            },
            'message': args.message,
            'metadata': {
                'source_site': args.source_site,
                'source_locale': args.source_locale,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'user_agent': 'CLI/main.py',
                'ip_address': '127.0.0.1',
                'referrer': 'direct'
            }
        }
        
        # Remove None values from contact
        inputs['contact'] = {k: v for k, v in inputs['contact'].items() if v is not None}
    
    # Add required fields for crew execution
    inputs['job_id'] = 'standalone-test'
    inputs['client_user_id'] = 'test-client-id'  # This would normally come from API key lookup
    
    logger.info("\n🚀 Starting Contact Form Crew")
    logger.info("=" * 50)
    logger.info(f"Processing inquiry from: {inputs['contact'].get('name')} ({inputs['contact'].get('email')})")
    logger.info(f"Type: {inputs['inquiry_type']}")
    logger.info(f"Message preview: {inputs['message'][:100]}...")
    logger.info("=" * 50 + "\n")
    
    try:
        # Execute the crew
        result = kickoff(inputs)
        
        logger.info("\n✅ Crew execution completed!")
        logger.info("=" * 50)
        
        # Display results
        if isinstance(result, dict):
            logger.info(f"Status: {result.get('status', 'unknown')}")
            logger.info(f"Processing time: {result.get('processing_time_seconds', 0):.2f} seconds")
            
            # Show analysis results
            if 'analysis' in result:
                analysis = result['analysis']
                logger.info(f"\n📊 Analysis Results:")
                logger.info(f"  - Intent: {analysis.get('primary_intent')}")
                logger.info(f"  - Urgency: {analysis.get('urgency_level')}")
                logger.info(f"  - Sentiment: {analysis.get('sentiment')}")
                logger.info(f"  - Key Topics: {', '.join(analysis.get('key_topics', []))}")
                logger.info(f"  - Priority: {analysis.get('follow_up_priority')}/10")
            
            # Show storage results
            if 'contact_entity' in result:
                entity = result['contact_entity']
                logger.info(f"\n💾 Memory Storage:")
                logger.info(f"  - Entity ID: {entity.get('entity_id')}")
                logger.info(f"  - New Contact: {entity.get('is_new_contact')}")
                logger.info(f"  - Previous Interactions: {entity.get('previous_interactions')}")
            
            if 'odoo_record' in result:
                odoo = result['odoo_record']
                if odoo.get('lead_id'):
                    logger.info(f"\n🏢 Odoo CRM:")
                    logger.info(f"  - Lead ID: {odoo.get('lead_id')}")
                    logger.info(f"  - Contact ID: {odoo.get('contact_id')}")
                    logger.info(f"  - URL: {odoo.get('record_url')}")
                elif odoo.get('error'):
                    logger.info(f"\n⚠️  Odoo Integration: {odoo.get('error')}")
            
            # Show suggested response
            if 'suggested_response' in result:
                logger.info(f"\n📧 Suggested Response:")
                logger.info("-" * 40)
                logger.info(result['suggested_response'])
                logger.info("-" * 40)
            
            # Show next actions
            if 'next_actions' in result:
                logger.info(f"\n📋 Next Actions:")
                for i, action in enumerate(result['next_actions'], 1):
                    logger.info(f"  {i}. {action}")
            
            # Show any errors
            if 'errors' in result and result['errors']:
                logger.info(f"\n⚠️  Warnings/Errors:")
                for error in result['errors']:
                    logger.info(f"  - {error}")
        else:
            logger.info(f"Result: {result}")
            
    except Exception as e:
        logger.info(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()