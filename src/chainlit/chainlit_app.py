import sys
import os
import chainlit as cl
import requests
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils.env_util import get_aifound_proj_conn_string


env = os.getenv("ENVIRONMENT", "")
base_url = os.getenv("API_URL")
if env == "azure": 
    api_url = f"{base_url}/api/generate_response"    
else:
    api_url = "http://localhost:8000/api/generate_response"

connection_string =  get_aifound_proj_conn_string()
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=connection_string,
)


@cl.on_chat_start
async def main():
    await cl.Message(content="""Hello there, I am your assistant. I can answer questions based on the information provided in the knowledge base""").send()

@cl.on_message
async def on_message(msg: cl.Message):    
    question = msg.content

    thread = cl.user_session.get("user_thread")
    if thread is None:
        thread = project_client.agents.create_thread()
        cl.user_session.set("user_thread", thread)
        
    # Data to be sent
    data = {
        "question": question,
        "thread_id": thread.id
    }
    
    # A POST request to the API
    response = requests.post(api_url, json=data)
    result = response.json()

    # Print the response    
    await cl.Message(result.get("answer")).send()    


if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)    