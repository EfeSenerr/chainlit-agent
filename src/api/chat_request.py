import os
import sys
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AzureAISearchTool
from azure.ai.projects.models import ToolSet
from azure.search.documents import SearchClient
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils.env_util import get_aifound_proj_conn_string, get_aisearch_conn

from dotenv import load_dotenv
load_dotenv()

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
        You are an assistant that provides information based on a knowledge base. You have access to an AI search tool that you must use for factual information.

        Core principles:
        1. For ANY factual information (dates, specifications, prices, features, etc.), you MUST verify using the knowledge base
        2. NEVER make up or hallucinate information
        3. If factual information is not found in the knowledge base, respond with: "I apologize, but I don't have that information in my knowledge base."
        4. You may engage in general conversation without searching, but ANY factual claims must be verified
        5. For questions about products, features, or any specific details, always search the knowledge base

        Remember: 
        - All factual information MUST come from the knowledge base
        - It's better to admit not having information than to provide unverified details
    """,
    toolset=toolset
)

def generate_response_agent(question, thread_id): 
    message = project_client.agents.create_message(        
        thread_id=thread_id,
        role="user",
        content=question
    )
        
    # Run the agent    
    run = project_client.agents.create_and_process_run(thread_id=thread_id, agent_id=agent.id)    

    if run.status == "failed":        
        print(f"Run failed: {run.last_error}")

    # Get messages from the thread 
    messages = project_client.agents.list_messages(thread_id=thread_id)    

    run_steps = project_client.agents.list_run_steps(run_id=run.id, thread_id=thread_id)
    run_steps_data = run_steps['data']
    print(f"Last run step detail: {run_steps_data}")    
        
    assistant_message = ""
    for message in messages.data:
        if message["role"] == "assistant":
            assistant_message = message["content"][0]["text"]["value"]
            break

    # Get the last message from the sender
    print(f"Assistant response: {assistant_message}")

    return {"question": question, "answer": assistant_message}