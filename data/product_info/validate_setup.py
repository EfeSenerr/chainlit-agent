#!/usr/bin/env python3
"""
Quick validation script to test the two-step workflow
"""

import os
from pathlib import Path
import subprocess
import sys

def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_CHAT_DEPLOYMENT', 
        'AZURE_EMBEDDING_NAME',
        'AZURE_SEARCH_ENDPOINT',
        'AZURE_SEARCH_INDEX'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease check your .env file")
        return False
    
    print("✅ All required environment variables are set")
    return True

def check_files():
    """Check if required files exist"""
    current_dir = Path(__file__).parent
    required_files = [
        'convert_base64_to_text.py',
        'create-azure-search.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not (current_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ All required script files exist")
    return True

def check_data_directory():
    """Check if data directory exists and has .md files"""
    data_dir = Path("./data")
    if not data_dir.exists():
        print("❌ Data directory './data' not found")
        print("   Create it and add your markdown files")
        return False
    
    md_files = list(data_dir.glob("**/*.md"))
    if not md_files:
        print("⚠️ No .md files found in ./data directory")
        print("   This is OK if you only have other file types")
    else:
        print(f"✅ Found {len(md_files)} markdown files")
    
    all_files = []
    for ext in ['.md', '.txt', '.csv', '.pdf', '.xlsx', '.xls', '.json']:
        all_files.extend(data_dir.glob(f"**/*{ext}"))
    
    print(f"📊 Total supported files found: {len(all_files)}")
    return len(all_files) > 0

def main():
    """Main validation function"""
    print("🧪 Validating Two-Step Document Indexing Workflow")
    print("=" * 60)
    
    # Check environment
    if not check_environment():
        return False
    
    # Check files
    if not check_files():
        return False
    
    # Check data
    if not check_data_directory():
        return False
    
    print("\n✅ VALIDATION PASSED!")
    print("\n📋 Next steps:")
    print("1. Run: python convert_base64_to_text.py")
    print("   (Preprocesses markdown files with base64 images)")
    print("2. Run: python create-azure-search.py")
    print("   (Creates the search index with all documents)")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
