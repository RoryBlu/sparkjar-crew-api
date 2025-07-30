#!/usr/bin/env python
"""
Main entry point for the Book Translation Crew.
This handles the kickoff function that integrates with the crew API.
"""

import logging
from typing import Dict, Any
from .crew import build_translation_crew

# Setup logging
logger = logging.getLogger(__name__)

def kickoff(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for book translation crew.
    
    Args:
        inputs: Dictionary containing:
            - client_user_id: Client ID
            - book_key: Book identifier
            - target_language: Target language code (default: 'en')
            
    Returns:
        Dictionary with translation results
    """
    try:
        logger.info(f"Starting book translation for book_key: {inputs.get('book_key')}")
        
        # Extract inputs
        client_user_id = inputs["client_user_id"]
        book_key = inputs["book_key"]
        target_language = inputs.get("target_language", "en")
        
        # Build the crew
        crew = build_translation_crew()
        
        # Prepare crew inputs
        crew_inputs = {
            "client_user_id": client_user_id,
            "book_key": book_key,
            "target_language": target_language,
            "source_language": "es"
        }
        
        # Execute the crew
        result = crew.kickoff(inputs=crew_inputs)
        
        return {
            "status": "completed",
            "book_key": book_key,
            "result": str(result),
            "target_language": target_language
        }
        
    except Exception as e:
        logger.error(f"Book translation failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "book_key": inputs.get("book_key", "")
        }

# Command line interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Book Translation Crew")
    # For Vervelyn books: client_user_id = 3a411a30-1653-4caf-acee-de257ff50e36
    # This maps to clients_id = 1d1c2154-242b-4f49-9ca8-e57129ddc823
    parser.add_argument("--client_user_id", required=True, help="Client user ID")
    parser.add_argument("--actor_type", required=True, help="Actor type")
    parser.add_argument("--actor_id", required=True, help="Actor ID")
    parser.add_argument("--book_key", required=True, help="Book key (e.g., Google Drive URL)")
    parser.add_argument("--target_language", default="en", help="Target language")
    
    args = parser.parse_args()
    
    inputs = {
        "client_user_id": args.client_user_id,
        "actor_type": args.actor_type,
        "actor_id": args.actor_id,
        "book_key": args.book_key,
        "target_language": args.target_language
    }
    
    result = kickoff(inputs)
    print(f"Translation result: {result}")