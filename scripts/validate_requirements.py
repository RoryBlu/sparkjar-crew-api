#!/usr/bin/env python3
"""
Validate the new requirements file.
"""

import subprocess
import sys
import tempfile
import os
import shutil

def test_requirements_in_venv(req_file):
    """Test requirements in a fresh virtual environment."""
    print(f"\n🧪 Testing {req_file} in fresh virtual environment...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = os.path.join(tmpdir, 'test_venv')
        
        # Create virtual environment
        print("Creating virtual environment...")
        result = subprocess.run(
            [sys.executable, '-m', 'venv', venv_path],
            capture_output=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to create venv: {result.stderr.decode()}")
            return False
        
        # Get pip and python paths
        if sys.platform == 'win32':
            pip_path = os.path.join(venv_path, 'Scripts', 'pip')
            python_path = os.path.join(venv_path, 'Scripts', 'python')
        else:
            pip_path = os.path.join(venv_path, 'bin', 'pip')
            python_path = os.path.join(venv_path, 'bin', 'python')
        
        # Upgrade pip
        print("Upgrading pip...")
        subprocess.run([pip_path, 'install', '--upgrade', 'pip'], capture_output=True)
        
        # Install requirements
        print(f"Installing requirements from {req_file}...")
        result = subprocess.run(
            [pip_path, 'install', '-r', req_file],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Installation failed!")
            print("\nError output:")
            print(result.stderr)
            
            # Try to identify the problematic package
            if 'error' in result.stderr.lower():
                lines = result.stderr.split('\n')
                for line in lines:
                    if 'error' in line.lower() or 'failed' in line.lower():
                        print(f"  → {line}")
            
            return False
        
        print("✅ Installation successful!")
        
        # Test critical imports
        print("\n🔍 Testing critical imports:")
        test_imports = [
            ("CrewAI", "import crewai; print(f'CrewAI version: {crewai.__version__}')"),
            ("FastAPI", "import fastapi; print(f'FastAPI version: {fastapi.__version__}')"),
            ("SQLAlchemy", "import sqlalchemy; print(f'SQLAlchemy version: {sqlalchemy.__version__}')"),
            ("Pydantic", "import pydantic; print(f'Pydantic version: {pydantic.__version__}')"),
            ("ChromaDB", "import chromadb; print('ChromaDB imported successfully')"),
            ("Redis", "import redis; print('Redis imported successfully')"),
            ("OpenAI", "import openai; print(f'OpenAI version: {openai.__version__}')"),
        ]
        
        all_passed = True
        for name, test_code in test_imports:
            result = subprocess.run(
                [python_path, '-c', test_code],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"  ✅ {name}: {result.stdout.strip()}")
            else:
                print(f"  ❌ {name}: {result.stderr.strip()}")
                all_passed = False
        
        # Check for ChromaDB server issue
        print("\n🎨 Checking ChromaDB configuration:")
        chromadb_check = subprocess.run(
            [python_path, '-c', """
import chromadb
print(f"ChromaDB version: {chromadb.__version__}")
# Check if it's client mode
if hasattr(chromadb, 'HttpClient'):
    print("✅ HttpClient available - can connect to remote ChromaDB")
if hasattr(chromadb, 'PersistentClient'):
    print("⚠️  PersistentClient available - might start local server")
"""],
            capture_output=True,
            text=True
        )
        if chromadb_check.returncode == 0:
            print(chromadb_check.stdout)
        
        # List installed packages with versions
        print("\n📦 Key installed packages:")
        list_result = subprocess.run(
            [pip_path, 'list'],
            capture_output=True,
            text=True
        )
        if list_result.returncode == 0:
            lines = list_result.stdout.split('\n')
            for line in lines:
                if any(pkg in line.lower() for pkg in ['crewai', 'chromadb', 'pydantic', 'fastapi', 'openai']):
                    print(f"  {line}")
        
        return all_passed

def check_dependency_conflicts(req_file):
    """Check for dependency conflicts."""
    print("\n🔍 Checking for dependency conflicts...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use pip-compile to resolve dependencies
        print("Resolving dependencies...")
        compile_result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--dry-run', '-r', req_file],
            capture_output=True,
            text=True
        )
        
        if 'conflict' in compile_result.stderr.lower():
            print("⚠️  Potential conflicts detected:")
            lines = compile_result.stderr.split('\n')
            for line in lines:
                if 'conflict' in line.lower():
                    print(f"  {line}")
        else:
            print("✅ No obvious conflicts detected")

def main():
    print("🚀 Validating New Requirements")
    print("=" * 60)
    
    req_file = 'requirements_new.txt'
    if not os.path.exists(req_file):
        print(f"❌ {req_file} not found!")
        return
    
    # First check for conflicts
    check_dependency_conflicts(req_file)
    
    # Then test installation
    success = test_requirements_in_venv(req_file)
    
    if success:
        print("\n✅ SUCCESS! The requirements file is valid.")
        print("\n🎯 Next steps:")
        print("1. Back up current requirements.txt: cp requirements.txt requirements_old.txt")
        print("2. Replace with new version: cp requirements_new.txt requirements.txt")
        print("3. Create fresh virtual environment")
        print("4. Test your application")
    else:
        print("\n❌ FAILED! The requirements file has issues.")
        print("\n🔧 Troubleshooting:")
        print("1. Check the error messages above")
        print("2. Try installing packages one by one to identify conflicts")
        print("3. Consider using pip-tools for better dependency resolution")

if __name__ == "__main__":
    main()