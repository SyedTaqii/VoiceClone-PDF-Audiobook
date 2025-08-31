import os
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play, save
import json

class ElevenLabsVoiceCloning:
    def __init__(self):
        load_dotenv()
        
        # Get API key
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not found in environment variables!")
        
        print(f"✅ API key loaded")
        
        # Initialize ElevenLabs client
        self.elevenlabs = ElevenLabs(api_key=self.api_key)
        
        # Create output directory
        self.output_dir = Path("audio_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Base URL for API calls
        self.base_url = "https://api.elevenlabs.io/v1"
    
    def upload_voice_sample(self, audio_file_path, voice_name="Taqi Voice", description="Voice cloned from audio sample"):
        """Upload audio sample and create a cloned voice"""
        audio_path = Path(audio_file_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file '{audio_path}' not found!")
        
        print(f"\n🎤 Uploading voice sample: {audio_path.name}")
        print(f"🎭 Creating voice: {voice_name}")
        
        # Check file size (ElevenLabs has limits)
        file_size = audio_path.stat().st_size / (1024 * 1024)  # MB
        print(f"📊 File size: {file_size:.2f} MB")
        
        if file_size > 25:
            print("⚠️  Warning: File is large. Consider compressing or trimming.")
        
        try:
            # Prepare the request
            url = f"{self.base_url}/voices/add"
            headers = {"xi-api-key": self.api_key}
            
            # Prepare form data
            files = {
                'files': (audio_path.name, open(audio_path, 'rb'), 'audio/wav')
            }
            
            data = {
                'name': voice_name,
                'description': description,
                'labels': json.dumps({"accent": "custom", "description": description})
            }
            
            print("🚀 Uploading to ElevenLabs...")
            response = requests.post(url, headers=headers, files=files, data=data)
            
            # Close the file
            files['files'][1].close()
            
            if response.status_code == 200:
                result = response.json()
                voice_id = result['voice_id']
                print(f"✅ Voice cloned successfully!")
                print(f"🎯 Voice ID: {voice_id}")
                print(f"📝 Voice Name: {voice_name}")
                
                return voice_id
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error uploading voice: {e}")
            return None
    
    def list_voices(self):
        """List all available voices including cloned ones"""
        try:
            voices = self.elevenlabs.voices.get_all()
            print("\n🎤 Available voices:")
            
            for voice in voices.voices:
                voice_type = "🤖 Pre-made" if hasattr(voice, 'category') and voice.category == "premade" else "🎭 Custom"
                print(f"   {voice_type} • {voice.name} (ID: {voice.voice_id})")
            
            return voices.voices
            
        except Exception as e:
            print(f"❌ Error fetching voices: {e}")
            return []
    
    def delete_voice(self, voice_id):
        """Delete a cloned voice"""
        try:
            url = f"{self.base_url}/voices/{voice_id}"
            headers = {"xi-api-key": self.api_key}
            
            response = requests.delete(url, headers=headers)
            
            if response.status_code == 200:
                print(f"✅ Voice {voice_id} deleted successfully")
                return True
            else:
                print(f"❌ Failed to delete voice: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting voice: {e}")
            return False
    
    def load_text_from_file(self, text_file_path):
        """Load already extracted and cleaned text from file"""
        text_path = Path(text_file_path)
        
        if not text_path.exists():
            raise FileNotFoundError(f"Text file '{text_path}' not found!")
        
        print(f"\n📖 Loading text from: {text_path.name}")
        
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            
            if not text:
                print("⚠️  Warning: Text file is empty!")
                return ""
            
            print(f"   ✅ Loaded {len(text)} characters from text file")
            return text
            
        except Exception as e:
            print(f"❌ Error loading text file: {e}")
            return ""
    
    def text_to_speech_with_cloned_voice(self, text, voice_id, save_audio=True):
        """Convert text to speech using cloned voice"""
        if not text.strip():
            raise ValueError("No text provided for conversion!")
        
        if not voice_id:
            raise ValueError("Voice ID is required!")
        
        print(f"\n Using cloned voice ID: {voice_id}")
        print(f"🔊 Converting {len(text)} characters to speech...")
        
        try:
            # Convert text to speech with cloned voice
            audio = self.elevenlabs.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            
            # Save audio file if requested
            audio_path = None
            if save_audio:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"cloned_voice_audiobook_{timestamp}.mp3"
                audio_path = self.output_dir / filename
                
                save(audio, str(audio_path))
                print(f"💾 Audio saved to: {audio_path}")
            
            return audio_path
            
        except Exception as e:
            print(f"❌ Error converting text to speech: {e}")
            return None
    
    def clone_and_generate_audiobook(self, text_file_path, reference_audio_path, voice_name="My Cloned Voice"):
        """Complete pipeline: clone voice and generate audiobook"""
        print(f"🚀 Starting Voice Cloning and Audiobook Generation...")
        print(f"📝 Text file: {text_file_path}")
        print(f"🎤 Reference audio: {reference_audio_path}")
        
        try:
            text = self.load_text_from_file(text_file_path)
            if not text:
                return None
            
            voice_id = self.upload_voice_sample(
                audio_file_path=reference_audio_path,
                voice_name=voice_name,
                description=f"Cloned voice for audiobook - {datetime.now().strftime('%Y-%m-%d')}"
            )
            
            if not voice_id:
                print("❌ Voice cloning failed!")
                return None
            
            print(f"\n🎭 Generating audiobook with cloned voice...")
            audio_path = self.text_to_speech_with_cloned_voice(
                text=text,
                voice_id=voice_id
            )
            
            if audio_path:
                print(f"\n🎉 Success! Cloned voice audiobook created!")
                print(f"🎯 Cloned Voice ID: {voice_id} (save this for future use)")
                
            return audio_path, voice_id
            
        except Exception as e:
            print(f"❌ Error in pipeline: {e}")
            return None, None

def main():
    """Main execution function"""
    print("🎭 ElevenLabs Voice Cloning for Audiobooks")
    print("=" * 50)
    
    try:
        cloner = ElevenLabsVoiceCloning()
        
        text_file = "audio_output/page_20_text.txt"  
        reference_audio = "myvoice.wav"              
        voice_name = "Taqi Voice"              
        
        # Check if files exist
        if not os.path.exists(text_file):
            print(f"❌ Text file '{text_file}' not found!")
            print("💡 Available text files in audio_output folder:")
            audio_dir = Path("audio_output")
            if audio_dir.exists():
                text_files = list(audio_dir.glob("*_text_*.txt"))
                for tf in text_files:
                    print(f"   • {tf.name}")
            return
        
        if not os.path.exists(reference_audio):
            print(f"❌ Reference audio file '{reference_audio}' not found!")
            return
        
        # Clone voice and generate audiobook
        audio_path, voice_id = cloner.clone_and_generate_audiobook(
            text_file_path=text_file,
            reference_audio_path=reference_audio,
            voice_name=voice_name
        )
        
        if audio_path and voice_id:
            print(f"\n🎉 Complete Success!")
            print(f"🔊 Audiobook: {audio_path}")
            print(f"🎯 Voice ID: {voice_id}")
            print(f"💡 Save the Voice ID to reuse this voice without re-uploading!")
            
            # Show updated voice list
            print(f"\n📋 Updated voice list:")
            cloner.list_voices()
            
        else:
            print(f"\n❌ Process failed.")
            
    except Exception as e:
        print(f"❌ Initialization failed: {e}")

# Additional utility functions
def reuse_existing_voice():
    """Use an already cloned voice without re-uploading"""
    cloner = ElevenLabsVoiceCloning()
    
    # Configuration for reusing existing voice
    text_file = "audio_output/page_20_text.txt"
    existing_voice_id = "your_voice_id_here"  # Use the voice ID from previous cloning
    
    # Load text and generate with existing voice
    text = cloner.load_text_from_file(text_file)
    if text:
        audio_path = cloner.text_to_speech_with_cloned_voice(text, existing_voice_id)
        print(f"🎉 Audiobook created with existing voice: {audio_path}")

if __name__ == "__main__":
    main()
    
    # reuse_existing_voice()

# Setup Instructions:
"""
1. Install required packages:
   pip install elevenlabs python-dotenv requests

2. Set up your .env file:
   ELEVENLABS_API_KEY=your_api_key_here

3. Prepare your reference audio:
   - Convert myvoice.wav to a supported format if needed
   - Recommended: MP3 or WAV, 22kHz, mono
   - Duration: 1-10 minutes of clear speech

4. Files needed in same directory:
   - This script
   - audio_output/page_20_text.txt (your extracted text)
   - myvoice.wav (or update the filename)
   - .env file with your API key

5. Run: python elevenlabs_clone.py

What this script does:
✅ Uploads your voice sample to ElevenLabs
✅ Creates a cloned voice automatically
✅ Uses that cloned voice to generate your audiobook
✅ Saves the voice ID for future reuse
✅ Much more reliable than local TTS
"""