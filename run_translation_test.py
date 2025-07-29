#!/usr/bin/env python3
"""
Run book translation crew test directly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.crews.book_translation_crew.main import kickoff

# Vervelyn book information from VERVELYN_CLIENT_INFO.md
inputs = {
    "client_user_id": "3a411a30-1653-4caf-acee-de257ff50e36",
    "actor_type": "client",
    "actor_id": "1d1c2154-242b-4f49-9ca8-e57129ddc823",
    "book_key": "https://drive.google.com/drive/u/0/folders/1HFDpMUHT0wjVWdWB9XIUMYavmq23I4JO",
    "target_language": "en"
}

print("Starting book translation for Vervelyn...")
print(f"Book key: {inputs['book_key']}")
print(f"Target language: {inputs['target_language']}")

try:
    result = kickoff(inputs)
    print("\nTranslation completed!")
    print(f"Result: {result}")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()