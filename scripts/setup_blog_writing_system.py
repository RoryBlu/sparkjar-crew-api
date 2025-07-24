#!/usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

"""
Setup script for the blog writing system.
This script:
1. Creates skill_modules tables (requires manual SQL execution)
2. Seeds all necessary schemas
3. Stores blog writing knowledge for synth_class 24

Run this to set up the complete blog writing foundation.
"""
import asyncio
import subprocess
import sys
from pathlib import Path

# Add src to Python path

def print_section(title):
    """Print a section header"""
    logger.info(f"\n{'='*60}")
    logger.info(f"  {title}")
    logger.info(f"{'='*60}\n")

async def main():
    """Main setup process"""
    
    print_section("Blog Writing System Setup")
    
    # Step 1: Database tables
    print_section("Step 1: Database Tables")
    logger.info("📝 SQL migration file created at: migrations/add_skill_modules_tables.sql")
    logger.info("⚠️  Please run this SQL manually in your database:")
    logger.info("   - Creates skill_modules table")
    logger.info("   - Creates synth_skill_subscriptions table")
    logger.info("\nPress Enter when you've run the SQL migration...")
    input()
    
    # Step 2: Seed schemas
    print_section("Step 2: Seeding Object Schemas")
    logger.info("🚀 Running seed_blog_writing_schemas.py...")
    
    try:
        result = subprocess.run(
            [sys.executable, "scripts/seed_blog_writing_schemas.py"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(f"Warnings: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error seeding schemas: {e}")
        logger.info(f"Output: {e.stdout}")
        logger.error(f"Error: {e.stderr}")
        return
    
    # Step 3: Store blog writing knowledge
    print_section("Step 3: Storing Blog Writing Knowledge")
    logger.info("📚 This will create the blog writing knowledge base for synth_class 24")
    logger.info("⚠️  Note: The store_blog_skill_synth_class.py script needs to be run manually")
    logger.info("   as it requires no client_id (architectural update needed)")
    logger.info("\nTo run it:")
    logger.info("python services/memory-service/scripts/store_blog_skill_synth_class.py")
    
    # Summary
    print_section("Setup Summary")
    logger.info("✅ Database migration SQL created (manual execution required)")
    logger.info("✅ Object schemas seeded (if successful above)")
    logger.info("📋 Next steps:")
    logger.info("   1. Ensure database migration was applied")
    logger.info("   2. Run the blog skill storage script")
    logger.info("   3. Create a test synth to verify access")
    logger.info("   4. Test hierarchical memory retrieval")
    
    logger.info("\n🎯 Blog Writing System setup process complete!")
    logger.info("   The foundation is ready for storing and retrieving")
    logger.info("   blog writing knowledge through hierarchical memory.")

if __name__ == "__main__":
    asyncio.run(main())