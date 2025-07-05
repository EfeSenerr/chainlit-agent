import os
import sys
import time
import re
import json
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AzureAISearchTool
from azure.ai.projects.models import ToolSet
from azure.search.documents import SearchClient
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils.env_util import get_aifound_proj_conn_string, get_aisearch_conn

from dotenv import load_dotenv
load_dotenv()

# Timeout configuration
AGENT_RUN_TIMEOUT = 25  # seconds
POLL_INTERVAL = 1  # seconds

connection_string = get_aifound_proj_conn_string()
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=connection_string,
)
index_name = os.environ["AZURE_SEARCH_INDEX"]

aisearch_conn_id = get_aisearch_conn()

# Initialize agent AI search tool and add the search index connection ID and index name
ai_search = AzureAISearchTool(index_connection_id=aisearch_conn_id, index_name=index_name, query_type="vector_semantic_hybrid")

# Initialize agent toolset with AI search
toolset = ToolSet()
toolset.add(ai_search)

agent = project_client.agents.create_agent(
    model="gpt-4o",
    name="my-assistant",
    instructions="""
        system:
       You are a fact-checking assistant that provides accurate, verified information based strictly on a trusted knowledge base. You have access to an AI-powered search tool for retrieving facts and evidence.

        Core principles:
        1. For ANY factual information (dates, specifications, prices, features, etc.), you MUST verify using the knowledge base
        2. NEVER make up or hallucinate information
        3. If factual information is not found in the knowledge base, respond with: "I apologize, but I don't have that information in my knowledge base."
        4. You may engage in general conversation without searching, but ANY factual claims must be verified
        5. You MUST provide a citation or reference from the knowledge base when giving factual information.
        6. If multiple relevant sources are found, summarize the most reliable information and cite all applicable sources.

        Citation format:
        - Always clearly indicate the source (e.g., [Source: XYZ Database], [Source: Knowledge Base: Product Guide 2024], etc.)
        - If multiple sources, list them all at the end of your response.

        Remember: 
        - All factual information MUST come from the knowledge base
        - It's better to admit not having information than to provide unverified details
        - Verified information with citations builds trust.
        - Keep responses concise and helpful.
    """,
    toolset=toolset
)

def extract_search_results_from_run_steps(run_steps_data):
    """Extract search results from run steps to build citation mapping"""
    search_results = []
    
    try:
        for step in run_steps_data:
            step_details = step.get('step_details', {})
            if step_details.get('type') == 'tool_calls':
                tool_calls = step_details.get('tool_calls', [])
                for tool_call in tool_calls:
                    if tool_call.get('type') == 'azure_ai_search':
                        print(f"🔍 Extracting search results from tool call...")
                        
                        # Try multiple possible locations for search results
                        search_result = None
                        
                        # Method 1: Check 'output' field
                        if 'output' in tool_call and tool_call['output']:
                            search_result = tool_call['output']
                            print(f"   Found results in 'output' field")
                        
                        # Method 2: Check nested azure_ai_search field
                        elif 'azure_ai_search' in tool_call:
                            azure_search_data = tool_call['azure_ai_search']
                            if 'results' in azure_search_data:
                                search_result = azure_search_data['results']
                                print(f"   Found results in 'azure_ai_search.results' field")
                            elif 'output' in azure_search_data:
                                search_result = azure_search_data['output']
                                print(f"   Found results in 'azure_ai_search.output' field")
                        
                        # Method 3: Check if the entire tool_call contains results directly
                        elif 'results' in tool_call:
                            search_result = tool_call['results']
                            print(f"   Found results in 'results' field")
                        
                        if search_result:
                            print(f"   🔍 Raw search result type: {type(search_result)}")
                            print(f"   🔍 Raw search result preview: {str(search_result)[:200]}...")
                            
                            try:
                                # If it's already a list or dict, use it directly
                                if isinstance(search_result, list):
                                    search_results.extend(search_result)
                                    print(f"   ✅ Added {len(search_result)} results from list")
                                elif isinstance(search_result, dict):
                                    if 'results' in search_result:
                                        results_list = search_result['results']
                                        if isinstance(results_list, list):
                                            search_results.extend(results_list)
                                            print(f"   ✅ Added {len(results_list)} results from dict.results")
                                    else:
                                        # Treat the dict as a single result
                                        search_results.append(search_result)
                                        print(f"   ✅ Added 1 result from dict")
                                elif isinstance(search_result, str):
                                    # Try to parse as JSON
                                    if search_result.startswith('[') or search_result.startswith('{'):
                                        try:
                                            # First try standard JSON parsing
                                            parsed_results = json.loads(search_result)
                                            print(f"   ✅ Successfully parsed as JSON")
                                        except json.JSONDecodeError as e:
                                            print(f"   ⚠️ Standard JSON parsing failed: {e}")
                                            try:
                                                # Try parsing Python literal (handles single quotes)
                                                import ast
                                                parsed_results = ast.literal_eval(search_result)
                                                print(f"   ✅ Successfully parsed as Python literal")
                                            except (ValueError, SyntaxError) as e2:
                                                print(f"   ❌ Python literal parsing failed: {e2}")
                                                try:
                                                    # Try replacing single quotes with double quotes for JSON
                                                    json_output = search_result.replace("'", '"')
                                                    parsed_results = json.loads(json_output)
                                                    print(f"   ✅ Successfully parsed after quote replacement")
                                                except json.JSONDecodeError as e3:
                                                    print(f"   ❌ Quote replacement parsing failed: {e3}")
                                                    raise e  # Re-raise original error
                                        
                                        if isinstance(parsed_results, list):
                                            search_results.extend(parsed_results)
                                            print(f"   ✅ Added {len(parsed_results)} results from parsed JSON list")
                                        elif isinstance(parsed_results, dict):
                                            if 'results' in parsed_results:
                                                results_list = parsed_results['results']
                                                search_results.extend(results_list)
                                                print(f"   ✅ Added {len(results_list)} results from parsed JSON dict.results")
                                            else:
                                                search_results.append(parsed_results)
                                                print(f"   ✅ Added 1 result from parsed JSON dict")
                                    else:
                                        print(f"   ⚠️ String result doesn't look like JSON")
                                else:
                                    print(f"   ⚠️ Unknown search result type: {type(search_result)}")
                                    
                            except json.JSONDecodeError as json_error:
                                print(f"   ❌ JSON parsing error: {json_error}")
                            except Exception as parse_error:
                                print(f"   ❌ Error parsing search results: {parse_error}")
                        else:
                            print(f"   ❌ No search results found in tool call")
                            
    except Exception as e:
        print(f"❌ Error extracting search results: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"🔍 Total search results extracted: {len(search_results)}")
    return search_results

def improve_citations(assistant_message, search_results):
    """Replace cryptic citations with meaningful document titles"""
    
    print(f"🔍 Improving citations...")
    print(f"   📝 Original message length: {len(assistant_message)}")
    print(f"   📋 Search results count: {len(search_results)}")
    
    if not search_results:
        print(f"   ⚠️ No search results available for citation improvement")
        return assistant_message
    
    # Create a mapping of document indices to titles
    citation_mapping = {}
    
    print(f"   🗂️ Building citation mapping...")
    
    # First, check if we have a single search result with metadata containing titles
    document_titles = []
    for result in search_results:
        if isinstance(result, dict):
            print(f"      Checking result: {list(result.keys())}")
            
            # Check if this result has metadata with titles
            if 'metadata' in result and isinstance(result['metadata'], dict):
                metadata = result['metadata']
                print(f"         Found metadata: {list(metadata.keys())}")
                
                if 'titles' in metadata and isinstance(metadata['titles'], list):
                    document_titles = metadata['titles']
                    print(f"         Found {len(document_titles)} titles in metadata: {document_titles}")
                    break
    
    # If we found titles in metadata, use those for citation mapping
    if document_titles:
        print(f"   📚 Using titles from metadata for citation mapping")
        for i, title in enumerate(document_titles):
            # Clean up the title
            cleaned_title = title
            if cleaned_title:
                # Remove file extensions for cleaner display
                if cleaned_title.endswith('.md') or cleaned_title.endswith('.pdf') or cleaned_title.endswith('.csv'):
                    cleaned_title = cleaned_title[:-4]
                elif cleaned_title.endswith('.xlsx'):
                    cleaned_title = cleaned_title[:-5]
                elif cleaned_title.endswith('.txt'):
                    cleaned_title = cleaned_title[:-4]
                elif cleaned_title.endswith('.json'):
                    cleaned_title = cleaned_title[:-5]
                
                # Truncate very long titles
                if len(cleaned_title) > 80:
                    cleaned_title = cleaned_title[:80] + "..."
                
                citation_mapping[i] = cleaned_title
                print(f"         Title {i}: {cleaned_title}")
    else:
        # Fallback: Extract titles from individual search results (old logic)
        print(f"   📂 No metadata titles found, extracting from individual search results...")
        for i, result in enumerate(search_results):
            print(f"      Result {i}: Type = {type(result)}, Fields = {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            # Try different fields for document title/name
            title = None
            
            # Check common title fields
            if isinstance(result, dict):
                # Debug: Print all fields for analysis
                print(f"         All fields: {list(result.keys())}")
                
                if 'title' in result:
                    title = result['title']
                    print(f"         Using 'title': {title}")
                elif 'originalFilename' in result:
                    title = result['originalFilename']
                    print(f"         Using 'originalFilename': {title}")
                elif 'originalTitle' in result:
                    title = result['originalTitle']
                    print(f"         Using 'originalTitle': {title}")
                elif 'filepath' in result:
                    # Extract filename from filepath
                    filepath = result['filepath']
                    title = filepath.split('/')[-1] if '/' in filepath else filepath
                    print(f"         Using 'filepath': {filepath} -> {title}")
                elif 'file_name' in result:
                    title = result['file_name']
                    print(f"         Using 'file_name': {title}")
                elif 'source' in result:
                    title = result['source']
                    print(f"         Using 'source': {title}")
                elif 'document' in result:
                    title = result['document']
                    print(f"         Using 'document': {title}")
                elif 'filename' in result:
                    title = result['filename']
                    print(f"         Using 'filename': {title}")
                elif '@search.score' in result:
                    # This is likely an Azure Search result format
                    # Look for content or chunk_id that might contain filename info
                    if 'chunk_id' in result:
                        chunk_id = result['chunk_id']
                        # Extract filename from chunk_id (format: filename_chunk_X)
                        if '_chunk_' in chunk_id:
                            title = chunk_id.split('_chunk_')[0]
                            print(f"         Extracted from 'chunk_id': {chunk_id} -> {title}")
                        else:
                            title = chunk_id
                            print(f"         Using 'chunk_id': {title}")
                    elif 'id' in result:
                        # Use document ID as fallback
                        doc_id = result['id']
                        if '_chunk_' in doc_id:
                            title = doc_id.split('_chunk_')[0]
                            print(f"         Extracted from 'id': {doc_id} -> {title}")
                        else:
                            title = doc_id
                            print(f"         Using 'id': {title}")
                
                # If still no title found, try to use any field that might be a filename
                if not title:
                    for key, value in result.items():
                        if isinstance(value, str) and ('.' in value or '/' in value):
                            # This might be a filename or path
                            title = value.split('/')[-1] if '/' in value else value
                            print(f"         Using potential filename from '{key}': {title}")
                            break
            else:
                title = f"Document {i+1}"
                print(f"         Using fallback for non-dict: {title}")
            
            # Clean up the title
            if title:
                # Remove file extensions for cleaner display
                if title.endswith('.md') or title.endswith('.pdf') or title.endswith('.csv'):
                    title = title[:-4]
                elif title.endswith('.xlsx'):
                    title = title[:-5]
                elif title.endswith('.txt'):
                    title = title[:-4]
                elif title.endswith('.json'):
                    title = title[:-5]
                
                # Truncate very long titles
                if len(title) > 60:
                    title = title[:60] + "..."
                
                citation_mapping[i] = title
                print(f"         Final title: {title}")
            else:
                # Final fallback
                citation_mapping[i] = f"Document {i+1}"
                print(f"         Using final fallback: Document {i+1}")
    
    print(f"   🗂️ Citation mapping: {citation_mapping}")
    
    # Replace citations in the message
    improved_message = assistant_message
    
    # Pattern to match citations like 【12:0†source】, 【5†source】, etc.
    citation_patterns = [
        r'【(\d+):?\d*†source】',  # Matches 【12:0†source】 or 【12†source】
        r'【(\d+)†source】',       # Matches 【5†source】
        r'\[(\d+)\]',              # Matches [5]
    ]
    
    replacements_made = 0
    
    for pattern_idx, pattern in enumerate(citation_patterns):
        print(f"   🔍 Trying pattern {pattern_idx + 1}: {pattern}")
        
        # Find all matches first
        matches = re.findall(pattern, improved_message)
        print(f"      Found matches: {matches}")
        
        def replace_citation(match):
            nonlocal replacements_made
            try:
                index = int(match.group(1))
                if index in citation_mapping:
                    replacement = f"[Source: {citation_mapping[index]}]"
                    print(f"         Replacing citation {index} with: {replacement}")
                    replacements_made += 1
                    return replacement
                else:
                    # If we don't have a mapping, try to use a generic name
                    replacement = f"[Source: Document {index + 1}]"
                    print(f"         Using generic replacement for {index}: {replacement}")
                    replacements_made += 1
                    return replacement
            except (ValueError, IndexError) as e:
                print(f"         Error parsing citation {match.group(0)}: {e}")
                return match.group(0)  # Return original if parsing fails
        
        improved_message = re.sub(pattern, replace_citation, improved_message)
    
    print(f"   ✅ Made {replacements_made} citation replacements")
    print(f"   📝 Final message length: {len(improved_message)}")
    
    if replacements_made > 0:
        print(f"   📖 Citation improvement preview: {improved_message[:200]}...")
    
    return improved_message

def generate_response_agent(question, thread_id): 
    """Generate response with timeout and error handling"""
    try:
        print(f"Creating message for thread {thread_id}")
        message = project_client.agents.create_message(        
            thread_id=thread_id,
            role="user",
            content=question
        )
        
        print(f"Starting agent run...")
        # Create run without waiting for completion
        run = project_client.agents.create_run(thread_id=thread_id, agent_id=agent.id)
        
        # Poll for completion with timeout
        start_time = time.time()
        while time.time() - start_time < AGENT_RUN_TIMEOUT:
            try:
                run_status = project_client.agents.get_run(thread_id=thread_id, run_id=run.id)
                print(f"Run status: {run_status.status}")
                
                if run_status.status == "completed":
                    print("Run completed successfully")
                    break
                elif run_status.status == "failed":
                    print(f"Run failed: {run_status.last_error}")
                    return {
                        "question": question, 
                        "answer": "I apologize, but I encountered an error while processing your request. Please try again.",
                        "error": "Agent run failed"
                    }
                elif run_status.status in ["cancelled", "expired"]:
                    print(f"Run was {run_status.status}")
                    return {
                        "question": question, 
                        "answer": "I apologize, but your request was interrupted. Please try again.",
                        "error": f"Agent run {run_status.status}"
                    }
                
                time.sleep(POLL_INTERVAL)
                
            except Exception as poll_error:
                print(f"Error polling run status: {poll_error}")
                time.sleep(POLL_INTERVAL)
        else:
            # Timeout reached
            print(f"Agent run timed out after {AGENT_RUN_TIMEOUT} seconds")
            try:
                # Try to cancel the run
                project_client.agents.cancel_run(thread_id=thread_id, run_id=run.id)
            except Exception as cancel_error:
                print(f"Error cancelling run: {cancel_error}")
            
            return {
                "question": question, 
                "answer": "I apologize, but your request is taking longer than expected. Please try asking a simpler question or try again later.",
                "error": "Request timeout"
            }

        # Get messages from the thread 
        try:
            messages = project_client.agents.list_messages(thread_id=thread_id)    
            
            # Get run steps for debugging
            try:
                run_steps = project_client.agents.list_run_steps(run_id=run.id, thread_id=thread_id)
                run_steps_data = run_steps.get('data', [])
                print(f"Run steps count: {len(run_steps_data)}")
                
                # Print detailed information about each run step
                for i, step in enumerate(run_steps_data):
                    print(f"--- Run Step {i+1} ---")
                    print(f"Step ID: {step.get('id', 'N/A')}")
                    print(f"Step Type: {step.get('type', 'N/A')}")
                    print(f"Step Status: {step.get('status', 'N/A')}")
                    
                    # Check for tool calls
                    step_details = step.get('step_details', {})
                    if step_details.get('type') == 'tool_calls':
                        tool_calls = step_details.get('tool_calls', [])
                        print(f"Tool calls found: {len(tool_calls)}")
                        
                        for j, tool_call in enumerate(tool_calls):
                            print(f"  Tool Call {j+1}:")
                            print(f"    ID: {tool_call.get('id', 'N/A')}")
                            print(f"    Type: {tool_call.get('type', 'N/A')}")
                            
                            # Azure AI Search tool details
                            if tool_call.get('type') == 'azure_ai_search':
                                # Debug: Print the entire tool call structure first
                                print(f"    🐛 Full tool call structure:")
                                import pprint
                                pprint.pprint(tool_call, indent=8)
                                
                                search_details = tool_call.get('azure_ai_search', {})
                                print(f"    🔍 Azure AI Search Query: {search_details.get('query', 'N/A')}")
                                print(f"    📊 Search Type: {search_details.get('query_type', 'N/A')}")
                                print(f"    📋 Top K: {search_details.get('top_k', 'N/A')}")
                                
                                # Search results if available
                                search_result = tool_call.get('output', '')
                                if search_result:
                                    print(f"    📄 Search Results Preview: {search_result[:200]}...")
                                    # Count number of search results
                                    try:
                                        if search_result.startswith('[') or search_result.startswith('{'):
                                            parsed_results = json.loads(search_result)
                                            if isinstance(parsed_results, list):
                                                print(f"    📈 Number of search results: {len(parsed_results)}")
                                            elif isinstance(parsed_results, dict) and 'results' in parsed_results:
                                                results_count = len(parsed_results.get('results', []))
                                                print(f"    📈 Number of search results: {results_count}")
                                    except:
                                        pass
                                else:
                                    print(f"    ⚠️ No search output found in tool call")
                            else:
                                # Other tool types
                                print(f"    🔧 Tool Details: {tool_call}")
                    
                    # Check for message creation
                    elif step_details.get('type') == 'message_creation':
                        message_details = step_details.get('message_creation', {})
                        message_id = message_details.get('message_id', 'N/A')
                        print(f"💬 Message created: {message_id}")
                    
                    print()  # Empty line for readability
                    
            except Exception as steps_error:
                print(f"Error getting run steps: {steps_error}")
                
            assistant_message = ""
            message_details = []
            
            for message in messages.data:
                if message.get("role") == "assistant":
                    content = message.get("content", [])
                    if content and len(content) > 0:
                        text_content = content[0].get("text", {})
                        assistant_message = text_content.get("value", "")
                        
                        # Log message details
                        message_details.append({
                            "id": message.get("id", "N/A"),
                            "created_at": message.get("created_at", "N/A"),
                            "thread_id": message.get("thread_id", "N/A"),
                            "content_length": len(assistant_message)
                        })
                        break

            if not assistant_message:
                print("❌ No assistant message found")
                return {
                    "question": question, 
                    "answer": "I apologize, but I didn't receive a proper response. Please try again.",
                    "error": "No assistant response"
                }

            print(f"✅ Assistant response received:")
            print(f"   📝 Length: {len(assistant_message)} characters")
            print(f"   📄 Preview: {assistant_message[:150]}...")
            
            # Log if search was used
            search_used = False
            search_queries = []
            
            if 'run_steps_data' in locals():
                for step in run_steps_data:
                    step_details = step.get('step_details', {})
                    if step_details.get('type') == 'tool_calls':
                        tool_calls = step_details.get('tool_calls', [])
                        for tool_call in tool_calls:
                            if tool_call.get('type') == 'azure_ai_search':
                                search_used = True
                                search_details = tool_call.get('azure_ai_search', {})
                                query = search_details.get('query', '')
                                if query:
                                    search_queries.append(query)
            
            print(f"   🔍 Azure AI Search used: {'Yes' if search_used else 'No'}")
            if search_queries:
                print(f"   📋 Search queries: {search_queries}")
            
            # Extract and improve citations
            search_results = extract_search_results_from_run_steps(run_steps_data)
            print(f"   📋 Extracted {len(search_results)} search results for citation improvement")
            
            if search_results:
                print(f"   🔍 Sample search result fields: {list(search_results[0].keys()) if search_results else 'None'}")
            
            improved_message = improve_citations(assistant_message, search_results)
            
            if improved_message != assistant_message:
                print(f"   ✅ Citations improved successfully")
                print(f"   📝 Improved preview: {improved_message[:150]}...")
            else:
                print(f"   ⚠️ No citations were improved (no matching patterns or search results)")
            
            return {"question": question, "answer": improved_message}
            
        except Exception as message_error:
            print(f"Error retrieving messages: {message_error}")
            return {
                "question": question, 
                "answer": "I encountered an error while retrieving the response. Please try again.",
                "error": "Message retrieval failed"
            }
            
    except Exception as e:
        print(f"Unexpected error in generate_response_agent: {e}")
        return {
            "question": question, 
            "answer": "I apologize, but I encountered an unexpected error. Please try again.",
            "error": str(e)
        }