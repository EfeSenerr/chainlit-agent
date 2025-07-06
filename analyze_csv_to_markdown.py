#!/usr/bin/env python3
"""
CSV Data Analyzer and Markdown Generator

This script processes all .csv files in a specified directory and generates 
objective analyses using GPT-4o. It reads CSV data, analyzes the content,
and creates detailed markdown reports with statistical insights.

Features:
- Processes all .csv files recursively in the specified directory
- Uses GPT-4o with Entra ID authentication for analysis
- Generates objective statistical analyses with numbers and trends
- Creates markdown files in data/csv_converted/ directory
- Detailed progress reporting
- Robust error handling

Usage:
    python analyze_csv_to_markdown.py [directory_path]
    
    If no directory is specified, it defaults to './data/product_info/data/'
"""

import os
import sys
import re
import csv
import shutil
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CSVAnalyzer:
    """Analyzes CSV files and generates objective markdown reports"""
    
    def __init__(self):
        """Initialize the analyzer with Azure OpenAI client"""
        self.setup_openai_client()
        self.output_dir = Path("./data/csv_converted")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.stats = {
            'files_processed': 0,
            'files_analyzed': 0,
            'analyses_generated': 0,
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
    
    def read_csv_content(self, file_path: Path) -> Dict[str, Any]:
        """
        Read CSV file and extract structured content
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Dictionary containing CSV data and metadata
        """
        try:
            # Try to read with pandas first for better handling
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
                
                # If DataFrame is mostly empty or has weird structure, try alternative approach
                if df.shape[0] < 2 or df.shape[1] < 2:
                    raise ValueError("DataFrame too small, trying raw CSV read")
                    
            except (pd.errors.EmptyDataError, ValueError, UnicodeDecodeError):
                # Fallback to raw CSV reading for complex formats
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read all lines
                    lines = f.readlines()
                
                # Find actual data start (skip metadata rows)
                data_start = 0
                for i, line in enumerate(lines):
                    if ',' in line and any(char.isdigit() for char in line):
                        data_start = i
                        break
                
                # Try to create DataFrame from data section
                if data_start < len(lines):
                    data_lines = lines[data_start:]
                    from io import StringIO
                    df = pd.read_csv(StringIO(''.join(data_lines)), encoding='utf-8')
                else:
                    # Last resort: treat as simple CSV
                    df = pd.read_csv(file_path, encoding='utf-8', header=None)
            
            # Extract metadata from the beginning of file
            metadata = {}
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract key metadata
            lines = content.split('\n')
            for line in lines[:20]:  # Check first 20 lines for metadata
                if 'Quelle' in line or 'Source' in line:
                    metadata['source'] = line.strip()
                elif 'Erhebungszeitraum' in line or 'Period' in line:
                    metadata['period'] = line.strip()
                elif 'Region' in line:
                    metadata['region'] = line.strip()
                elif 'Beschreibung' in line or 'Description' in line:
                    metadata['description'] = line.strip()
            
            return {
                'dataframe': df,
                'metadata': metadata,
                'raw_content': content[:2000],  # First 2000 chars for context
                'shape': df.shape,
                'columns': list(df.columns),
                'file_name': file_path.name
            }
            
        except Exception as e:
            print(f"   ❌ Error reading CSV file: {e}")
            return None
    
    def analyze_csv_with_gpt4(self, csv_data: Dict[str, Any]) -> str:
        """
        Analyze CSV data using GPT-4o to generate objective analysis
        
        Args:
            csv_data: Dictionary containing CSV data and metadata
            
        Returns:
            Detailed objective analysis as markdown text
        """
        try:
            df = csv_data['dataframe']
            metadata = csv_data['metadata']
            file_name = csv_data['file_name']
            
            # Prepare data summary
            data_summary = f"""
File: {file_name}
Shape: {df.shape[0]} rows × {df.shape[1]} columns
Columns: {', '.join(df.columns)}

Sample Data:
{df.head(10).to_string()}

Data Types:
{df.dtypes.to_string()}

Metadata:
{metadata}

Raw content preview:
{csv_data['raw_content']}
"""
            
            # Create comprehensive analysis prompt
            prompt = f"""Analyze this CSV dataset and provide a comprehensive, objective statistical analysis. The analysis should include:

## REQUIRED SECTIONS:

### 1. **Data Overview**
- Source and context of the data
- Time period covered
- Geographic region (if applicable)
- Dataset structure and variables

### 2. **Key Statistics**
- Present ALL important numerical values from the data
- Calculate percentages, trends, and changes where relevant
- Identify highest/lowest values, averages, totals
- Include specific numbers with proper context

### 3. **Temporal Analysis** (if time series data)
- Year-over-year changes with specific percentages
- Trends over time (increasing/decreasing/stable)
- Notable peaks, valleys, or inflection points
- Growth rates and percentage changes

## ANALYSIS REQUIREMENTS:
- Be completely objective and factual
- Include ALL significant numbers and percentages
- Use proper statistical terminology
- Provide context for all numerical findings
- Format as clear, professional markdown
- Use tables where appropriate to present data clearly
- Include source attribution

Dataset to analyze:
{data_summary}
"""

            # Call GPT-4o for analysis
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert statistical analyst specializing in objective data analysis. Your task is to provide comprehensive, factual analyses of datasets with precise numerical insights and proper statistical interpretation. Always include specific numbers, percentages, and trends. Be thorough and professional."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=2000,  # Increased for detailed analysis
                temperature=0.1   # Low temperature for objective analysis
            )
            
            analysis = response.choices[0].message.content.strip()
            
            # Add header with metadata
            header = f"""# Statistical Analysis: {file_name.replace('.csv', '')}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Source File:** `{file_name}`  
**Analysis Method:** GPT-4o Statistical Analysis  

---

"""
            
            return header + analysis
                
        except Exception as e:
            error_msg = f"Failed to analyze CSV data: {str(e)}"
            print(f"   ⚠️ {error_msg}")
            return f"# Analysis Error\n\n**Error:** {error_msg}\n\n**File:** {csv_data['file_name']}"
    
    def process_csv_file(self, file_path: Path) -> bool:
        """
        Process a single CSV file to generate analysis
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            print(f"\n📄 Processing: {file_path.name}")
            
            # Read CSV data
            csv_data = self.read_csv_content(file_path)
            if csv_data is None:
                print(f"   ❌ Failed to read CSV data")
                self.stats['errors'] += 1
                return False
            
            print(f"   📊 Dataset shape: {csv_data['shape'][0]} rows × {csv_data['shape'][1]} columns")
            
            # Generate analysis with GPT-4o
            print(f"   🤖 Analyzing data with GPT-4o...")
            analysis = self.analyze_csv_with_gpt4(csv_data)
            
            # Create output file path
            output_filename = file_path.stem + ".md"
            output_path = self.output_dir / output_filename
            
            # Write analysis to markdown file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(analysis)
            
            print(f"   ✅ Analysis saved to: {output_path}")
            
            self.stats['files_processed'] += 1
            self.stats['files_analyzed'] += 1
            self.stats['analyses_generated'] += 1
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error processing {file_path.name}: {e}")
            self.stats['errors'] += 1
            return False
    
    def process_directory(self, directory_path: str) -> None:
        """
        Process all CSV files in a directory recursively
        
        Args:
            directory_path: Path to the directory to process
        """
        dir_path = Path(directory_path)
        
        if not dir_path.exists():
            print(f"❌ Directory does not exist: {directory_path}")
            return
        
        # Find all .csv files recursively
        csv_files = list(dir_path.glob("**/*.csv"))
        
        if not csv_files:
            print(f"ℹ️ No .csv files found in {directory_path}")
            return
        
        print(f"🔍 Found {len(csv_files)} CSV files to process")
        print(f"📁 Processing directory: {dir_path.absolute()}")
        print(f"📁 Output directory: {self.output_dir.absolute()}")
        
        # Process each file
        for file_path in csv_files:
            self.process_csv_file(file_path)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print processing summary statistics"""
        print(f"\n{'='*60}")
        print("📊 CSV ANALYSIS SUMMARY")
        print(f"{'='*60}")
        print(f"📄 Files processed: {self.stats['files_processed']}")
        print(f"📊 Files analyzed: {self.stats['files_analyzed']}")
        print(f"📝 Analyses generated: {self.stats['analyses_generated']}")
        print(f"📁 Output directory: {self.output_dir.absolute()}")
        if self.stats['errors'] > 0:
            print(f"❌ Errors encountered: {self.stats['errors']}")
        else:
            print("✅ No errors encountered")
        print(f"{'='*60}")

def main():
    """Main execution function"""
    print("🚀 CSV Data Analyzer and Markdown Generator")
    print("=" * 60)
    
    # Get directory path from command line argument or use default
    if len(sys.argv) > 1:
        directory_path = sys.argv[1]
    else:
        directory_path = "./data/product_info/data/"
    
    print(f"📁 Target directory: {Path(directory_path).absolute()}")
    
    try:
        # Initialize analyzer
        analyzer = CSVAnalyzer()
        
        # Process directory
        analyzer.process_directory(directory_path)
        
        print(f"\n🎉 ANALYSIS COMPLETED!")
        print("Next steps:")
        print("1. Review the generated analyses in data/csv_converted/")
        print("2. Verify the statistical insights and numbers")
        print("3. Use the markdown files for your knowledge base indexing")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
