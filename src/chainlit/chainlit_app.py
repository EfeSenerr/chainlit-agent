import sys
import os
import chainlit as cl
import requests
import asyncio
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils.env_util import get_aifound_proj_conn_string

# Configuration
REQUEST_TIMEOUT = 35  # seconds - slightly longer than backend timeout
MAX_RETRIES = 2

env = os.getenv("ENVIRONMENT", "")
base_url = os.getenv("API_URL")
if env == "azure": 
    api_url = f"{base_url}/api/generate_response"    
else:
    api_url = "http://localhost:8000/api/generate_response"

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

⚠️ **Please note:**
- I only provide information that I can verify from my knowledge base
- If I don't have information on a topic, I'll let you know
- Responses may take a few seconds as I search through the knowledge base

Feel free to ask me anything! 🤔"""
    
    await cl.Message(content=welcome_message).send()

async def call_backend_with_retry(data, retries=MAX_RETRIES):
    """Call backend API with retry logic and timeout handling"""
    for attempt in range(retries + 1):
        try:
            # Show typing indicator for longer requests
            async with cl.Step(name="🔍 Searching knowledge base..." if attempt == 0 else f"🔄 Retrying... (attempt {attempt + 1})") as step:
                response = requests.post(
                    api_url, 
                    json=data, 
                    timeout=REQUEST_TIMEOUT,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    step.output = "✅ Search completed"
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