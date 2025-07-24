#!/usr/bin/env python3
"""
Scan codebase for actual imports to understand what's really needed.
"""

import os
import re
from collections import defaultdict

def scan_python_files(directory):
    """Scan all Python files for imports."""
    imports = defaultdict(set)
    
    for root, dirs, files in os.walk(directory):
        # Skip venv and cache directories
        dirs[:] = [d for d in dirs if d not in ['venv', '.venv', '__pycache__', '.git']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        
                    # Find imports
                    import_pattern = r'^(?:from\s+(\S+)\s+import|import\s+(\S+))'
                    matches = re.findall(import_pattern, content, re.MULTILINE)
                    
                    for match in matches:
                        module = match[0] if match[0] else match[1]
                        # Get base module
                        base_module = module.split('.')[0]
                        
                        # Skip local imports
                        if not base_module.startswith(('src', '_', '.')):
                            imports[base_module].add(filepath)
                            
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return imports

def categorize_imports(imports):
    """Categorize imports by type."""
    categories = {
        'standard_lib': [],
        'crewai': [],
        'fastapi': [],
        'database': [],
        'auth': [],
        'google': [],
        'llm': [],
        'testing': [],
        'other': []
    }
    
    # Common standard library modules
    stdlib = {
        'os', 'sys', 'json', 'datetime', 'typing', 'uuid', 'asyncio',
        'collections', 'enum', 'logging', 'pathlib', 're', 'time',
        'hashlib', 'base64', 'secrets', 'functools', 'itertools',
        'urllib', 'io', 'tempfile', 'shutil', 'subprocess', 'abc',
        'traceback', 'inspect', 'warnings', 'copy', 'random', 'math'
    }
    
    for module in sorted(imports.keys()):
        if module in stdlib:
            categories['standard_lib'].append(module)
        elif module in ['crewai', 'crewai_tools']:
            categories['crewai'].append(module)
        elif module in ['fastapi', 'uvicorn', 'starlette', 'pydantic']:
            categories['fastapi'].append(module)
        elif module in ['sqlalchemy', 'alembic', 'psycopg2', 'asyncpg']:
            categories['database'].append(module)
        elif module in ['jose', 'passlib', 'jwt']:
            categories['auth'].append(module)
        elif module in ['googleapiclient', 'google_auth_httplib2', 'google']:
            categories['google'].append(module)
        elif module in ['openai', 'tiktoken', 'litellm']:
            categories['llm'].append(module)
        elif module in ['pytest', 'pytest_asyncio', 'pytest_mock']:
            categories['testing'].append(module)
        else:
            categories['other'].append(module)
    
    return categories

def main():
    print("🔍 Scanning codebase for imports...")
    print("=" * 60)
    
    # Scan src directory
    src_dir = os.path.join(os.path.dirname(__file__), '..', 'src')
    imports = scan_python_files(src_dir)
    
    # Categorize imports
    categories = categorize_imports(imports)
    
    # Display results
    for category, modules in categories.items():
        if modules and category != 'standard_lib':
            print(f"\n📦 {category.upper()}:")
            for module in modules:
                count = len(imports[module])
                print(f"  • {module} (used in {count} files)")
    
    # Show all unique imports
    print("\n📋 All Third-Party Imports:")
    third_party = []
    for category, modules in categories.items():
        if category != 'standard_lib':
            third_party.extend(modules)
    
    for module in sorted(set(third_party)):
        print(f"  - {module}")
    
    # Map to package names
    print("\n📌 Required Packages (based on imports):")
    package_map = {
        'crewai': 'crewai',
        'crewai_tools': 'crewai-tools',
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn[standard]',
        'pydantic': 'pydantic',  # Usually comes with fastapi
        'sqlalchemy': 'sqlalchemy',
        'alembic': 'alembic',
        'psycopg2': 'psycopg2-binary',
        'asyncpg': 'asyncpg',
        'jose': 'python-jose[cryptography]',
        'passlib': 'passlib[bcrypt]',
        'jwt': 'pyjwt',
        'googleapiclient': 'google-api-python-client',
        'google_auth_httplib2': 'google-auth-httplib2',
        'openai': 'openai',
        'tiktoken': 'tiktoken',
        'litellm': 'litellm',
        'httpx': 'httpx',
        'requests': 'requests',
        'yaml': 'pyyaml',
        'dotenv': 'python-dotenv',
        'redis': 'redis',
        'structlog': 'structlog',
        'prometheus_client': 'prometheus-client',
        'cachetools': 'cachetools',
        'sendgrid': 'sendgrid',
        'PIL': 'Pillow',
        'pdfplumber': 'pdfplumber',
        'pypdf': 'pypdf',
        'chromadb': 'chromadb',
        'multipart': 'python-multipart',
    }
    
    required_packages = set()
    for module in third_party:
        if module in package_map:
            required_packages.add(package_map[module])
        else:
            print(f"  ⚠️  Unknown package for module: {module}")
    
    print("\nMinimal requirements based on actual usage:")
    for pkg in sorted(required_packages):
        print(f"  {pkg}")
    
    # Write scan results
    with open('import_scan_results.txt', 'w') as f:
        f.write("Import Scan Results\n")
        f.write("==================\n\n")
        
        for category, modules in categories.items():
            if modules:
                f.write(f"{category.upper()}:\n")
                for module in modules:
                    count = len(imports[module])
                    f.write(f"  {module} ({count} files)\n")
                f.write("\n")
    
    print("\n💾 Detailed results saved to: import_scan_results.txt")

if __name__ == "__main__":
    main()