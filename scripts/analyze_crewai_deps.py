#!/usr/bin/env python3
"""
Analyze CrewAI 0.148.0 dependencies and conflicts.
"""

import subprocess
import json
import sys

def get_package_info(package, version=None):
    """Get package info from PyPI."""
    url = f"https://pypi.org/pypi/{package}/json" if not version else f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        result = subprocess.run(['curl', '-s', url], capture_output=True, text=True)
        return json.loads(result.stdout)
    except:
        return None

def parse_requirement(req):
    """Parse a requirement string."""
    # Remove extras and environment markers
    if '[' in req:
        req = req.split('[')[0]
    if ';' in req:
        req = req.split(';')[0]
    
    # Parse package name and version spec
    for op in ['>=', '<=', '==', '!=', '~=', '>', '<']:
        if op in req:
            parts = req.split(op, 1)
            return parts[0].strip(), op + parts[1].strip()
    
    return req.strip(), None

def analyze_dependencies(package_name, version, depth=0, analyzed=None):
    """Recursively analyze dependencies."""
    if analyzed is None:
        analyzed = set()
    
    if f"{package_name}=={version}" in analyzed or depth > 2:
        return {}
    
    analyzed.add(f"{package_name}=={version}")
    
    indent = "  " * depth
    print(f"{indent}📦 {package_name}=={version}")
    
    info = get_package_info(package_name, version)
    if not info:
        return {}
    
    deps = {}
    requires_dist = info.get('info', {}).get('requires_dist', [])
    
    if requires_dist:
        for req in requires_dist:
            # Skip conditional dependencies for now
            if 'extra ==' in req or 'python_version' in req:
                continue
                
            pkg_name, version_spec = parse_requirement(req)
            print(f"{indent}  → {pkg_name} {version_spec or ''}")
            deps[pkg_name] = version_spec
    
    return deps

def main():
    print("🚀 Analyzing CrewAI 0.148.0 Dependencies")
    print("=" * 60)
    
    # Get CrewAI 0.148.0 info
    crewai_info = get_package_info('crewai', '0.148.0')
    if not crewai_info:
        print("❌ Failed to fetch CrewAI 0.148.0 info")
        return
    
    # Extract requirements
    requires_dist = crewai_info.get('info', {}).get('requires_dist', [])
    
    print("\n📋 CrewAI 0.148.0 Direct Dependencies:")
    crewai_deps = {}
    
    for req in requires_dist:
        # Skip extras and conditionals for now
        if 'extra ==' in req:
            continue
        
        # Basic parsing
        if ';' in req:
            base_req = req.split(';')[0].strip()
        else:
            base_req = req.strip()
        
        pkg_name, version_spec = parse_requirement(base_req)
        crewai_deps[pkg_name] = version_spec
        print(f"  • {pkg_name} {version_spec or ''}")
    
    # Check specific problematic packages
    print("\n🔍 Checking Key Dependencies:")
    
    # Check ChromaDB
    if 'chromadb' in crewai_deps:
        print(f"\n📌 ChromaDB: {crewai_deps['chromadb']}")
        chromadb_version = crewai_deps['chromadb'].replace('>=', '').replace('==', '').strip()
        chromadb_info = get_package_info('chromadb', chromadb_version)
        if chromadb_info:
            chromadb_requires = chromadb_info.get('info', {}).get('requires_dist', [])
            print("  ChromaDB dependencies:")
            for req in chromadb_requires[:10]:  # First 10
                if 'extra ==' not in req and 'python_version' not in req:
                    print(f"    - {req.split(';')[0].strip()}")
    
    # Check Pydantic
    if 'pydantic' in crewai_deps:
        print(f"\n📌 Pydantic: {crewai_deps['pydantic']}")
    
    # Check OpenAI
    if 'openai' in crewai_deps:
        print(f"\n📌 OpenAI: {crewai_deps['openai']}")
    
    # Write minimal requirements
    print("\n💡 Suggested Minimal Requirements:")
    print("# Core dependencies with specific versions to avoid conflicts")
    print("crewai==0.148.0")
    print("# Let pip resolve transitive dependencies")
    
    # Write comprehensive analysis
    with open('crewai_deps_analysis.json', 'w') as f:
        json.dump({
            'crewai_version': '0.148.0',
            'direct_dependencies': crewai_deps,
            'requires_dist_raw': requires_dist
        }, f, indent=2)
    
    print("\n💾 Full analysis saved to: crewai_deps_analysis.json")

if __name__ == "__main__":
    main()