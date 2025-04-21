import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from chat_request import generate_response_agent
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils.env_util import get_aifound_proj_conn_string

load_dotenv()
connection_string =  get_aifound_proj_conn_string()    
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=connection_string,
)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

class Item(BaseModel):
    question: str
    thread_id: str

@app.post("/api/generate_response")
def generate_response(item: Item) -> dict:
    result = generate_response_agent(item.question, item.thread_id)
    return result    

@app.post("/api/test")
def test(question: str) -> dict:
    thread = project_client.agents.create_thread()
    result = generate_response_agent(question, thread.id)
    return result   

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)