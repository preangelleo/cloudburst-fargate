#!/usr/bin/env python3
"""
Upload CloudBurst Fargate to PyPI
"""

import os
import subprocess
import sys

# Get the API token from environment
token = os.getenv("PYPI_API_TOKEN")

if not token:
    print("❌ Error: PYPI_API_TOKEN environment variable not set!")
    print("\nTo upload to PyPI, you need to:")
    print("1. Get your PyPI API token from https://pypi.org/manage/account/token/")
    print("2. Set it as environment variable:")
    print("   export PYPI_API_TOKEN='your-token-here'")
    print("3. Run this script again")
    sys.exit(1)

print(f"✅ PyPI API Token found (length: {len(token)})")

# Check if packages exist
dist_files = [
    "dist/cloudburst_fargate-1.0.0-py3-none-any.whl",
    "dist/cloudburst_fargate-1.0.0.tar.gz"
]

for file in dist_files:
    if not os.path.exists(file):
        print(f"❌ Missing distribution file: {file}")
        print("Run 'python -m build' first")
        sys.exit(1)

print("✅ Distribution files found")

# Upload using twine
print("\n📤 Uploading to PyPI...")
cmd = [
    "python", "-m", "twine", "upload",
    "dist/*",
    "--username", "__token__",
    "--password", token
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Successfully uploaded to PyPI!")
        print("\n🎉 CloudBurst Fargate is now available on PyPI!")
        print("Install with: pip install cloudburst-fargate")
    else:
        print(f"❌ Upload failed!")
        print(f"Error: {result.stderr}")
        
except Exception as e:
    print(f"❌ Error running twine: {str(e)}")