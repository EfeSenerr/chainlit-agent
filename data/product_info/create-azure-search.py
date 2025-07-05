#!/usr/bin/env python
# coding: utf-8

"""
Multi-Format Document Indexing Pipeline for Azure Cognitive Search

This script creates a comprehensive search index by processing multiple document types:
- Markdown (.md) - preprocessed with convert_base64_to_text.py to extract image content
- Text files (.txt) 
- CSV files (.csv) with special handling for German statistical data
- PDF files (.pdf)
- Excel files (.xlsx, .xls)
- JSON files (.json)

Features:
- Smart content extraction and chunking
- German text encoding handling
- Metadata enrichment
- Always-fresh index creation for testing
- Comprehensive error handling

Prerequisites:
1. Run convert_base64_to_text.py first to preprocess markdown files with images
2. Configure environment variables in .env file

Requirements:
- Azure Search Service
- Azure OpenAI Service (with Entra ID authentication)
- Environment variables in .env file (use .env.sample as template)
"""

import os
import pandas as pd
import re
import json
from pathlib import Path
from typing import List, Dict, Union

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswParameters,
    HnswAlgorithmConfiguration,
    SemanticPrioritizedFields,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticSearch,
    SemanticConfiguration,
    SemanticField,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
    ExhaustiveKnnAlgorithmConfiguration,
    ExhaustiveKnnParameters,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters
)
from openai import AzureOpenAI
from dotenv import load_dotenv

# Optional dependencies with graceful fallback
try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False
    print("⚠️ chardet not available. Install with: pip install chardet")

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PyPDF2 not available. Install with: pip install PyPDF2")

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    print("⚠️ openpyxl not available. Install with: pip install openpyxl")

load_dotenv()


def clean_german_text(text: str) -> str:
    """Clean up common German encoding issues"""
    replacements = {
        'Ã¤': 'ä', 'Ã¶': 'ö', 'Ã¼': 'ü', 'Ã': 'ß',
        'Ã„': 'Ä', 'Ã–': 'Ö', 'Ãœ': 'Ü',
        'â€œ': '"', 'â€': '"', 'â€™': "'", 'â€"': '–', 'â€"': '—'
    }
    
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    
    return text

def detect_encoding(file_path: Path) -> str:
    """Detect file encoding with fallback options"""
    if CHARDET_AVAILABLE:
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result['encoding'] or 'utf-8'
        except Exception:
            pass
    
    # Fallback: try common encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(100)  # Test read
                return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    return 'utf-8'  # Final fallback

def chunk_text(text: str, max_tokens: int = 4000) -> List[str]:
    """Split text into chunks while preserving word boundaries"""
    # Simple word-based chunking (estimate ~3 chars per token)
    max_chars = max_tokens * 3
    
    if len(text) <= max_chars:
        return [text]
    
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk + paragraph) <= max_chars:
            if current_chunk:
                current_chunk += "\n\n"
            current_chunk += paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                # Paragraph too long, split by sentences
                sentences = re.split(r'[.!?]+\s+', paragraph)
                temp_chunk = ""
                for sentence in sentences:
                    if len(temp_chunk + sentence) <= max_chars:
                        if temp_chunk:
                            temp_chunk += ". "
                        temp_chunk += sentence
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = sentence
                        
                        # If single sentence too long, split by words
                        if len(temp_chunk) > max_chars:
                            words = temp_chunk.split()
                            word_chunk = ""
                            for word in words:
                                if len(word_chunk + " " + word) <= max_chars:
                                    if word_chunk:
                                        word_chunk += " "
                                    word_chunk += word
                                else:
                                    if word_chunk:
                                        chunks.append(word_chunk.strip())
                                    word_chunk = word
                            if word_chunk:
                                temp_chunk = word_chunk
                
                current_chunk = temp_chunk
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return [chunk for chunk in chunks if chunk.strip()]

# Document processors for different file types
def process_text_file(file_path: Path) -> str:
    """Process text and markdown files with encoding detection
    
    Note: Markdown files should be preprocessed with convert_base64_to_text.py
    to extract image content before running this indexing pipeline.
    """
    encoding = detect_encoding(file_path)
    
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
            
        content = clean_german_text(content)
        return content
        
    except Exception as e:
        return f"Error processing text file {file_path.name}: {str(e)}"

def process_csv_file(file_path: Path) -> str:
    """Process CSV files with special handling for German statistics"""
    try:
        # Detect encoding
        encoding = detect_encoding(file_path)
        
        # Check if this looks like German statistics data
        with open(file_path, 'r', encoding=encoding) as f:
            sample_content = f.read(1000).lower()
        
        is_german_stats = any(keyword in sample_content for keyword in [
            'straftat', 'verdächtig', 'kriminal', 'deutschland', 'statistik', 'bka'
        ])
        
        if is_german_stats:
            return process_german_statistics_csv(file_path, encoding)
        else:
            return process_regular_csv(file_path, encoding)
            
    except Exception as e:
        return f"Error processing CSV file {file_path.name}: {str(e)}"

def process_regular_csv(file_path: Path, encoding: str) -> str:
    """Process regular CSV files"""
    try:
        df = pd.read_csv(file_path, encoding=encoding)
        
        content_parts = [f"CSV Data from {file_path.name}"]
        content_parts.append(f"Columns: {', '.join(df.columns)}")
        content_parts.append("")
        
        # Add first few rows as examples
        for idx, row in df.head(10).iterrows():
            row_data = []
            for col in df.columns:
                if pd.notna(row[col]):
                    row_data.append(f"{col}: {row[col]}")
            if row_data:
                content_parts.append(" | ".join(row_data))
        
        if len(df) > 10:
            content_parts.append(f"... and {len(df) - 10} more rows")
        
        content = '\n'.join(content_parts)
        return clean_german_text(content)
        
    except Exception as e:
        return f"Error processing regular CSV {file_path.name}: {str(e)}"

def process_german_statistics_csv(file_path: Path, encoding: str) -> str:
    """Specialized processor for German statistics CSV files"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
        
        content_parts = [f"German Statistical Data from {file_path.name}", ""]
        
        # Extract meaningful rows with German text and numbers
        meaningful_rows = []
        data_rows = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.replace(',', '').strip() == '':
                continue
                
            try:
                row_parts = [part.strip().strip('"') for part in line.split(',')]
                row_text = ' '.join([part for part in row_parts if part and part != 'nan'])
                
                if len(row_text) > 20:
                    # Key statistical content
                    if any(keyword in row_text.lower() for keyword in [
                        'straftat', 'verdächtig', 'kriminal', 'delikt', 'deutschland', 
                        'polizei', 'ermittelt', 'ausländer', 'rohheit', 'diebstahl'
                    ]):
                        meaningful_rows.append(f"Zeile {i+1}: {row_text}")
                        
                        if any(num in row_text for num in ['000', '.000', ',000']):
                            content_parts.append(f"📊 WICHTIGE STATISTIK: {row_text}")
                    
                    elif any(crime_type in row_text for crime_type in [
                        'Strafrechtliche Nebengesetze', 'Rohheitsdelikte', 'Diebstahlsdelikte',
                        'Vermögens- und Fälschungsdelikte', 'Gewaltkriminalität', 'Rauschgiftkriminalität'
                    ]):
                        data_rows.append(row_text)
                        
            except Exception:
                if len(line) > 20 and any(keyword in line.lower() for keyword in [
                    'straftat', 'verdächtig', 'deutschland', 'polizei', 'ausländer'
                ]):
                    meaningful_rows.append(f"Text Zeile {i+1}: {line}")
        
        # Add content
        if meaningful_rows:
            content_parts.extend(["BESCHREIBUNG UND KONTEXT:"] + meaningful_rows[:10])
            content_parts.append("")
        
        if data_rows:
            content_parts.extend(["STATISTISCHE DATEN:"] + data_rows)
            content_parts.append("")
        
        content_parts.extend([
            "QUELLE: Bundeskriminalamt (BKA)",
            "JAHR: 2024", 
            "REGION: Deutschland"
        ])
        
        result = '\n'.join(content_parts)
        return clean_german_text(result)
        
    except Exception as e:
        return f"Error processing German statistics CSV {file_path.name}: {str(e)}"

def process_pdf_file(file_path: Path) -> str:
    """Process PDF files to extract text content"""
    if not PDF_AVAILABLE:
        return f"PDF processing not available for {file_path.name}. Install PyPDF2."
    
    try:
        content_parts = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    text = clean_german_text(text)
                    content_parts.append(f"Page {page_num}:\n{text.strip()}")
        
        return '\n\n'.join(content_parts)
        
    except Exception as e:
        return f"Error processing PDF file {file_path.name}: {str(e)}"

def process_excel_file(file_path: Path) -> str:
    """Process Excel files with multiple sheets"""
    if not EXCEL_AVAILABLE:
        return f"Excel processing not available for {file_path.name}. Install openpyxl."
    
    try:
        content_parts = [f"Excel Data from {file_path.name}"]
        
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            content_parts.append(f"\nSheet: {sheet_name}")
            content_parts.append(f"Columns: {', '.join(df.columns)}")
            
            # Add sample rows
            for idx, row in df.head(5).iterrows():
                row_data = []
                for col in df.columns:
                    if pd.notna(row[col]):
                        row_data.append(f"{col}: {row[col]}")
                if row_data:
                    content_parts.append(" | ".join(row_data))
            
            if len(df) > 5:
                content_parts.append(f"... and {len(df) - 5} more rows in this sheet")
        
        content = '\n'.join(content_parts)
        return clean_german_text(content)
        
    except Exception as e:
        return f"Error processing Excel file {file_path.name}: {str(e)}"

def process_json_file(file_path: Path) -> str:
    """Process JSON files"""
    try:
        encoding = detect_encoding(file_path)
        
        with open(file_path, 'r', encoding=encoding) as f:
            data = json.load(f)
        
        # Convert to readable text
        content_parts = [f"JSON Data from {file_path.name}"]
        
        def json_to_text(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, (dict, list)):
                        content_parts.append(f"{prefix}{key}:")
                        json_to_text(value, prefix + "  ")
                    else:
                        content_parts.append(f"{prefix}{key}: {value}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj[:10]):  # Limit to first 10 items
                    content_parts.append(f"{prefix}[{i}]:")
                    json_to_text(item, prefix + "  ")
                if len(obj) > 10:
                    content_parts.append(f"{prefix}... and {len(obj) - 10} more items")
            else:
                content_parts.append(f"{prefix}{obj}")
        
        json_to_text(data)
        
        content = '\n'.join(content_parts)
        return clean_german_text(content)
        
    except Exception as e:
        return f"Error processing JSON file {file_path.name}: {str(e)}"

def get_file_processor(file_path: Path):
    """Get the appropriate processor function for a file type"""
    suffix = file_path.suffix.lower()
    
    processors = {
        '.md': process_text_file,
        '.txt': process_text_file,
        '.csv': process_csv_file,
        '.pdf': process_pdf_file,
        '.xlsx': process_excel_file,
        '.xls': process_excel_file,
        '.json': process_json_file,
    }
    
    return processors.get(suffix, process_text_file)

# Index management functions
def delete_index(search_index_client: SearchIndexClient, search_index: str):
    """Delete an existing search index"""
    print(f"🗑️ Deleting index {search_index}")
    search_index_client.delete_index(search_index)


# In[3]:


def create_index_definition(name: str) -> SearchIndex:
    """
    Returns an Azure Cognitive Search index with enhanced metadata fields
    for multi-format document processing.
    """
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="filepath", type=SearchFieldDataType.String),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="url", type=SearchFieldDataType.String),
        # Enhanced metadata fields for better document management
        SimpleField(name="originalFilename", type=SearchFieldDataType.String),
        SearchableField(name="originalTitle", type=SearchFieldDataType.String),
        SimpleField(name="documentStem", type=SearchFieldDataType.String),
        SimpleField(name="documentType", type=SearchFieldDataType.String),
        SimpleField(name="fileExtension", type=SearchFieldDataType.String),
        SimpleField(name="chunkIndex", type=SearchFieldDataType.Int32),
        SimpleField(name="totalChunks", type=SearchFieldDataType.Int32),
        SimpleField(name="isChunked", type=SearchFieldDataType.Boolean),
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="myHnswProfile",
        ),
        SearchField(
            name="titleVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="myHnswProfile",
        ),    
    ]

    # Semantic configuration
    semantic_config = SemanticConfiguration(
        name="default",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            keywords_fields=[],
            content_fields=[SemanticField(field_name="content")],
        ),
    )

    # Vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="myHnsw",
                kind=VectorSearchAlgorithmKind.HNSW,
                parameters=HnswParameters(
                    m=4,
                    ef_construction=400,
                    ef_search=500,
                    metric=VectorSearchAlgorithmMetric.COSINE,
                ),
            ),
            ExhaustiveKnnAlgorithmConfiguration(
                name="myExhaustiveKnn",
                kind=VectorSearchAlgorithmKind.EXHAUSTIVE_KNN,
                parameters=ExhaustiveKnnParameters(
                    metric=VectorSearchAlgorithmMetric.COSINE
                ),
            ),
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw",
                vectorizer_name="myvectorizer"
            ),
            VectorSearchProfile(
                name="myExhaustiveKnnProfile",
                algorithm_configuration_name="myExhaustiveKnn",
            ),
        ],
        vectorizers=[  
            AzureOpenAIVectorizer(  
                vectorizer_name="myvectorizer",  
                kind="azureOpenAI",  
                parameters=AzureOpenAIVectorizerParameters(  
                    resource_url=os.environ["AZURE_OPENAI_ENDPOINT"],  
                    deployment_name=os.environ["AZURE_EMBEDDING_NAME"],
                    model_name=os.environ["AZURE_EMBEDDING_NAME"],
                ),
            ),  
        ],  
    )

    semantic_search = SemanticSearch(configurations=[semantic_config])

    return SearchIndex(
        name=name,
        fields=fields,
        semantic_search=semantic_search,
        vector_search=vector_search,
    )


# In[4]:


def gen_multi_format_documents(folder_path: str) -> List[Dict[str, any]]:
    """
    Process documents of multiple formats (MD, CSV, PDF, Excel, etc.)
    with enhanced metadata and chunking support.
    
    Args:
        folder_path: Path to the folder containing documents
        
    Note: Markdown files should be preprocessed with convert_base64_to_text.py
    to extract image content before running this indexing pipeline.
    """
    print(f"🔄 Processing multi-format documents from: {folder_path}")
    print("� Processing documents (markdown files should be preprocessed for images)")
    
    openai_service_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    openai_deployment = os.environ["AZURE_EMBEDDING_NAME"]

    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")    
    client = AzureOpenAI(
        api_version="2023-07-01-preview",
        azure_endpoint=openai_service_endpoint,
        azure_deployment=openai_deployment,
        azure_ad_token_provider=token_provider
    )

    items = []
    folder = Path(folder_path)
    
    # Supported file extensions
    supported_extensions = {'.md', '.txt', '.csv', '.pdf', '.xlsx', '.xls', '.json'}
    
    # Find all supported files in the folder and subfolders
    all_files = []
    for ext in supported_extensions:
        all_files.extend(folder.glob(f"**/*{ext}"))
    
    print(f"📂 Found {len(all_files)} supported files to process")
    
    doc_id = 1
    for file_path in all_files:
        try:
            print(f"\n📄 Processing: {file_path.name} ({file_path.suffix})")
            
            # Get the appropriate processor for this file type
            processor = get_file_processor(file_path)
            
            # Call processor (text files are expected to be preprocessed)
            content = processor(file_path)
            
            if not content or len(content.strip()) < 50:
                print(f"⚠️  Skipping {file_path.name} - insufficient content")
                continue
            
            # Determine document type and metadata
            file_extension = file_path.suffix.lower()
            document_type = {
                '.md': 'Markdown Document',
                '.txt': 'Text Document', 
                '.csv': 'CSV Data Table',
                '.pdf': 'PDF Document',
                '.xlsx': 'Excel Spreadsheet',
                '.xls': 'Excel Spreadsheet',
                '.json': 'JSON Data'
            }.get(file_extension, 'Unknown Document')
            
            # Extract title based on file type
            if file_extension == '.md':
                title = file_path.stem
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break
            elif file_extension == '.csv':
                title = file_path.stem
                lines = content.split('\n')[:5]
                for line in lines:
                    if len(line.strip()) > 10 and not line.startswith('Unnamed'):
                        title = line.strip()[:100]
                        break
            else:
                title = file_path.stem
            
            # Document metadata
            original_filename = file_path.name
            document_path = str(file_path.relative_to(folder))
            document_stem = file_path.stem
            
            # Split content into chunks
            content_chunks = chunk_text(content)
            
            print(f"   📑 Split into {len(content_chunks)} chunks")
            
            # Process each chunk as a separate document
            for chunk_idx, chunk in enumerate(content_chunks):
                chunk_id = f"{doc_id}_{chunk_idx + 1}" if len(content_chunks) > 1 else str(doc_id)
                
                display_title = title
                if len(content_chunks) > 1:
                    display_title = f"{title} (Part {chunk_idx + 1})"
                
                # Enhanced content with document reference
                enhanced_content = f"Source Document: {original_filename}\n"
                enhanced_content += f"Document Type: {document_type}\n"
                if len(content_chunks) > 1:
                    enhanced_content += f"Document Section: Part {chunk_idx + 1} of {len(content_chunks)}\n"
                enhanced_content += f"Original Title: {title}\n\n{chunk}"
                
                url = f"/docs/{document_path.replace(file_extension, '').replace('/', '-').lower()}"
                if len(content_chunks) > 1:
                    url += f"-part-{chunk_idx + 1}"
                
                # Generate embeddings
                try:
                    print(f"   🔄 Processing chunk {chunk_idx + 1}/{len(content_chunks)}")
                    
                    content_emb = client.embeddings.create(input=enhanced_content, model=openai_deployment)
                    title_emb = client.embeddings.create(input=display_title, model=openai_deployment)
                    
                    rec = {
                        "id": chunk_id,
                        "content": enhanced_content,
                        "filepath": document_path,
                        "title": display_title,
                        "url": url,
                        "contentVector": content_emb.data[0].embedding,
                        "titleVector": title_emb.data[0].embedding,
                        # Enhanced metadata
                        "originalFilename": original_filename,
                        "originalTitle": title,
                        "documentStem": document_stem,
                        "documentType": document_type,
                        "fileExtension": file_extension,
                        "chunkIndex": chunk_idx + 1,
                        "totalChunks": len(content_chunks),
                        "isChunked": len(content_chunks) > 1
                    }
                    items.append(rec)
                    print(f"   ✅ Processed chunk {chunk_idx + 1}: {display_title}")
                    
                except Exception as e:
                    print(f"   ❌ Error processing chunk {chunk_idx + 1}: {e}")
                    continue
            
            doc_id += 1
            
        except Exception as e:
            print(f"❌ Error processing file {file_path.name}: {e}")
            continue

    print(f"\n📊 Processing completed: {len(items)} document chunks from {doc_id-1} files")
    return items


# Utility functions for index management and testing
def get_index_stats(search_client: SearchClient) -> Dict[str, any]:
    """Get comprehensive statistics about the index"""
    try:
        results = search_client.search("*", select=["originalFilename", "documentType"], top=1000)
        
        files = set()
        doc_types = {}
        total_docs = 0
        
        for result in results:
            total_docs += 1
            if result.get("originalFilename"):
                files.add(result["originalFilename"])
            doc_type = result.get("documentType", "Unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        return {
            "total_documents": total_docs,
            "unique_files": len(files),
            "files": sorted(files),
            "document_types": doc_types
        }
    except Exception as e:
        print(f"❌ Error getting index stats: {e}")
        return {}

def test_search_functionality(search_client: SearchClient):
    """Test basic search functionality"""
    try:
        print("🧪 Testing search functionality...")
        
        # Test basic search
        results = search_client.search("*", top=3)
        result_count = sum(1 for _ in results)
        print(f"   📋 Basic search: {result_count} results")
        
        # Test German search if applicable
        german_results = search_client.search("deutschland OR ausländer OR statistik", top=3)
        german_count = sum(1 for _ in german_results)
        if german_count > 0:
            print(f"   🇩🇪 German search: {german_count} results found")
        
        return True
    except Exception as e:
        print(f"   ❌ Search test failed: {e}")
        return False

def main():
    """Main execution function"""
    print("🚀 Starting Multi-Format Document Indexing Pipeline")
    print("=" * 60)
    
    # Configuration
    search_endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    index_name = os.environ["AZURE_SEARCH_INDEX"]
    document_folder = "./data/"  # Change this path as needed
    
    print("� Processing documents (ensure markdown files are preprocessed with convert_base64_to_text.py)")
    print(f"📍 Search Endpoint: {search_endpoint}")
    print(f"📍 Index Name: {index_name}")
    print(f"📍 Document Folder: {document_folder}")
    
    # Initialize clients
    search_index_client = SearchIndexClient(search_endpoint, DefaultAzureCredential())
    
    try:
        # Step 1: Delete existing index for fresh start
        print(f"\n🗑️ Deleting existing index '{index_name}' for fresh start...")
        try:
            delete_index(search_index_client, index_name)
            print("✅ Index deleted successfully")
        except Exception as e:
            print(f"ℹ️ Index deletion: {e} (this is normal if index didn't exist)")
        
        # Step 2: Create fresh index
        print(f"\n🏗️ Creating fresh index '{index_name}'...")
        index = create_index_definition(index_name)
        search_index_client.create_or_update_index(index)
        print("✅ Fresh index created successfully")
        
        # Step 3: Process documents
        print(f"\n📂 Processing documents from '{document_folder}'...")
        docs = gen_multi_format_documents(document_folder)
        
        if len(docs) == 0:
            print("❌ No documents found to process!")
            print(f"   Make sure documents exist in: {document_folder}")
            print(f"   Supported extensions: .md, .txt, .csv, .pdf, .xlsx, .xls, .json")
            return
        
        # Step 4: Upload documents
        print(f"\n📤 Uploading {len(docs)} document chunks to index...")
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=DefaultAzureCredential(),
        )
        
        # Upload in batches
        batch_size = 50
        successful_batches = 0
        failed_batches = 0
        
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            try:
                search_client.upload_documents(batch)
                successful_batches += 1
                print(f"✅ Uploaded batch {i//batch_size + 1}: {len(batch)} documents")
            except Exception as e:
                failed_batches += 1
                print(f"❌ Error uploading batch {i//batch_size + 1}: {e}")
        
        print(f"\n📊 Upload Summary:")
        print(f"   ✅ Successful batches: {successful_batches}")
        if failed_batches > 0:
            print(f"   ❌ Failed batches: {failed_batches}")
        
        # Step 5: Verify and test
        print(f"\n🔍 Verifying index content...")
        stats = get_index_stats(search_client)
        
        if stats:
            print(f"📊 Index Statistics:")
            print(f"   📄 Total documents: {stats['total_documents']}")
            print(f"   📁 Unique files: {stats['unique_files']}")
            print(f"   📋 Document types: {stats['document_types']}")
            
            print(f"\n📁 Indexed files:")
            for filename in stats['files']:
                print(f"   📄 {filename}")
        
        # Test search functionality
        test_search_functionality(search_client)
        
        print(f"\n{'='*60}")
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"✅ {stats.get('unique_files', 0)} files indexed with {stats.get('total_documents', 0)} total chunks")
        print(f"✅ Index '{index_name}' is ready for use")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

