#!/usr/bin/env python3
"""
Database connection test suite.
Tests basic database connectivity and simple queries.
"""
import asyncio
import os
import sys

import pytest

pytestmark = pytest.mark.integration

# Add project root to path

from services.crew_api.src.database.connection import get_direct_session

class TestDatabaseConnection:
    """Test database connection functionality."""

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test basic database connection."""
        print("Testing direct connection...")
        
        try:
            async with get_direct_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                print(f"✅ Connection successful! Result: {row}")
                assert row is not None
                assert row[0] == 1
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            pytest.fail(f"Database connection test failed: {e}")

    @pytest.mark.asyncio
    async def test_database_version(self):
        """Test database version query."""
        try:
            async with get_direct_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT version()"))
                version = result.fetchone()
                print(f"Database version: {version[0] if version else 'Unknown'}")
                assert version is not None
        except Exception as e:
            pytest.fail(f"Database version test failed: {e}")

# Keep the original standalone functionality for direct execution
async def simple_test():
    """Simple connection test for standalone execution."""
    print("Testing direct connection...")
    
    try:
        async with get_direct_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ Connection successful! Result: {row}")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_test())
    sys.exit(0 if success else 1)
