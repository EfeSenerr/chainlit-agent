import sys
import os
import chainlit as cl
import requests
import asyncio
import io
import numpy as np
import wave
import audioop
import time
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils.env_util import get_aifound_proj_conn_string

# Configuration
REQUEST_TIMEOUT = 35  # seconds - slightly longer than backend timeout
MAX_RETRIES = 2
MIN_REQUEST_INTERVAL = 2.0  # Minimum seconds between requests

# Audio configuration
SILENCE_THRESHOLD = 3500  # Adjust based on your audio level
SILENCE_TIMEOUT = 1300.0  # Milliseconds of silence to consider the turn finished

env = os.getenv("ENVIRONMENT", "")
base_url = os.getenv("API_URL")
if env == "azure": 
    api_url = f"{base_url}/api/generate_response"
    speech_api_url = f"{base_url}/api/speech_to_response"
else:
    api_url = "http://localhost:8000/api/generate_response"
    speech_api_url = "http://localhost:8000/api/speech_to_response"

connection_string = get_aifound_proj_conn_string()
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=connection_string,
)

@cl.on_chat_start
async def main():
    welcome_message = """👋 Hello! I'm your fact-checking assistant.

I can help you find accurate, verified information from my knowledge base. Here are a few things to keep in mind:

✅ **What I can do:**
- Answer questions using verified information from my knowledge base
- Provide citations and sources for factual claims
- Help with research and fact-checking
- Process voice messages (press `P` to talk!)

⚠️ **Please note:**
- I only provide information that I can verify from my knowledge base
- If I don't have information on a topic, I'll let you know
- Responses may take a few seconds as I search through the knowledge base
- Please note that our tool does not claim to provide you with the absolute truth. Despite careful selection of the sources for our database, there may still be errors in the data itself, or incorrect citations and references in the chatbot itself. If you have any questions about the information in the sources, we recommend that you always contact the author or publishing institution.
- The Description texts for csv and Excel data sets, as well as for graphics and illustrations from PDF sources were created by a GPT agent. These were of course checked for correctness by our team, but not completely written by us manually.

Feel free to ask me anything! 🤔"""
    
    await cl.Message(content=welcome_message).send()

@cl.on_audio_start
async def on_audio_start():
    """Initialize audio recording session"""
    cl.user_session.set("silent_duration_ms", 0)
    cl.user_session.set("is_speaking", False)
    cl.user_session.set("audio_chunks", [])
    return True

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Process incoming audio chunks and detect silence"""
    audio_chunks = cl.user_session.get("audio_chunks")

    if audio_chunks is not None:
        audio_chunk = np.frombuffer(chunk.data, dtype=np.int16)
        audio_chunks.append(audio_chunk)

    # If this is the first chunk, initialize timers and state
    if chunk.isStart:
        cl.user_session.set("last_elapsed_time", chunk.elapsedTime)
        cl.user_session.set("is_speaking", True)
        return

    audio_chunks = cl.user_session.get("audio_chunks")
    last_elapsed_time = cl.user_session.get("last_elapsed_time")
    silent_duration_ms = cl.user_session.get("silent_duration_ms")
    is_speaking = cl.user_session.get("is_speaking")

    # Calculate the time difference between this chunk and the previous one
    time_diff_ms = chunk.elapsedTime - last_elapsed_time
    cl.user_session.set("last_elapsed_time", chunk.elapsedTime)

    # Compute the RMS (root mean square) energy of the audio chunk
    audio_energy = audioop.rms(chunk.data, 2)  # Assumes 16-bit audio (2 bytes per sample)

    if audio_energy < SILENCE_THRESHOLD:
        # Audio is considered silent
        silent_duration_ms += time_diff_ms
        cl.user_session.set("silent_duration_ms", silent_duration_ms)
        if silent_duration_ms >= SILENCE_TIMEOUT and is_speaking:
            cl.user_session.set("is_speaking", False)
            await process_audio()
    else:
        # Audio is not silent, reset silence timer and mark as speaking
        cl.user_session.set("silent_duration_ms", 0)
        if not is_speaking:
            cl.user_session.set("is_speaking", True)

async def process_audio():
    """Process recorded audio and send to backend for transcription and response"""
    # Get the audio buffer from the session
    if audio_chunks := cl.user_session.get("audio_chunks"):
        try:
            # Concatenate all chunks
            concatenated = np.concatenate(list(audio_chunks))

            # Create an in-memory binary stream
            wav_buffer = io.BytesIO()

            # Create WAV file with proper parameters
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)  # mono
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(24000)  # sample rate (24kHz PCM)
                wav_file.writeframes(concatenated.tobytes())

            # Reset buffer position
            wav_buffer.seek(0)
            
            # Reset audio chunks for next recording
            cl.user_session.set("audio_chunks", [])

            # Check if audio is long enough
            frames = len(concatenated)
            rate = 24000
            duration = frames / float(rate)
            
            if duration <= 1.0:
                await cl.Message(content="⚠️ The audio is too short, please try again.").send()
                return

            audio_buffer = wav_buffer.getvalue()

            # Show the audio to user
            input_audio_el = cl.Audio(content=audio_buffer, mime="audio/wav")

            # Get or create thread
            thread = cl.user_session.get("user_thread")
            if thread is None:
                try:
                    thread = project_client.agents.create_thread()
                    cl.user_session.set("user_thread", thread)
                except Exception as e:
                    await cl.Message(content=f"❌ Error creating conversation thread: {str(e)}").send()
                    return

            # Send audio to backend for processing
            async with cl.Step(name="🎤 Processing voice message...") as step:
                try:
                    files = {"file": ("audio.wav", audio_buffer, "audio/wav")}
                    data = {"thread_id": thread.id}
                    
                    response = requests.post(
                        speech_api_url,
                        files=files,
                        data=data,
                        timeout=REQUEST_TIMEOUT
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        step.output = "✅ Voice message processed"
                        
                        # Show transcription
                        transcription = result.get("transcription", "")
                        if transcription:
                            await cl.Message(
                                author="You",
                                type="user_message",
                                content=f"🎤 *{transcription}*",
                                elements=[input_audio_el],
                            ).send()
                        
                        # Show response
                        answer = result.get("answer", "I apologize, but I didn't receive a proper response.")
                        if result.get("error"):
                            error_note = f"\n\n⚠️ *Note: {result.get('error')}*"
                            answer += error_note
                        
                        await cl.Message(content=answer).send()
                        
                    else:
                        step.output = f"❌ Error: {response.status_code}"
                        await cl.Message(content="❌ Sorry, I couldn't process your voice message. Please try again.").send()
                        
                except Exception as e:
                    step.output = f"❌ Error: {str(e)}"
                    await cl.Message(content=f"❌ Error processing voice message: {str(e)}").send()
                    
        except Exception as e:
            await cl.Message(content=f"❌ Error processing audio: {str(e)}").send()

async def call_backend_with_retry(data, retries=MAX_RETRIES):
    """Call backend API with retry logic and timeout handling"""
    for attempt in range(retries + 1):
        try:
            # Show typing indicator for requests
            step_name = "🤔 Thinking..." if attempt == 0 else f"🔄 Retrying... (attempt {attempt + 1})"
            async with cl.Step(name=step_name) as step:
                # Start the request
                start_time = asyncio.get_event_loop().time()
                
                # Create a task for the HTTP request
                async def make_request():
                    return requests.post(
                        api_url, 
                        json=data, 
                        timeout=REQUEST_TIMEOUT,
                        headers={"Content-Type": "application/json"}
                    )
                
                # Wait for either the request to complete or 5 seconds to show progress
                try:
                    response = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, lambda: requests.post(
                            api_url, 
                            json=data, 
                            timeout=REQUEST_TIMEOUT,
                            headers={"Content-Type": "application/json"}
                        )), 
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    # If it takes longer than 5 seconds, update the step message
                    step.name = "🔍 Searching knowledge base..." if attempt == 0 else f"🔄 Still working... (attempt {attempt + 1})"
                    # Continue waiting for the full timeout
                    response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.post(
                        api_url, 
                        json=data, 
                        timeout=REQUEST_TIMEOUT,
                        headers={"Content-Type": "application/json"}
                    ))
                
                if response.status_code == 200:
                    result = response.json()
                    step.output = "✅ Response completed"
                    return result, None
                elif response.status_code == 408:
                    error_msg = "Request timed out on the server. Please try a simpler question."
                    step.output = f"⏱️ {error_msg}"
                    return None, error_msg
                elif response.status_code == 500:
                    error_msg = f"Server error occurred. Please try again."
                    step.output = f"❌ {error_msg}"
                    if attempt < retries:
                        await asyncio.sleep(2)  # Wait before retry
                        continue
                    return None, error_msg
                else:
                    error_msg = f"Unexpected response: {response.status_code}"
                    step.output = f"❌ {error_msg}"
                    return None, error_msg
                    
        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after {REQUEST_TIMEOUT} seconds."
            if attempt < retries:
                await cl.Message(content=f"⏱️ Request is taking longer than expected. Retrying... (attempt {attempt + 2})").send()
                await asyncio.sleep(3)
                continue
            return None, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = "Could not connect to the backend service. Please check if the API server is running."
            if attempt < retries:
                await cl.Message(content="🔄 Connection issue. Retrying...").send()
                await asyncio.sleep(3)
                continue
            return None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            if attempt < retries:
                await asyncio.sleep(2)
                continue
            return None, error_msg
    
    return None, "Maximum retries exceeded"

@cl.on_message
async def on_message(msg: cl.Message):    
    question = msg.content.strip()
    
    # Rate limiting check
    last_request_time = cl.user_session.get("last_request_time", 0)
    current_time = time.time()
    time_since_last = current_time - last_request_time
    
    if time_since_last < MIN_REQUEST_INTERVAL:
        wait_time = MIN_REQUEST_INTERVAL - time_since_last
        await cl.Message(content=f"⏳ Please wait {wait_time:.1f} more seconds before sending another message.").send()
        return
    
    cl.user_session.set("last_request_time", current_time)
    
    # Validate input
    if not question:
        await cl.Message(content="Please ask me a question! 🤔").send()
        return
    
    if len(question) > 1000:
        await cl.Message(content="Your question is quite long. Please try to keep it under 1000 characters for better performance.").send()
        return

    # Get or create thread
    thread = cl.user_session.get("user_thread")
    if thread is None:
        try:
            thread = project_client.agents.create_thread()
            cl.user_session.set("user_thread", thread)
        except Exception as e:
            await cl.Message(content=f"❌ Error creating conversation thread: {str(e)}").send()
            return
        
    # Prepare request data
    data = {
        "question": question,
        "thread_id": thread.id
    }
    
    # Call backend with retry logic
    result, error = await call_backend_with_retry(data)
    
    if error:
        error_response = f"""❌ **Sorry, I encountered an issue:**

{error}

💡 **Suggestions:**
- Try asking a simpler or shorter question
- Check if the backend service is running
- If the problem persists, try refreshing the page

🔧 **For developers:** Check the backend logs for more details."""
        await cl.Message(content=error_response).send()
        return
    
    # Extract and send the answer
    answer = result.get("answer", "I apologize, but I didn't receive a proper response.")
    
    # Check if there was an error in the result
    if result.get("error"):
        error_note = f"\n\n⚠️ *Note: {result.get('error')}*"
        answer += error_note
    
    await cl.Message(content=answer).send()    


if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)