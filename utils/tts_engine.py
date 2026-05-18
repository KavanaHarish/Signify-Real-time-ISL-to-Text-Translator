from gtts import gTTS
import os
import tempfile
import base64
class TTSEngine:
    """
    Text-to-Speech engine using gTTS for multilingual audio output
    """
    def __init__(self, default_language='en'):
        self.default_language = default_language
        self.supported_languages = {
            'en': 'English',
            'hi': 'Hindi',
            'kn': 'Kannada',
            'ta': 'Tamil',
            'te': 'Telugu',
            'ml': 'Malayalam',
            'bn': 'Bengali',
            'gu': 'Gujarati',
            'mr': 'Marathi'
        }
    
    def text_to_speech(self, text, language=None):
        """
        Convert text to speech audio
        
        Args:
            text: Text to convert
            language: Language code (defaults to self.default_language)
            
        Returns:
            audio_file_path: Path to generated audio file
        """
        if not text or text.strip() == "":
            return None
        
        lang = language or self.default_language
        
        try:
            # Create TTS object
            tts = gTTS(text=text, lang=lang, slow=False)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Save audio
            tts.save(temp_file_path)
            
            return temp_file_path
        
        except Exception as e:
            print(f"TTS Error: {str(e)}")
            return None
    
    def get_audio_base64(self, audio_path):
        """
        Convert audio file to base64 for web playback
        """
        try:
            with open(audio_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
                audio_base64 = base64.b64encode(audio_bytes).decode()
                return audio_base64
        except Exception as e:
            print(f"Audio encoding error: {str(e)}")
            return None
    
    def cleanup_audio(self, audio_path):
        """
        Delete temporary audio file
        """
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            print(f"Cleanup error: {str(e)}")
    
    def is_language_supported(self, language_code):
        """
        Check if language is supported by gTTS
        """
        return language_code in self.supported_languages
    
    def get_supported_languages(self):
        """
        Return dictionary of supported languages
        """
        return self.supported_languages
    
    def set_default_language(self, language_code):
        """
        Set default language for TTS
        """
        if self.is_language_supported(language_code):
            self.default_language = language_code
            return True
        return False
