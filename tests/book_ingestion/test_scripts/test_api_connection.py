#!/usr/bin/env python
"""Test database connection using API's config."""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services/crew-api/src'))

import asyncio
from database.connection import check_database_connection, get_direct_session
from database.models import ClientUsers, ClientSecrets
from sqlalchemy import select

async def test_connections():
    """Test both main DB and client DB connections."""
    
    # Test main database connection
    print("Testing main database connection...")
    can_connect = await check_database_connection()
    print(f"Main DB connection: {'✅ Success' if can_connect else '❌ Failed'}")
    
    if can_connect:
        # Get client database URL from secrets
        print("\nFetching client database URL from secrets...")
        async with get_direct_session() as session:
            # Get user
            result = await session.execute(
                select(ClientUsers).filter_by(id="3a411a30-1653-4caf-acee-de257ff50e36")
            )
            user = result.scalar_one_or_none()
            
            if user:
                print(f"Found user: {user.full_name}")
                
                # Get database URL secret
                secrets_result = await session.execute(
                    select(ClientSecrets).filter_by(
                        client_id=user.clients_id,
                        secret_key="database_url"
                    )
                )
                secret = secrets_result.scalar_one_or_none()
                
                if secret:
                    print("Found client database URL in secrets")
                    # Check the value
                    db_url = secret.secret_value
                    print(f"URL length: {len(db_url)}")
                    print(f"URL starts with: {db_url[:30]}...")
                    print(f"URL ends with: ...{db_url[-30:]}")
                    
                    # Check if it's the expected format
                    if "vervelyn" in db_url:
                        print("✅ URL contains 'vervelyn' - looks like client-specific DB")
                    else:
                        print("⚠️  URL doesn't contain 'vervelyn' - might be wrong URL")
                else:
                    print("❌ No database_url secret found for client")
            else:
                print("❌ User not found")

if __name__ == "__main__":
    asyncio.run(test_connections())