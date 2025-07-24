#!/usr/bin/env python3
"""
Store client secrets in the database.

Usage:
    python scripts/store_client_secret.py --client-id vervelyn_publishing --secret-key database_url --secret-value "postgresql://..."
"""

import os
import sys
import argparse
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.utils.secret_manager import SecretManager
from src.utils.crew_logger import setup_logging

logger = setup_logging(__name__)


def main():
    parser = argparse.ArgumentParser(description="Store client secrets in database")
    parser.add_argument("--client-id", required=True, help="Client ID")
    parser.add_argument("--secret-key", required=True, help="Secret key name")
    parser.add_argument("--secret-value", required=True, help="Secret value")
    parser.add_argument("--actor-type", help="Optional actor type")
    parser.add_argument("--actor-id", help="Optional actor ID")
    
    args = parser.parse_args()
    
    logger.info(f"Storing secret '{args.secret_key}' for client '{args.client_id}'")
    
    success = SecretManager.set_client_secret(
        client_id=args.client_id,
        secret_name=args.secret_key,
        secret_value=args.secret_value,
        actor_type=args.actor_type,
        actor_id=args.actor_id
    )
    
    if success:
        logger.info("✅ Secret stored successfully!")
        
        # Verify it can be retrieved
        retrieved = SecretManager.get_client_secret(args.client_id, args.secret_key)
        if retrieved:
            logger.info("✅ Secret verified - can be retrieved successfully")
        else:
            logger.error("❌ Failed to retrieve secret after storing")
    else:
        logger.error("❌ Failed to store secret")
        sys.exit(1)


if __name__ == "__main__":
    main()