#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""
Standalone execution entry point for Entity Research Crew.
Allows direct CLI testing without the full API infrastructure.

Usage:
    python main.py "OpenAI" --entity-domain "technology"
    python main.py "Tesla" --entity-domain "automotive" --detailed
    python main.py --test  # Uses sample test entity
"""

import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the crew builder
from crews.entity_research_crew.crew import build_crew

def load_test_data() -> Dict[str, Any]:
    """Load sample test data for entity research."""
    return {
        "entity_name": "SparkJAR Technologies",
        "entity_domain": "AI/automation",
        "client_user_id": "test-client-123",
        "job_id": "standalone-test"
    }

def main() -> None:
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(
        description='Run Entity Research Crew',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Research a technology company
    python main.py "OpenAI" --entity-domain "technology"
    
    # Research with detailed output
    python main.py "Tesla" --entity-domain "automotive" --detailed
    
    # Use test data
    python main.py --test
    
    # Save results to file
    python main.py "Microsoft" --output results.json
        """
    )
    
    # Positional argument for entity name (optional if using --test)
    parser.add_argument('entity_name', nargs='?', 
                       help='Name of the entity to research')
    
    # Optional arguments
    parser.add_argument('--entity-domain', '--domain', type=str, default='general',
                       help='Domain or industry of the entity (default: general)')
    parser.add_argument('--test', action='store_true',
                       help='Use sample test data')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed research output')
    parser.add_argument('--output', type=str,
                       help='Save results to JSON file')
    parser.add_argument('--client-id', type=str, default='test-client-123',
                       help='Client ID for tracking (default: test-client-123)')
    parser.add_argument('--job-id', type=str, default='standalone-test',
                       help='Job ID for tracking (default: standalone-test)')
    
    args = parser.parse_args()
    
    # Determine entity to research
    if args.test:
        logger.info("📄 Using sample test data")
        inputs = load_test_data()
    elif args.entity_name:
        inputs = {
            "entity_name": args.entity_name,
            "entity_domain": args.entity_domain,
            "client_user_id": args.client_id,
            "job_id": args.job_id
        }
    else:
        logger.error("❌ Error: Must provide entity_name or use --test")
        parser.print_help()
        sys.exit(1)
    
    logger.info("\n🚀 Starting Entity Research Crew")
    logger.info("=" * 50)
    logger.info(f"Entity: {inputs['entity_name']}")
    logger.info(f"Domain: {inputs['entity_domain']}")
    logger.info(f"Client ID: {inputs['client_user_id']}")
    logger.info(f"Job ID: {inputs['job_id']}")
    logger.info("=" * 50 + "\n")
    
    try:
        # Build and execute the crew
        crew = build_crew()
        result = crew.kickoff(inputs)
        
        logger.info("\n✅ Research completed!")
        logger.info("=" * 50)
        
        # Process and display results
        if args.detailed or os.getenv('VERBOSE', '').lower() == 'true':
            # Show full detailed output
            logger.info("\n📋 Detailed Research Results:")
            logger.info("-" * 40)
            if isinstance(result, dict):
                logger.info(json.dumps(result, indent=2))
            else:
                logger.info(result)
            logger.info("-" * 40)
        else:
            # Show summary output
            logger.info("\n📊 Research Summary:")
            if isinstance(result, dict):
                # Extract key information from result
                if 'summary' in result:
                    logger.info(f"\n📄 Summary:")
                    logger.info(result['summary'])
                
                if 'key_facts' in result:
                    logger.info(f"\n🔑 Key Facts:")
                    for fact in result['key_facts']:
                        logger.info(f"  • {fact}")
                
                if 'products' in result:
                    logger.info(f"\n📦 Products/Services:")
                    for product in result['products']:
                        logger.info(f"  • {product}")
                
                if 'competitors' in result:
                    logger.info(f"\n🏆 Competitors:")
                    for competitor in result['competitors']:
                        logger.info(f"  • {competitor}")
                
                if 'recent_news' in result:
                    logger.info(f"\n📰 Recent News:")
                    for news in result['recent_news'][:3]:  # Show top 3
                        logger.info(f"  • {news}")
            else:
                # Fallback for string results
                lines = str(result).split('\n')
                for line in lines[:20]:  # Show first 20 lines
                    logger.info(line)
                if len(lines) > 20:
                    logger.info(f"\n... ({len(lines) - 20} more lines)")
        
        # Save to file if requested
        if args.output:
            output_data = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "inputs": inputs,
                "result": result if isinstance(result, dict) else str(result)
            }
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"\n💾 Results saved to: {args.output}")
            
    except Exception as e:
        logger.error(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()