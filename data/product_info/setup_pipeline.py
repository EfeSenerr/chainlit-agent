#!/usr/bin/env python3
"""
Setup script to configure the document indexing pipeline using your existing Azure environment
"""

import os
import shutil
from pathlib import Path

def setup_environment():
    """Setup the environment configuration from your existing .env file"""
    
    print("🔧 Setting up document indexing pipeline environment")
    print("=" * 60)
    
    # Source .env file in workspace root
    source_env = Path("/workspaces/chainlit-agent/.env")
    target_env = Path("./data/product_info/.env")
    
    if not source_env.exists():
        print("❌ Source .env file not found at /workspaces/chainlit-agent/.env")
        return False
    
    # Read the source environment variables we need
    env_vars = {}
    with open(source_env, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value.strip('"')
    
    # Required variables for the indexing pipeline
    required_vars = {
        'AZURE_SEARCH_ENDPOINT': env_vars.get('AZURE_SEARCH_ENDPOINT'),
        'AZURE_SEARCH_INDEX': env_vars.get('AZURE_SEARCH_INDEX', 'document-index'),
        'AZURE_OPENAI_ENDPOINT': env_vars.get('AZURE_OPENAI_ENDPOINT'),
        'AZURE_EMBEDDING_NAME': env_vars.get('AZURE_EMBEDDING_NAME'),
        'AZURE_OPENAI_CHAT_DEPLOYMENT': env_vars.get('AZURE_OPENAI_CHAT_DEPLOYMENT'),
        'AZURE_OPENAI_API_VERSION': env_vars.get('AZURE_OPENAI_API_VERSION'),
    }
    
    # Check if we have the required variables
    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Create the target .env file
    target_env.parent.mkdir(parents=True, exist_ok=True)
    
    with open(target_env, 'w') as f:
        f.write("# Auto-generated configuration for document indexing pipeline\n")
        f.write("# Based on your existing Azure environment\n\n")
        
        f.write("# Azure Search Configuration\n")
        f.write(f"AZURE_SEARCH_ENDPOINT={required_vars['AZURE_SEARCH_ENDPOINT']}\n")
        f.write(f"AZURE_SEARCH_INDEX={required_vars['AZURE_SEARCH_INDEX']}\n\n")
        
        f.write("# Azure OpenAI Configuration (using Entra ID authentication)\n")
        f.write(f"AZURE_OPENAI_ENDPOINT={required_vars['AZURE_OPENAI_ENDPOINT']}\n")
        f.write(f"AZURE_EMBEDDING_NAME={required_vars['AZURE_EMBEDDING_NAME']}\n")
        f.write(f"AZURE_OPENAI_CHAT_DEPLOYMENT={required_vars['AZURE_OPENAI_CHAT_DEPLOYMENT']}\n")
        f.write(f"AZURE_OPENAI_API_VERSION={required_vars['AZURE_OPENAI_API_VERSION']}\n\n")
        
        f.write("# GPT-4o deployment for vision capabilities\n")
        f.write(f"AZURE_OPENAI_GPT4_DEPLOYMENT_NAME={required_vars['AZURE_OPENAI_CHAT_DEPLOYMENT']}\n\n")
        
        f.write("# Optional: Azure AI Vision for enhanced OCR\n")
        f.write("# AZURE_VISION_ENDPOINT=https://your-vision-service.cognitiveservices.azure.com/\n")
        f.write("# AZURE_VISION_KEY=your-vision-api-key\n\n")
        
        f.write("# Authentication: Using Entra ID (Azure AD) - DefaultAzureCredential\n")
        f.write("# No API keys needed - script uses managed identity/service principal\n")
    
    print("✅ Environment configuration created successfully!")
    print(f"📁 Created: {target_env}")
    
    print(f"\n📋 Configuration Summary:")
    print(f"   🔍 Search Endpoint: {required_vars['AZURE_SEARCH_ENDPOINT']}")
    print(f"   📚 Search Index: {required_vars['AZURE_SEARCH_INDEX']}")
    print(f"   🧠 OpenAI Endpoint: {required_vars['AZURE_OPENAI_ENDPOINT']}")
    print(f"   📊 Embedding Model: {required_vars['AZURE_EMBEDDING_NAME']}")
    print(f"   🖼️ Vision Model: {required_vars['AZURE_OPENAI_CHAT_DEPLOYMENT']}")
    print(f"   🔐 Authentication: Entra ID (DefaultAzureCredential)")
    
    return True

def create_sample_data():
    """Create sample data directory structure"""
    data_dir = Path("./data/product_info/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a sample markdown file with base64 image for testing
    sample_md = data_dir / "sample_document.md"
    with open(sample_md, 'w', encoding='utf-8') as f:
        f.write("""# Sample Document with Image

This is a test document to demonstrate image content extraction.

![Sample Chart](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==)

The image above would normally be processed to extract any text or visual content.

## Key Features

- Document processing with image content extraction
- Multi-format support (MD, CSV, PDF, Excel, JSON)
- German text encoding handling
- Azure Cognitive Search indexing

This sample demonstrates the pipeline functionality.
""")
    
    print(f"✅ Sample data created at: {data_dir}")
    return True

if __name__ == "__main__":
    print("🚀 Document Indexing Pipeline Setup")
    print("=" * 60)
    
    if setup_environment():
        create_sample_data()
        
        print(f"\n{'='*60}")
        print("🎉 SETUP COMPLETED SUCCESSFULLY!")
        print("\nNext steps:")
        print("1. Navigate to: cd data/product_info")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Add your documents to: ./data/")
        print("4. Run the pipeline: python create-azure-search.py")
        print(f"{'='*60}")
    else:
        print(f"\n❌ Setup failed. Please check your environment configuration.")
