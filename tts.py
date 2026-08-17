import edge_tts
import tempfile
import os
import time
import re
from config import VOICE_NAME

def clean_text_for_speech(text: str) -> str:
    """Strip markdown code blocks, symbols, and formatting for natural speech synthesis."""
    # Remove code blocks ```...```
    text = re.sub(r'```[\s\S]*?```', ' Code snippet omitted. ', text)
    # Remove inline code `...`
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Remove URLs
    text = re.sub(r'http[s]?://\S+', ' link ', text)
    # Remove markdown bold/italics
    text = re.sub(r'[*_~#>-]', ' ', text)
    # Condense multiple spaces/newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def text_to_speech(text: str, voice: str = VOICE_NAME) -> str | None:
    """Generate audio speech from text using Microsoft Edge TTS.
    
    Returns:
        Path to the generated MP3/OGG audio file, or None on failure.
    """
    try:
        clean_text = clean_text_for_speech(text)
        if not clean_text:
            return None
        
        # Limit spoken text length if output was a huge wall of text
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000] + "... and so on, sir."
            
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, f"jarvis_voice_{int(time.time()*1000)}.mp3")
        
        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(audio_path)
        
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            return audio_path
        return None
    except Exception as e:
        print(f"[TTS Error]: {e}")
        return None
