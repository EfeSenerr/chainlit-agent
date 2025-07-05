import os
import sys
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chat_request import generate_response_agent
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils.env_util import get_aifound_proj_conn_string

load_dotenv()

# Configure timeout for Azure operations (30 seconds)
AGENT_TIMEOUT = 30

connection_string = get_aifound_proj_conn_string()    
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=connection_string,
)

app = FastAPI()

# Add CORS middleware for frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create thread pool for handling blocking operations
executor = ThreadPoolExecutor(max_workers=4)

@app.get("/")
async def root():
    return {"message": "FastAPI Backend is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "fastapi-backend"}

class Item(BaseModel):
    question: str
    thread_id: str

async def run_agent_with_timeout(question: str, thread_id: str) -> dict:
    """Run agent with timeout to prevent hanging"""
    try:
        loop = asyncio.get_event_loop()
        # Run the blocking operation in a thread pool with timeout
        result = await asyncio.wait_for(
            loop.run_in_executor(executor, generate_response_agent, question, thread_id),
            timeout=AGENT_TIMEOUT
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408, 
            detail=f"Request timed out after {AGENT_TIMEOUT} seconds. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent processing failed: {str(e)}"
        )

@app.post("/api/generate_response")
async def generate_response(item: Item) -> dict:
    """Generate response using AI agent with timeout protection"""
    start_time = time.time()
    
    try:
        if not item.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        if not item.thread_id.strip():
            raise HTTPException(status_code=400, detail="Thread ID cannot be empty")
            
        print(f"🔍 Processing request:")
        print(f"   📝 Question: {item.question}")
        print(f"   🧵 Thread ID: {item.thread_id}")
        print(f"   ⏱️ Started at: {time.strftime('%H:%M:%S')}")
        
        result = await run_agent_with_timeout(item.question, item.thread_id)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Request completed successfully in {elapsed_time:.2f} seconds")
        print(f"   📊 Response: {result.get('answer', '')[:100]}...")
        return result
        
    except HTTPException:
        elapsed_time = time.time() - start_time
        print(f"❌ Request failed after {elapsed_time:.2f} seconds")
        raise
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ Unexpected error after {elapsed_time:.2f} seconds: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/test")
async def test(question: str) -> dict:
    """Test endpoint with new thread creation"""
    try:
        if not question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
            
        print(f"Creating new thread for test request...")
        thread = project_client.agents.create_thread()
        result = await run_agent_with_timeout(question, thread.id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Test endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Test endpoint failed")

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server with timeout protection...")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        # Configure uvicorn for better handling of long requests
        timeout_keep_alive=30,
        timeout_graceful_shutdown=10,
        access_log=True
    )