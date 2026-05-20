"""
Voice message handling functions for Telegram API.

This module provides Speech-to-Text functionality using Deepgram API
for converting voice messages to text.
"""
import tempfile
from pathlib import Path

from .core import _request_with_fixed_retry, client, logger


async def transcribe_telegram_audio(file_id: str, bot_token: str) -> str:
    """
    Transcribe a Telegram voice message to text using Deepgram API.
    
    This function:
    1. Gets the file path from Telegram using getFile API
    2. Downloads the audio file from Telegram servers
    3. Sends the audio to Deepgram API for transcription
    4. Returns the transcribed text
    
    Args:
        file_id: Telegram file_id of the voice message
        bot_token: Telegram bot token for API authentication
    
    Returns:
        str: Transcribed text from the voice message
    
    Raises:
        Exception: If any step of the transcription process fails
    """
    # Import DEEPGRAM_API_KEY here to avoid circular imports
    from ..config import DEEPGRAM_API_KEY
    
    # Step 1: Get file path from Telegram
    get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile"
    get_file_response = await _request_with_fixed_retry(
        client.get, 
        get_file_url, 
        params={"file_id": file_id}
    )
    get_file_response.raise_for_status()
    
    file_path = get_file_response.json()["result"]["file_path"]
    logger.info(f"Got file path for voice message: {file_path}")
    
    # Step 2: Download audio file from Telegram
    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    download_response = await _request_with_fixed_retry(client.get, download_url)
    download_response.raise_for_status()
    
    audio_data = download_response.content
    logger.info(f"Downloaded audio file, size: {len(audio_data)} bytes")
    
    # Save audio to temp file for debugging
    temp_dir = Path(tempfile.gettempdir()) / "flirtello_voice_debug"
    temp_dir.mkdir(exist_ok=True)
    debug_audio_path = temp_dir / f"voice_{file_id[-10:]}.ogg"
    
    with open(debug_audio_path, "wb") as f:
        f.write(audio_data)
    logger.info(f"Saved audio to debug file: {debug_audio_path}")
    
    # Step 3: Send to Deepgram API for transcription
    # Important: detect_language requires language parameter to be absent or set to "multi"
    deepgram_url = "https://api.deepgram.com/v1/listen"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/ogg",
    }
    
    # For language detection, don't specify language parameter at all
    params = {
        "model": "nova-3",
        "smart_format": "true",
        "detect_language": "true",
        "punctuate": "true",
        "paragraphs": "true",
    }
    
    logger.info(f"Sending audio to Deepgram API for transcription (size: {len(audio_data)} bytes)...")
    logger.info(f"Deepgram params: {params}")
    
    # Use client.post with explicit timeout - send raw bytes like curl does
    deepgram_response = await client.post(
        deepgram_url,
        content=audio_data,
        headers=headers,
        params=params,
        timeout=30.0,  # Deepgram needs time to process audio
    )
    
    logger.info(f"Deepgram response status: {deepgram_response.status_code}")
    deepgram_response.raise_for_status()
    
    # Step 4: Extract transcript from response
    result = deepgram_response.json()
    logger.info(f"Deepgram API response: {result}")
    
    # Check if we got a transcript
    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
    
    if not transcript or transcript.strip() == "":
        logger.warning(f"Empty transcript received. Full response: {result}")
        logger.warning(f"Audio saved for manual debugging at: {debug_audio_path}")
        logger.warning("You can test it manually with:")
        logger.warning(f'curl --insecure -X POST "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true&detect_language=true" -H "Authorization: Token {DEEPGRAM_API_KEY}" -H "Content-Type: audio/ogg" --data-binary "@{debug_audio_path}"')
        return "[Empty voice message]"
    
    logger.info(f"Successfully transcribed audio: {transcript[:100]}...")
    return transcript

