#!/usr/bin/env python3
"""Test that all imports work correctly."""

import sys
import os
from pathlib import Path

# Add crew-api src to path
crew_api_src = str(Path(__file__).parent / "services" / "crew-api" / "src")
sys.path.insert(0, crew_api_src)
sys.path.insert(0, str(Path(__file__).parent))

print("🧪 Testing Imports")
print("=" * 70)

# Load environment from .env file
if os.path.exists('.env'):
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

try:
    print("✅ Testing CrewAI...")
    import crewai
    print(f"   CrewAI version: {crewai.__version__}")

    print("✅ Testing Google API client...")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    print("   Google API client imported successfully")

    print("✅ Testing database modules...")
    import sqlalchemy
    import psycopg2
    import pgvector
    print(f"   SQLAlchemy: {sqlalchemy.__version__}")

    print("✅ Testing ChromaDB client...")
    import chromadb
    print(f"   ChromaDB: {chromadb.__version__}")

    print("✅ Testing FastAPI...")
    import fastapi
    import pydantic
    print(f"   FastAPI: {fastapi.__version__}")
    print(f"   Pydantic: {pydantic.__version__}")

    print("✅ Testing crew modules...")
    try:
        from crews.book_ingestion_crew.crew import kickoff
        print("   Book ingestion crew imported successfully")
    except Exception as e:
        print(f"   ⚠️  Book ingestion crew import issue: {e}")

    try:
        from tools.google_drive_tool import GoogleDriveTool
        print("   Google Drive tool imported successfully")
    except Exception as e:
        print(f"   ⚠️  Google Drive tool import issue: {e}")

    print("\n🎉 All core imports successful!")

except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()

print(f"\n🏁 Import test completed")