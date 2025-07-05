#!/usr/bin/env python3
"""
Base64 Image to Text Converter for Markdown Files

This script processes all .md files in a specified directory and converts embedded 
base64 images to detailed text descriptions using GPT-4o Vision. It preserves the 
original files as backups and creates cleaned versions with image content extracted.

Features:
- Processes all .md files recursively in the specified directory
- Uses GPT-4o Vision with Entra ID authentication
- Extracts text, percentages, charts, graphs, and visual data from images
- Creates backups of original files
- Detailed progress reporting
- Robust error handling

Usage:
    python convert_base64_to_text.py [directory_path]
    
    If no directory is specified, it defaults to './data/'
"""

import os
import re
import base64
import sys
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Base64ImageConverter:
    """Converts base64 images in markdown files to detailed text descriptions"""
    
    def __init__(self):
        """Initialize the converter with Azure OpenAI client"""
        self.setup_openai_client()
        self.stats = {
            'files_processed': 0,
            'files_with_images': 0,
            'images_converted': 0,
            'errors': 0
        }
    
    def setup_openai_client(self):
        """Setup Azure OpenAI client with Entra ID authentication"""
        try:
            api_base = os.getenv('AZURE_OPENAI_ENDPOINT')
            deployment_name = os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-4o')
            api_version = "2024-02-01"  # Use known working API version
            
            if not api_base:
                raise ValueError("AZURE_OPENAI_ENDPOINT not configured in environment")
            
            # Create client using Entra ID authentication
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), 
                "https://cognitiveservices.azure.com/.default"
            )
            
            self.client = AzureOpenAI(
                azure_endpoint=api_base,
                azure_ad_token_provider=token_provider,
                api_version=api_version
            )
            
            self.deployment_name = deployment_name
            print(f"✅ Azure OpenAI client initialized successfully")
            print(f"   🎯 Using deployment: {deployment_name}")
            print(f"   🔐 Authentication: Entra ID (DefaultAzureCredential)")
            print(f"   📅 API Version: {api_version}")
            
        except Exception as e:
            print(f"❌ Failed to initialize Azure OpenAI client: {e}")
            raise
    
    def extract_base64_images(self, text: str) -> List[Tuple[str, str, str, str]]:
        """
        Extract all base64 images from markdown text
        
        Returns:
            List of tuples: (full_match, alt_text, image_format, base64_data)
        """
        images = []
        
        # Pattern for markdown images with base64
        markdown_pattern = r'!\[(.*?)\]\(data:image/([^;]+);base64,([A-Za-z0-9+/\s]+=*)\)'
        matches = re.finditer(markdown_pattern, text, re.DOTALL)
        
        for match in matches:
            full_match = match.group(0)
            alt_text = match.group(1)
            image_format = match.group(2)
            base64_data = match.group(3)
            images.append((full_match, alt_text, image_format, base64_data))
        
        # Pattern for HTML img tags with base64
        html_pattern = r'<img[^>]*src="data:image/([^;]+);base64,([A-Za-z0-9+/\s]+=*)"[^>]*>'
        html_matches = re.finditer(html_pattern, text, re.DOTALL)
        
        for match in html_matches:
            full_match = match.group(0)
            alt_text = ""  # HTML images might not have alt text easily extractable
            image_format = match.group(1)
            base64_data = match.group(2)
            images.append((full_match, alt_text, image_format, base64_data))
        
        return images
    
    def analyze_image_with_gpt4v(self, image_bytes: bytes, image_format: str, alt_text: str = "") -> str:
        """
        Analyze image using GPT-4o Vision to extract detailed content
        
        Args:
            image_bytes: The decoded image bytes
            image_format: Image format (png, jpg, etc.)
            alt_text: Alternative text if available
            
        Returns:
            Detailed description of the image content
        """
        try:
            # Encode image for API
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create detailed prompt for content extraction
            prompt = """Analyze this image and provide a comprehensive, detailed description that includes:

1. **Text Content**: Extract ALL visible text, numbers, percentages, labels, titles, and captions exactly as they appear
2. **Data & Statistics**: If there are charts, graphs, or tables, describe the data values, percentages, trends, and relationships
3. **Visual Structure**: Describe the layout, type of visualization (bar chart, pie chart, line graph, table, diagram, etc.)
4. **Context & Meaning**: Explain what the image is showing and its apparent purpose
5. **Details**: Include colors, legends, axes labels, units of measurement, and any other relevant details

Focus on making this description comprehensive enough that someone could understand the full content and meaning of the image without seeing it. Pay special attention to any numerical data, percentages, statistics, or quantitative information."""

            if alt_text:
                prompt += f"\n\nNote: The image has alt text: '{alt_text}'"
            
            # Call GPT-4o Vision API
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert at analyzing images and extracting comprehensive, detailed descriptions for document processing. Focus on accuracy and completeness."
                    },
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "text", 
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500,  # Increased for detailed descriptions
                temperature=0.1   # Low temperature for consistent analysis
            )
            
            description = response.choices[0].message.content.strip()
            
            # Add alt text context if provided
            if alt_text:
                return f"**Image Description (Alt text: {alt_text}):**\n\n{description}"
            else:
                return f"**Image Description:**\n\n{description}"
                
        except Exception as e:
            error_msg = f"Failed to analyze image: {str(e)}"
            print(f"   ⚠️ {error_msg}")
            if alt_text:
                return f"**Image Description (Alt text: {alt_text}):** [Error analyzing image: {error_msg}]"
            else:
                return f"**Image Description:** [Error analyzing image: {error_msg}]"
    
    def convert_images_in_text(self, text: str, filename: str) -> Tuple[str, int]:
        """
        Convert all base64 images in text to detailed descriptions
        
        Args:
            text: The markdown text content
            filename: Name of the file being processed (for logging)
            
        Returns:
            Tuple of (converted_text, number_of_images_converted)
        """
        images = self.extract_base64_images(text)
        
        if not images:
            return text, 0
        
        print(f"   🖼️ Found {len(images)} base64 images to convert")
        
        converted_text = text
        converted_count = 0
        
        for i, (full_match, alt_text, image_format, base64_data) in enumerate(images, 1):
            try:
                print(f"   📸 Converting image {i}/{len(images)}...")
                
                # Decode base64 image
                # Clean up the base64 data (remove whitespace and newlines)
                clean_base64 = base64_data.replace('\n', '').replace(' ', '').replace('\r', '')
                image_bytes = base64.b64decode(clean_base64)
                
                # Analyze image with GPT-4o Vision
                description = self.analyze_image_with_gpt4v(image_bytes, image_format, alt_text)
                
                # Replace the base64 image with the description
                converted_text = converted_text.replace(full_match, f"\n{description}\n")
                converted_count += 1
                
                print(f"   ✅ Image {i} converted successfully")
                
            except Exception as e:
                print(f"   ❌ Failed to convert image {i}: {e}")
                # Replace with error message but continue processing
                error_desc = f"**Image Description:** [Failed to process image: {str(e)}]"
                if alt_text:
                    error_desc = f"**Image Description (Alt text: {alt_text}):** [Failed to process image: {str(e)}]"
                converted_text = converted_text.replace(full_match, f"\n{error_desc}\n")
                self.stats['errors'] += 1
        
        return converted_text, converted_count
    
    def create_backup(self, file_path: Path) -> Path:
        """Create a backup of the original file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".backup_{timestamp}{file_path.suffix}")
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def process_markdown_file(self, file_path: Path) -> bool:
        """
        Process a single markdown file to convert base64 images
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            print(f"\n📄 Processing: {file_path.name}")
            
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file contains base64 images
            if 'data:image/' not in content or 'base64,' not in content:
                print(f"   ℹ️ No base64 images found")
                self.stats['files_processed'] += 1
                return True
            
            # Create backup
            backup_path = self.create_backup(file_path)
            print(f"   💾 Backup created: {backup_path.name}")
            
            # Convert images to descriptions
            converted_content, image_count = self.convert_images_in_text(content, file_path.name)
            
            if image_count > 0:
                # Write the converted content back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(converted_content)
                
                print(f"   ✅ Converted {image_count} images and updated file")
                self.stats['files_with_images'] += 1
                self.stats['images_converted'] += image_count
            else:
                print(f"   ⚠️ No images were successfully converted")
            
            self.stats['files_processed'] += 1
            return True
            
        except Exception as e:
            print(f"   ❌ Error processing {file_path.name}: {e}")
            self.stats['errors'] += 1
            return False
    
    def process_directory(self, directory_path: str) -> None:
        """
        Process all markdown files in a directory recursively
        
        Args:
            directory_path: Path to the directory to process
        """
        dir_path = Path(directory_path)
        
        if not dir_path.exists():
            print(f"❌ Directory does not exist: {directory_path}")
            return
        
        # Find all .md files recursively
        md_files = list(dir_path.glob("**/*.md"))
        
        if not md_files:
            print(f"ℹ️ No .md files found in {directory_path}")
            return
        
        print(f"🔍 Found {len(md_files)} markdown files to process")
        print(f"📁 Processing directory: {dir_path.absolute()}")
        
        # Process each file
        for file_path in md_files:
            self.process_markdown_file(file_path)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print processing summary statistics"""
        print(f"\n{'='*60}")
        print("📊 CONVERSION SUMMARY")
        print(f"{'='*60}")
        print(f"📄 Files processed: {self.stats['files_processed']}")
        print(f"🖼️ Files with images: {self.stats['files_with_images']}")
        print(f"📸 Total images converted: {self.stats['images_converted']}")
        if self.stats['errors'] > 0:
            print(f"❌ Errors encountered: {self.stats['errors']}")
        else:
            print("✅ No errors encountered")
        print(f"{'='*60}")

def main():
    """Main execution function"""
    print("🚀 Base64 Image to Text Converter for Markdown Files")
    print("=" * 60)
    
    # Get directory path from command line argument or use default
    if len(sys.argv) > 1:
        directory_path = sys.argv[1]
    else:
        directory_path = "./data/"
    
    print(f"📁 Target directory: {Path(directory_path).absolute()}")
    
    try:
        # Initialize converter
        converter = Base64ImageConverter()
        
        # Process directory
        converter.process_directory(directory_path)
        
        print(f"\n🎉 CONVERSION COMPLETED!")
        print("Next steps:")
        print("1. Review the converted files to ensure accuracy")
        print("2. Run your document indexing pipeline")
        print("3. Backup files are available if you need to revert changes")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
