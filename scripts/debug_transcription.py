#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""Debug the transcription process."""
import sys
import os

from .tools.google_drive_tool import GoogleDriveTool
import json

# Test parameters
folder_path = "0AM0PEUhIEQFUUk9PVA/Vervelyn/Castor Gonzalez/book 1"
client_user_id = "587f8370-825f-4f0c-8846-2e6d70782989"

logger.info("=== TESTING GOOGLE DRIVE IMAGE LISTING ===")

# Initialize tool
drive_tool = GoogleDriveTool()

# List images
result = drive_tool._run(
    folder_path=folder_path,
    client_user_id=client_user_id,
    file_types=["image/jpeg", "image/png", "image/jpg", "image/webp"],
    download=False
)

logger.info(f"\nRaw result: {result}")

try:
    data = json.loads(result) if isinstance(result, str) else result
    if data.get('status') == 'success':
        files = data.get('files', [])
        logger.info(f"\nFound {len(files)} image files:")
        for i, file in enumerate(files):
            logger.info(f"{i+1}. {file['name']} - {file['id']} - {file.get('size', 'N/A')} bytes")
    else:
        logger.error(f"Error: {data.get('error')}")
except Exception as e:
    logger.error(f"Failed to parse result: {e}")

logger.info("\n=== EXPECTED TRANSCRIPTION OUTPUT FORMAT ===")
expected = {
    "total_pages": 3,
    "transcriptions": {
        "IMG_5610.jpg": "Transcribed Spanish text from page 1...",
        "IMG_5611.jpg": "Transcribed Spanish text from page 2...",
        "IMG_5612.jpg": "Transcribed Spanish text from page 3..."
    },
    "unclear_sections": ["Some unclear handwriting on page 2"],
    "quality_summary": "Good quality transcription with 95% confidence"
}
logger.info(json.dumps(expected, indent=2))