#!/usr/bin/env python3
"""
Run translation for Vervelyn's book.
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment variables
os.environ["DATABASE_URL"] = "postgresql://postgres.clbzzkvjvcmcqfyosoqj:vD4bVQ5YLJ6WqRRX@aws-0-us-east-2.pooler.supabase.com:5432/postgres"
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")

from crews.book_translation_crew.main import kickoff

# Vervelyn's book information
inputs = {
    "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
    "actor_type": "client",
    "actor_id": "1d1c2154-242b-4f49-9ca8-e57129ddc823",
    "book_key": "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO",
    "target_language": "en"
}

print("Starting translation for Vervelyn's book...")
print(f"Book: {inputs['book_key']}")
print(f"Target language: {inputs['target_language']}")
print()

result = kickoff(inputs)
print(f"\nTranslation result: {result}")