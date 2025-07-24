#!/usr/bin/env python3
"""
Test all imports and identify dependency conflicts.
"""

import sys
import subprocess
import importlib
import importlib.metadata
from collections import defaultdict

# List of all packages to test
PACKAGES_TO_TEST = [
    # Core
    ('crewai', ['crewai']),
    ('crewai-tools', ['crewai_tools']),
    
    # API Framework
    ('fastapi', ['fastapi']),
    ('uvicorn', ['uvicorn']),
    ('python-multipart', ['multipart']),
    
    # Database
    ('sqlalchemy', ['sqlalchemy']),
    ('psycopg2-binary', ['psycopg2']),
    ('alembic', ['alembic']),
    
    # Auth
    ('python-jose', ['jose']),
    ('passlib', ['passlib']),
    
    # Vector DB
    ('chromadb', ['chromadb']),
    
    # LLM
    ('openai', ['openai']),
    ('tiktoken', ['tiktoken']),
    
    # Utilities
    ('python-dotenv', ['dotenv']),
    ('pydantic', ['pydantic']),
    ('pyyaml', ['yaml']),
    ('httpx', ['httpx']),
    ('requests', ['requests']),
    
    # Testing
    ('pytest', ['pytest']),
    ('pytest-asyncio', ['pytest_asyncio']),
    ('pytest-mock', ['pytest_mock']),
    
    # Google
    ('google-api-python-client', ['googleapiclient']),
    ('google-auth-httplib2', ['google_auth_httplib2']),
    ('google-auth-oauthlib', ['google_auth_oauthlib']),
    
    # OCR
    ('paddlepaddle', ['paddle']),
    ('paddleocr', ['paddleocr']),
    ('Pillow', ['PIL']),
    
    # Docs
    ('pdfplumber', ['pdfplumber']),
    ('pypdf', ['pypdf']),
    
    # Email
    ('sendgrid', ['sendgrid']),
    
    # Chat
    ('redis', ['redis']),
    ('structlog', ['structlog']),
    ('prometheus-client', ['prometheus_client']),
    ('cachetools', ['cachetools']),
]

def check_package_version(package_name):
    """Check installed version of a package."""
    try:
        version = importlib.metadata.version(package_name)
        return version
    except importlib.metadata.PackageNotFoundError:
        return None

def test_import(module_name):
    """Test if a module can be imported."""
    try:
        importlib.import_module(module_name)
        return True, None
    except Exception as e:
        return False, str(e)

def get_package_dependencies(package_name):
    """Get dependencies of a package."""
    try:
        metadata = importlib.metadata.metadata(package_name)
        requires = metadata.get_all('Requires-Dist') or []
        # Filter out conditional dependencies
        deps = []
        for req in requires:
            if ';' in req:
                # Skip conditional dependencies for now
                base_req = req.split(';')[0].strip()
            else:
                base_req = req.strip()
            if base_req:
                deps.append(base_req)
        return deps
    except:
        return []

def main():
    print("🔍 Testing Requirements and Dependencies")
    print("=" * 60)
    
    # First, check what's actually installed
    print("\n📦 Checking installed packages:")
    missing_packages = []
    installed_packages = {}
    
    for package_name, import_names in PACKAGES_TO_TEST:
        version = check_package_version(package_name)
        if version:
            installed_packages[package_name] = version
            print(f"✅ {package_name}=={version}")
        else:
            missing_packages.append(package_name)
            print(f"❌ {package_name} - NOT INSTALLED")
    
    # Test imports
    print("\n🧪 Testing imports:")
    import_errors = []
    
    for package_name, import_names in PACKAGES_TO_TEST:
        if package_name in installed_packages:
            for import_name in import_names:
                success, error = test_import(import_name)
                if success:
                    print(f"✅ import {import_name}")
                else:
                    import_errors.append((import_name, error))
                    print(f"❌ import {import_name} - {error}")
    
    # Check for dependency conflicts
    print("\n🔗 Checking dependencies:")
    dependency_map = defaultdict(set)
    
    for package_name in installed_packages:
        deps = get_package_dependencies(package_name)
        for dep in deps:
            dependency_map[package_name].add(dep)
            print(f"  {package_name} → {dep}")
    
    # Check CrewAI specific issues
    print("\n🚢 CrewAI Analysis:")
    if 'crewai' in installed_packages:
        crewai_version = installed_packages['crewai']
        print(f"Current CrewAI version: {crewai_version}")
        print("Latest CrewAI version: 0.148.0")
        
        # Check CrewAI dependencies
        crewai_deps = get_package_dependencies('crewai')
        print("\nCrewAI dependencies:")
        for dep in crewai_deps:
            print(f"  - {dep}")
    
    # Check ChromaDB client/server issue
    print("\n🎨 ChromaDB Analysis:")
    if 'chromadb' in installed_packages:
        chromadb_version = installed_packages['chromadb']
        print(f"ChromaDB version: {chromadb_version}")
        print("Note: ChromaDB should be used as a client, not server")
        
        # Test ChromaDB import
        try:
            import chromadb
            print("✅ ChromaDB client import successful")
            
            # Check if it's trying to start a server
            if hasattr(chromadb, 'HttpClient'):
                print("✅ ChromaDB HttpClient available (correct for client usage)")
            if hasattr(chromadb, 'PersistentClient'):
                print("⚠️  ChromaDB PersistentClient available (might start local server)")
        except Exception as e:
            print(f"❌ ChromaDB import error: {e}")
    
    # Summary
    print("\n📊 Summary:")
    print(f"Total packages: {len(PACKAGES_TO_TEST)}")
    print(f"Installed: {len(installed_packages)}")
    print(f"Missing: {len(missing_packages)}")
    print(f"Import errors: {len(import_errors)}")
    
    if missing_packages:
        print("\n❌ Missing packages:")
        for pkg in missing_packages:
            print(f"  - {pkg}")
    
    if import_errors:
        print("\n❌ Import errors:")
        for module, error in import_errors:
            print(f"  - {module}: {error}")
    
    # Write detailed report
    with open('requirements_report.txt', 'w') as f:
        f.write("Requirements Analysis Report\n")
        f.write("==========================\n\n")
        
        f.write("Installed Packages:\n")
        for pkg, ver in installed_packages.items():
            f.write(f"  {pkg}=={ver}\n")
        
        f.write("\nMissing Packages:\n")
        for pkg in missing_packages:
            f.write(f"  {pkg}\n")
        
        f.write("\nImport Errors:\n")
        for module, error in import_errors:
            f.write(f"  {module}: {error}\n")
        
        f.write("\nDependency Map:\n")
        for pkg, deps in dependency_map.items():
            f.write(f"\n{pkg}:\n")
            for dep in deps:
                f.write(f"  → {dep}\n")
    
    print("\n💾 Detailed report saved to: requirements_report.txt")

if __name__ == "__main__":
    main()