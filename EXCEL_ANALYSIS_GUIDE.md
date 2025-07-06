# Excel Analysis Script Guide

## Overview

The `analyze_excel_to_markdown.py` script processes Excel files and generates comprehensive statistical analyses using GPT-4o. It's specifically designed to handle large Excel files by analyzing only the **first 18 rows** of each sheet, making it efficient for getting insights from complex datasets.

## Features

### ✅ **What It Does**
- **Reads Excel files (.xlsx)** with multiple sheets
- **Analyzes first 18 rows only** - perfect for large files
- **Detects headers automatically** in complex Excel structures
- **Generates comprehensive markdown reports** with statistical insights
- **Uses GPT-4o with Entra ID authentication** for intelligent analysis
- **Handles complex Excel formats** with robust error handling

### 📊 **Analysis Includes**
1. **File Structure Analysis** - Sheet breakdown and organization
2. **Data Overview** - Column definitions and data types
3. **Statistical Summary** - Key numbers, totals, percentages
4. **Content Analysis** - Data type identification and context
5. **Data Quality Assessment** - Completeness and reliability
6. **Key Insights** - Trends, patterns, and notable findings

## Usage

### Basic Usage
```bash
# Analyze all Excel files in the default directory
python analyze_excel_to_markdown.py

# Analyze Excel files in a specific directory
python analyze_excel_to_markdown.py /path/to/excel/files/

# Analyze a specific Excel file
python analyze_excel_to_markdown.py /path/to/directory/ filename
```

### Example Commands
```bash
# Analyze the specific BU-TV file we just processed
python analyze_excel_to_markdown.py ./data/product_info/data/ BU-TV-17-T50-TV-nichtdeutsch

# Analyze all Excel files in the data directory
python analyze_excel_to_markdown.py ./data/product_info/data/
```

## Output

### 📁 **Output Location**
All generated analyses are saved in: `./data/excel_converted/`

### 📄 **Output Format**
- **Filename**: `[original_filename].md` (without .xlsx extension)
- **Content**: Comprehensive markdown analysis with:
  - File metadata and generation timestamp
  - Analysis scope limitation notice
  - Detailed statistical breakdown
  - Professional formatting with tables and sections

## Example Analysis Results

From the `BU-TV-17-T50-TV-nichtdeutsch.xlsx` file we just processed:

### 📊 **Key Statistics Found**
- **Total suspects**: 913,196
- **Gender distribution**: 77.42% male, 22.58% female
- **Age groups**: 80.91% adults (21+), 7.41% juveniles, 4.34% children
- **Detailed breakdowns** by age and gender categories

### 🔍 **Analysis Quality**
- **Objective and factual** statistical analysis
- **Specific numbers and percentages** included
- **Data quality assessment** with missing values noted
- **Limitations clearly stated** (first 18 rows only)

## Technical Details

### 🛠️ **Dependencies**
- `pandas` - Excel file reading and data manipulation
- `openpyxl` - Excel file processing
- `azure-openai` - GPT-4o analysis
- `azure-identity` - Entra ID authentication

### 🔧 **Robust Excel Reading**
The script uses multiple fallback methods:
1. **Standard pandas reading** with openpyxl engine
2. **Alternative encoding attempts** if primary method fails
3. **Full-then-limit approach** for difficult files
4. **Header detection algorithm** for complex structures

### ⚠️ **Limitations**
- **18-row limit per sheet** - designed for efficiency with large files
- **Analysis scope clearly stated** in each output
- **Complex Excel formats** may require manual inspection

## Configuration

### 🎯 **Customizable Settings**
```python
self.max_rows = 18  # Change this to analyze more/fewer rows
```

### 🔐 **Authentication**
Uses the same Azure OpenAI credentials as other scripts:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_CHAT_DEPLOYMENT`
- Entra ID authentication via `DefaultAzureCredential`

## Best Practices

### ✅ **When to Use**
- **Large Excel files** where full analysis would be time-consuming
- **Initial data exploration** to understand file structure
- **Quick insights** from complex administrative datasets
- **Batch processing** of multiple Excel files

### 📋 **Workflow Recommendation**
1. **Run the script** on your Excel files
2. **Review generated analyses** in `data/excel_converted/`
3. **Identify interesting patterns** from the first 18 rows
4. **Decide if full analysis** is needed for specific files
5. **Use markdown files** for knowledge base indexing

## Integration with Knowledge Base

The generated markdown files are perfect for:
- **Azure AI Search indexing** - structured content with clear sections
- **RAG (Retrieval Augmented Generation)** - fact-checking queries
- **Documentation** - objective statistical summaries
- **Policy analysis** - data-driven insights with citations

## Error Handling

The script includes robust error handling:
- **Multiple Excel reading attempts** with different methods
- **Sheet-by-sheet processing** - one failed sheet won't stop others
- **Detailed error logging** for troubleshooting
- **Graceful degradation** - continues processing other files if one fails

---

This script bridges the gap between complex Excel datasets and AI-powered analysis, making large statistical files accessible for knowledge base integration and fact-checking applications.
