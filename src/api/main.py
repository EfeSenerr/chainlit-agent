import os
import sys
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chat_request import generate_response_agent, speech_to_text
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

@app.post("/api/upload_audio")
async def upload_audio(file: UploadFile = File(...), thread_id: str = "") -> dict:
    """Upload audio file and transcribe to text using AI agent"""
    try:
        if not thread_id.strip():
            raise HTTPException(status_code=400, detail="Thread ID cannot be empty")
        
        # Save the uploaded file temporarily
        temp_file_path = f"/tmp/{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        print(f"📥 Received audio file: {file.filename}")
        print(f"   🧵 Thread ID: {thread_id}")
        
        # Transcribe audio to text
        transcription_result = await run_agent_with_timeout(
            f"Transcribe the audio to text.", thread_id
        )
        
        elapsed_time = time.time() - start_time
        print(f"✅ Audio processed and transcribed in {elapsed_time:.2f} seconds")
        
        return {
            "transcription": transcription_result.get("answer", ""),
            "thread_id": thread_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Audio upload and processing error: {e}")
        raise HTTPException(status_code=500, detail="Audio processing failed")

@app.post("/api/speech_to_text")
async def transcribe_audio(file: UploadFile = File(...)) -> dict:
    """Transcribe audio to text using Azure OpenAI Whisper"""
    try:
        if not file.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.ogg', '.flac')):
            raise HTTPException(status_code=400, detail="Unsupported audio format")
        
        # Read audio file content
        audio_content = await file.read()
        
        print(f"🎤 Processing audio file: {file.filename}, size: {len(audio_content)} bytes")
        
        # Convert speech to text
        transcription = await asyncio.get_event_loop().run_in_executor(
            executor, 
            speech_to_text, 
            audio_content, 
            file.filename
        )
        
        print(f"✅ Transcription completed: {transcription[:100]}...")
        
        return {
            "transcription": transcription,
            "filename": file.filename,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Speech-to-text error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/api/speech_to_response")
async def transcribe_and_respond(file: UploadFile = File(...), thread_id: str = Form(...)) -> dict:
    """Transcribe audio and generate response using AI agent"""
    try:
        if not thread_id.strip():
            raise HTTPException(status_code=400, detail="Thread ID cannot be empty")
            
        if not file.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.ogg', '.flac')):
            raise HTTPException(status_code=400, detail="Unsupported audio format")
        
        # Read audio file content
        audio_content = await file.read()
        
        print(f"🎤 Processing audio file: {file.filename}, size: {len(audio_content)} bytes")
        print(f"🧵 Thread ID: {thread_id}")
        
        # Convert speech to text
        transcription = await asyncio.get_event_loop().run_in_executor(
            executor, 
            speech_to_text, 
            audio_content, 
            file.filename
        )
        
        print(f"📝 Transcription: {transcription}")
        
        # Generate response using the transcribed text
        result = await run_agent_with_timeout(transcription, thread_id)
        
        # Add transcription to the result
        result["transcription"] = transcription
        result["filename"] = file.filename
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Speech-to-response error: {e}")
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")

@app.post("/api/test_whisper_direct")
async def test_whisper_direct(file: UploadFile = File(...)) -> dict:
    """Direct test of Whisper API"""
    try:
        audio_content = await file.read()
        
        print(f"🎤 Direct Whisper test - file: {file.filename}, size: {len(audio_content)} bytes")
        
        # Test the speech_to_text function directly
        result = await asyncio.get_event_loop().run_in_executor(
            executor, 
            speech_to_text, 
            audio_content, 
            file.filename
        )
        
        return {
            "transcription": result,
            "status": "success",
            "test": "direct_whisper"
        }
        
    except Exception as e:
        print(f"Direct Whisper test error: {e}")
        raise HTTPException(status_code=500, detail=f"Direct Whisper test failed: {str(e)}")

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