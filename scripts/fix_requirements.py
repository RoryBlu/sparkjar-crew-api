#!/usr/bin/env python3
"""
Strategic approach to fixing requirements.txt
"""

import subprocess
import sys
import os
import tempfile
import shutil

# Define package groups
PACKAGE_GROUPS = {
    "core": [
        "crewai==0.148.0",
        "crewai-tools>=0.51.1",
    ],
    "api": [
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "python-multipart>=0.0.6",
    ],
    "database": [
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.0",
        "alembic>=1.13.0",
        "asyncpg>=0.29.0",  # For async support
    ],
    "auth": [
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
    ],
    "llm": [
        # OpenAI is included by CrewAI, so we don't need to specify
        "tiktoken>=0.5.2",
    ],
    "utils": [
        "python-dotenv>=1.0.0",
        # Pydantic is included by CrewAI
        "pyyaml>=6.0.0",
        "httpx>=0.25.0",
        "requests>=2.31.0",
    ],
    "google": [
        "google-api-python-client>=2.100.0",
        "google-auth-httplib2>=0.1.1",
        "google-auth-oauthlib>=1.1.0",
    ],
    "docs": [
        "pdfplumber>=0.11.4",  # Already in CrewAI
        "pypdf>=3.17.0",
        "python-docx>=1.0.0",
    ],
    "email": [
        "sendgrid>=6.11.0",
    ],
    "chat": [
        "redis>=5.0.0",
        "structlog>=24.1.0",
        "prometheus-client>=0.19.0",
        "cachetools>=5.3.0",
    ],
    "testing": [
        "pytest>=7.4.0",
        "pytest-asyncio>=0.21.0",
        "pytest-mock>=3.12.0",
    ]
}

# OCR packages are problematic, handle separately
OCR_PACKAGES = [
    # "paddlepaddle>=2.5.0",  # Very large and complex
    # "paddleocr>=2.7.0",     # Depends on paddlepaddle
    "Pillow>=10.0.0",  # Basic image support
]

def create_test_requirements(packages, filename):
    """Create a test requirements file."""
    with open(filename, 'w') as f:
        for pkg in packages:
            f.write(f"{pkg}\n")

def test_installation(req_file, venv_path):
    """Test installation in a clean virtual environment."""
    print(f"\n🧪 Testing {req_file}...")
    
    # Create virtual environment
    subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)
    
    # Get pip path
    pip_path = os.path.join(venv_path, 'bin', 'pip')
    
    # Upgrade pip
    subprocess.run([pip_path, 'install', '--upgrade', 'pip'], capture_output=True)
    
    # Try installation
    result = subprocess.run(
        [pip_path, 'install', '-r', req_file],
        capture_output=True,
        text=True
    )
    
    success = result.returncode == 0
    
    if not success:
        print(f"❌ Installation failed!")
        print("Error output:")
        print(result.stderr[-1000:])  # Last 1000 chars
    else:
        print(f"✅ Installation successful!")
        
        # Check key imports
        python_path = os.path.join(venv_path, 'bin', 'python')
        test_imports = [
            "import crewai",
            "import fastapi",
            "import sqlalchemy",
            "import redis",
        ]
        
        for imp in test_imports:
            result = subprocess.run(
                [python_path, '-c', imp],
                capture_output=True
            )
            if result.returncode == 0:
                print(f"  ✅ {imp}")
            else:
                print(f"  ❌ {imp}")
    
    # Cleanup
    shutil.rmtree(venv_path)
    
    return success

def build_requirements_incrementally():
    """Build requirements incrementally, testing each group."""
    working_packages = []
    failed_groups = []
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Start with core
        for group_name, packages in PACKAGE_GROUPS.items():
            print(f"\n📦 Testing group: {group_name}")
            
            test_packages = working_packages + packages
            req_file = os.path.join(tmpdir, f"test_{group_name}.txt")
            create_test_requirements(test_packages, req_file)
            
            venv_path = os.path.join(tmpdir, f"venv_{group_name}")
            
            if test_installation(req_file, venv_path):
                working_packages.extend(packages)
                print(f"✅ Group {group_name} added successfully")
            else:
                failed_groups.append(group_name)
                print(f"❌ Group {group_name} failed - skipping")
        
        # Test OCR packages separately
        print(f"\n📦 Testing OCR packages...")
        for pkg in OCR_PACKAGES:
            test_packages = working_packages + [pkg]
            req_file = os.path.join(tmpdir, f"test_ocr_{pkg.split('>=')[0]}.txt")
            create_test_requirements(test_packages, req_file)
            
            venv_path = os.path.join(tmpdir, f"venv_ocr_{pkg.split('>=')[0]}")
            
            if test_installation(req_file, venv_path):
                working_packages.append(pkg)
                print(f"✅ {pkg} added successfully")
            else:
                print(f"❌ {pkg} failed - skipping")
    
    return working_packages, failed_groups

def write_final_requirements(packages):
    """Write the final working requirements.txt"""
    filename = "requirements_fixed.txt"
    
    with open(filename, 'w') as f:
        f.write("# Fixed requirements for crew-api service\n")
        f.write("# Generated after testing each package group\n")
        f.write("# CrewAI version: 0.148.0\n\n")
        
        # Group packages by category for readability
        groups = {
            "Core CrewAI": [],
            "API Framework": [],
            "Database": [],
            "Authentication": [],
            "Utilities": [],
            "Google Integration": [],
            "Document Processing": [],
            "Chat Interface": [],
            "Testing": [],
            "Other": []
        }
        
        for pkg in packages:
            pkg_name = pkg.split('>=')[0].split('==')[0]
            
            if 'crewai' in pkg_name:
                groups["Core CrewAI"].append(pkg)
            elif pkg_name in ['fastapi', 'uvicorn', 'python-multipart']:
                groups["API Framework"].append(pkg)
            elif pkg_name in ['sqlalchemy', 'psycopg2-binary', 'alembic', 'asyncpg']:
                groups["Database"].append(pkg)
            elif pkg_name in ['python-jose', 'passlib']:
                groups["Authentication"].append(pkg)
            elif pkg_name in ['redis', 'structlog', 'prometheus-client', 'cachetools']:
                groups["Chat Interface"].append(pkg)
            elif 'google' in pkg_name:
                groups["Google Integration"].append(pkg)
            elif pkg_name in ['pdfplumber', 'pypdf', 'python-docx', 'Pillow']:
                groups["Document Processing"].append(pkg)
            elif pkg_name in ['pytest', 'pytest-asyncio', 'pytest-mock']:
                groups["Testing"].append(pkg)
            else:
                groups["Utilities"].append(pkg)
        
        for group_name, group_packages in groups.items():
            if group_packages:
                f.write(f"# {group_name}\n")
                for pkg in sorted(group_packages):
                    f.write(f"{pkg}\n")
                f.write("\n")
    
    print(f"\n✅ Final requirements written to: {filename}")
    return filename

def main():
    print("🛠️  Strategic Requirements Fix")
    print("=" * 60)
    print("Starting with CrewAI 0.148.0 and building up...")
    
    # Check Python version
    print(f"\nPython version: {sys.version}")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required for CrewAI")
        return
    
    # Build requirements incrementally
    working_packages, failed_groups = build_requirements_incrementally()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"✅ Working packages: {len(working_packages)}")
    print(f"❌ Failed groups: {len(failed_groups)}")
    
    if failed_groups:
        print(f"\nFailed groups: {', '.join(failed_groups)}")
    
    # Write final requirements
    if working_packages:
        final_file = write_final_requirements(working_packages)
        
        print("\n🎯 Next steps:")
        print(f"1. Review {final_file}")
        print(f"2. Replace requirements.txt with {final_file}")
        print("3. Test in your actual environment")
        print("4. Consider alternatives for failed packages")

if __name__ == "__main__":
    main()