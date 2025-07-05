#!/usr/bin/env python3
"""
Quick test to validate Azure OpenAI configuration for GPT-4o Vision
"""

import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

def test_azure_openai_config():
    """Test Azure OpenAI configuration"""
    print("🧪 Testing Azure OpenAI Configuration")
    print("=" * 50)
    
    # Get configuration - force specific API version
    api_base = os.getenv('AZURE_OPENAI_ENDPOINT')
    deployment_name = os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-4o')
    api_version = "2024-02-01"  # Force a known working version
    
    print(f"📍 Endpoint: {api_base}")
    print(f"🎯 Deployment: {deployment_name}")
    print(f"📅 API Version: {api_version} (forced)")
    
    if not api_base:
        print("❌ AZURE_OPENAI_ENDPOINT not configured")
        return False
    
    try:
        # Create client
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), 
            "https://cognitiveservices.azure.com/.default"
        )
        
        client = AzureOpenAI(
            azure_endpoint=api_base,
            azure_ad_token_provider=token_provider,
            api_version=api_version
        )
        
        print("✅ Client created successfully")
        
        # Test simple text completion
        print("🧪 Testing text completion...")
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "user", "content": "Hello, just testing the connection. Please respond with 'Connection successful!'"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ Text response: {result}")
        
        # Test vision capability with a simple test
        print("🧪 Testing vision capability...")
        test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="  # 1x1 red pixel
        
        vision_response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What do you see in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{test_image_b64}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ],
            max_tokens=50
        )
        
        vision_result = vision_response.choices[0].message.content.strip()
        print(f"✅ Vision response: {vision_result}")
        
        print("\n🎉 All tests passed! Configuration is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Error testing configuration: {e}")
        return False

if __name__ == "__main__":
    test_azure_openai_config()
