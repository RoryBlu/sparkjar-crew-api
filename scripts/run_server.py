#!/usr/bin/env python
"""
Wrapper to run the crew API server with proper imports.
This handles the monorepo structure for local development.
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run the main module
import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main.main())