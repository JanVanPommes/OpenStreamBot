import aiohttp
import os
import tempfile
import logging

logger = logging.getLogger("ElevenLabsTTS")

class ElevenLabsTTS:
    def __init__(self, api_key, max_chars=200):
        self.api_key = api_key
        self.max_chars = max_chars
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }

    async def generate_tts(self, text, voice_id="21m00Tcm4TlvDq8ikWAM"): # Rachel as default if empty
        if not self.api_key:
            print("[ElevenLabs] Error: No API key provided.")
            return None
            
        if not voice_id:
            voice_id = "21m00Tcm4TlvDq8ikWAM"
            
        # Enforce max chars
        if len(text) > self.max_chars:
            print(f"[ElevenLabs] Warning: Text length ({len(text)}) exceeds max_chars ({self.max_chars}). Truncating.")
            text = text[:self.max_chars]

        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=self.headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # Save to temp file
                        fd, path = tempfile.mkstemp(suffix=".mp3")
                        with os.fdopen(fd, 'wb') as f:
                            f.write(content)
                        
                        return path
                    else:
                        err = await response.text()
                        try:
                            import json
                            err_json = json.loads(err)
                            detail = err_json.get('detail', {})
                            if isinstance(detail, dict):
                                msg = detail.get('message', err)
                            else:
                                msg = str(detail)
                            print(f"[ElevenLabs] API Fehler ({response.status}): {msg}")
                        except:
                            print(f"[ElevenLabs] API Fehler ({response.status}): {err}")
                        return None
        except Exception as e:
            print(f"[ElevenLabs] Request failed: {e}")
            return None

    async def fetch_voices(self):
        """Fetches available voices for the setup UI."""
        if not self.api_key:
             return []
             
        url = f"{self.base_url}/voices"
        headers = {"xi-api-key": self.api_key}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        voices = []
                        for v in data.get('voices', []):
                            voices.append({
                                'voice_id': v.get('voice_id'),
                                'name': v.get('name'),
                                'category': v.get('category')
                            })
                        return voices
                    else:
                        print(f"[ElevenLabs] Fetch Voices Error: {response.status}")
                        return []
        except Exception as e:
            print(f"[ElevenLabs] Fetching voices failed: {e}")
            return []
