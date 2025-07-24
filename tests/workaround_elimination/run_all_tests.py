#!/usr/bin/env python3
"""
Run all workaround elimination tests.

Usage:
    python run_all_tests.py              # Run all tests
    python run_all_tests.py -v           # Verbose output
    python run_all_tests.py -k logging   # Run only logging tests
    python run_all_tests.py --cov        # With coverage report
"""

import sys
import os
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
# REMOVED: sys.path.insert(0, str(project_root))

def main():
    """Run the test suite."""
    # Base test arguments
    args = [
        # Test discovery
        str(Path(__file__).parent),
        
        # Output options
        "-v",  # Verbose
        "--tb=short",  # Shorter traceback format
        
        # Test markers
        "-m", "not integration",  # Skip integration tests by default
    ]
    
    # Add any command line arguments
    args.extend(sys.argv[1:])
    
    # Add coverage if requested
    if "--cov" in args:
        args.extend([
            "--cov=shared",
            "--cov=services",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    # Run tests
    print("=" * 80)
    print("Running Workaround Elimination Test Suite")
    print("=" * 80)
    
    exit_code = pytest.main(args)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())