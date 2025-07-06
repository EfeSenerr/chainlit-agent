# Speech-to-Text Integration Guide

## Overview

This integration adds speech-to-text functionality to your fact-checking assistant using Azure OpenAI Whisper with Entra ID authentication.

## Features Added

### 1. **Chainlit Voice Interface**
- Press `P` key to start voice recording
- Automatic silence detection to end recording
- Visual feedback during audio processing
- Transcription display with original audio playback

### 2. **API Endpoints**
- `/api/speech_to_text` - Transcribe audio to text only
- `/api/speech_to_response` - Transcribe audio and generate response

### 3. **Supported Audio Formats**
- WAV, MP3, M4A, OGG, FLAC

## Configuration

### Environment Variables
Make sure your `.env` file includes:
```bash
AZURE_WHISPER_MODEL="whisper-1"  # Update with your deployed model name
AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/"
AZURE_OPENAI_API_VERSION="2024-02-01"
```

### Authentication
The integration uses Entra ID authentication via `DefaultAzureCredential`, so make sure your environment is properly authenticated.

## Usage

### In Chainlit Interface
1. Start the Chainlit app: `chainlit run src/chainlit/chainlit_app.py`
2. Open the web interface
3. Press `P` key to start voice recording
4. Speak your question
5. The system will automatically detect when you stop speaking
6. Your audio will be transcribed and processed

### Via API
```python
import requests

# Transcribe audio only
with open("audio.wav", "rb") as f:
    files = {"file": ("audio.wav", f, "audio/wav")}
    response = requests.post("http://localhost:8000/api/speech_to_text", files=files)
    print(response.json())

# Transcribe and get response
with open("audio.wav", "rb") as f:
    files = {"file": ("audio.wav", f, "audio/wav")}
    data = {"thread_id": "your_thread_id"}
    response = requests.post("http://localhost:8000/api/speech_to_response", files=files, data=data)
    print(response.json())
```

## Testing

Run the test script to verify the integration:
```bash
python test_speech_integration.py
```

This will:
1. Check if the API is running
2. Create a test audio file
3. Test the speech-to-text endpoint

## Audio Configuration

### Silence Detection
- `SILENCE_THRESHOLD = 3500` - Adjust based on your microphone sensitivity
- `SILENCE_TIMEOUT = 1300.0` - Milliseconds of silence before ending recording

### Audio Quality
- Sample Rate: 24kHz PCM
- Format: 16-bit mono WAV
- Minimum Duration: 1 second

## Troubleshooting

### Common Issues

1. **"Speech-to-text conversion failed"**
   - Check your Azure OpenAI endpoint and authentication
   - Verify the Whisper model name in environment variables
   - Ensure proper Entra ID permissions

2. **"Audio is too short"**
   - Speak for at least 1 second
   - Check microphone permissions in browser

3. **"Unsupported audio format"**
   - Use supported formats: WAV, MP3, M4A, OGG, FLAC
   - Ensure proper file extensions

4. **Token Refresh Issues**
   - The system automatically refreshes Entra ID tokens
   - Check Azure credentials: `az login`

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export AZURE_LOG_LEVEL=DEBUG
```

## Dependencies

New packages added:
- `numpy` - Audio processing
- `python-multipart` - File upload handling
- `azure-identity` - Entra ID authentication
- `openai` - Azure OpenAI client

## Security Notes

- Audio files are processed in memory and not stored permanently
- Authentication uses managed identity or user credentials
- All API calls use HTTPS in production
- Audio data is sent to Azure OpenAI for transcription

## Performance

- Audio processing time: ~2-5 seconds for typical voice messages
- Automatic timeout handling (35 seconds max)
- Retry logic for network issues
- Background processing to avoid UI blocking
